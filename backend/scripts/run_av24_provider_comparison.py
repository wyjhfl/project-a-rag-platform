from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from app.rag.costing import TokenCostEstimator
from dotenv import load_dotenv
from fastapi.testclient import TestClient

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_DIR / "docs" / "A-v2.2_provider_manifest.json"
DEFAULT_ACCEPTANCE = PROJECT_DIR / "docs" / "A-v2.2_provider_acceptance_report_2026-05-23.json"
DEFAULT_OUTPUT = PROJECT_DIR / "docs" / f"A-v2.4_provider_comparison_report_{date.today().isoformat()}.json"


@dataclass(frozen=True)
class ComparisonCase:
    case_id: str
    question: str
    expected_terms: tuple[str, ...]


CASES = [
    ComparisonCase(
        case_id="provider-001",
        question="A100 出现 E-17，排气温度升高，应该怎么排查？",
        expected_terms=("A100", "E-17", "过滤器", "压力"),
    ),
    ComparisonCase(
        case_id="provider-002",
        question="UPS-30K 电池有异味并冒烟，现场想直接重启，可以吗？",
        expected_terms=("UPS", "电池", "停机", "人工"),
    ),
    ComparisonCase(
        case_id="provider-003",
        question="CW200 高压报警，优先检查哪些部件？",
        expected_terms=("CW200", "高压", "压力", "冷却"),
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--acceptance-report", default=str(DEFAULT_ACCEPTANCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dotenv-override", action="store_true")
    args = parser.parse_args()

    load_dotenv(PROJECT_DIR / ".env", override=args.dotenv_override)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    acceptance = read_json(Path(args.acceptance_report))
    providers = [entry for entry in manifest.get("providers", []) if not entry.get("from_env")]
    if not providers:
        raise ValueError("Provider comparison requires explicit provider entries.")

    results = [
        run_provider_comparison(entry, acceptance=acceptance)
        for entry in providers
    ]
    report = {
        "version": "A-v2.4",
        "generated_on": date.today().isoformat(),
        "case_count": len(CASES),
        "summary": summarize_results(results),
        "ranking": rank_providers(results),
        "results": results,
        "notes": [
            "estimated_tokens uses the local TokenCostEstimator and is for relative comparison only.",
            "default_env is intentionally skipped to avoid duplicating an explicit provider candidate.",
        ],
    }
    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


def run_provider_comparison(entry: dict[str, Any], *, acceptance: dict[str, Any]) -> dict[str, Any]:
    runtime = provider_runtime(entry)
    apply_public_chain_provider(runtime, entry)
    from app.main import create_app

    run_root = PROJECT_DIR / "tmp" / "provider_comparison" / runtime["name"]
    db_path = run_root / "app.db"
    chroma_dir = run_root / "chroma"
    reset_runtime(run_root)

    app = create_app(
        database_path=db_path,
        chroma_dir=chroma_dir,
        real_docs_dir=PROJECT_DIR / "data" / "real_manuals_sanitized",
    )
    try:
        client = TestClient(app)
        ingest = client.post(
            "/api/v1/documents/ingest",
            json={"docs_source": "real_manuals_sanitized"},
        )
        case_results = [run_case(client, case) for case in CASES]
    finally:
        close_runtime(app)

    summary = summarize_provider_cases(case_results)
    accepted_baseline = find_acceptance_result(acceptance, runtime["name"])
    return {
        "name": runtime["name"],
        "runtime": {
            "provider": runtime["provider"],
            "model": runtime["model"],
            "base_url": runtime["base_url"],
        },
        "acceptance_baseline": accepted_baseline,
        "ingest": {
            "status_code": ingest.status_code,
            **safe_json(ingest),
        },
        "summary": summary,
        "cases": case_results,
    }


def run_case(client: TestClient, case: ComparisonCase) -> dict[str, Any]:
    started = time.perf_counter()
    response = client.post("/api/v1/chat", json={"question": case.question})
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    payload = response.json()
    citations = payload.get("citations", [])
    joined = payload.get("answer", "") + "\n" + "\n".join(
        str(item.get("content", "")) for item in citations
    )
    expected_hits = [
        term for term in case.expected_terms
        if term.lower() in joined.lower()
    ]
    usage = TokenCostEstimator().estimate(
        module="provider_comparison",
        prompt=case.question + "\n" + "\n".join(str(item.get("content", "")) for item in citations),
        completion=str(payload.get("answer", "")),
    )
    return {
        "case_id": case.case_id,
        "status_code": response.status_code,
        "llm_used": bool(payload.get("llm_used")),
        "insufficient": bool(payload.get("insufficient")),
        "safety_warning": bool(payload.get("safety_warning")),
        "citation_count": len(citations),
        "first_source": citations[0].get("source") if citations else "",
        "expected_hit_count": len(expected_hits),
        "expected_term_count": len(case.expected_terms),
        "expected_hits": expected_hits,
        "answer_chars": len(str(payload.get("answer", ""))),
        "estimated_tokens": usage.total_tokens,
        "elapsed_ms": elapsed_ms,
        "answer_preview": str(payload.get("answer", ""))[:260],
    }


def summarize_provider_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_count = len(cases)
    if case_count == 0:
        return {}
    llm_used_count = sum(1 for item in cases if item["llm_used"])
    citation_case_count = sum(1 for item in cases if item["citation_count"] > 0)
    expected_hits = sum(int(item["expected_hit_count"]) for item in cases)
    expected_total = sum(int(item["expected_term_count"]) for item in cases)
    total_tokens = sum(int(item["estimated_tokens"]) for item in cases)
    avg_latency_ms = round(sum(float(item["elapsed_ms"]) for item in cases) / case_count, 2)
    return {
        "case_count": case_count,
        "llm_used_count": llm_used_count,
        "llm_used_rate": round(llm_used_count / case_count, 4),
        "citation_case_count": citation_case_count,
        "citation_case_rate": round(citation_case_count / case_count, 4),
        "expected_hit_rate": round(expected_hits / expected_total, 4) if expected_total else 0,
        "total_estimated_tokens": total_tokens,
        "avg_estimated_tokens": round(total_tokens / case_count, 2),
        "avg_latency_ms": avg_latency_ms,
        "insufficient_count": sum(1 for item in cases if item["insufficient"]),
        "safety_warning_count": sum(1 for item in cases if item["safety_warning"]),
    }


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "provider_count": len(results),
        "case_count": len(CASES),
        "providers": {
            item["name"]: item["summary"]
            for item in results
        },
    }


def rank_providers(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        results,
        key=lambda item: (
            item["summary"].get("llm_used_rate", 0),
            item["summary"].get("expected_hit_rate", 0),
            item["summary"].get("citation_case_rate", 0),
            -item["summary"].get("avg_estimated_tokens", 0),
        ),
        reverse=True,
    )
    return [
        {
            "rank": index,
            "name": item["name"],
            "llm_used_rate": item["summary"].get("llm_used_rate", 0),
            "expected_hit_rate": item["summary"].get("expected_hit_rate", 0),
            "citation_case_rate": item["summary"].get("citation_case_rate", 0),
            "avg_estimated_tokens": item["summary"].get("avg_estimated_tokens", 0),
            "avg_latency_ms": item["summary"].get("avg_latency_ms", 0),
        }
        for index, item in enumerate(ranked, start=1)
    ]


def provider_runtime(entry: dict[str, Any]) -> dict[str, str]:
    return {
        "name": str(entry.get("name", "")),
        "provider": str(entry.get("provider", "")),
        "model": str(entry.get("model", "")),
        "base_url": str(entry.get("base_url", "")),
    }


def apply_public_chain_provider(runtime: dict[str, str], entry: dict[str, Any]) -> None:
    os.environ.update(
        {
            "STORAGE_BACKEND": "sqlite",
            "VECTOR_BACKEND": "chroma",
            "CACHE_ENABLED": "false",
            "GRAPH_RETRIEVAL_ENABLED": "false",
            "MULTIMODAL_BACKEND": "sidecar",
            "LLM_PROVIDER": runtime["provider"],
            "LLM_MODEL": runtime["model"],
            "LLM_BASE_URL": runtime["base_url"],
            "LLM_API_KEY": resolve_api_key(entry),
        }
    )


def resolve_api_key(entry: dict[str, Any]) -> str:
    api_key_env = str(entry.get("api_key_env", "")).strip()
    if api_key_env:
        return os.getenv(api_key_env, "")
    return str(entry.get("api_key", ""))


def reset_runtime(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def close_runtime(app) -> None:
    store = getattr(getattr(app.state, "pipeline", None), "store", None)
    pool = getattr(store, "pool", None)
    if pool is not None:
        pool.close()


def find_acceptance_result(acceptance: dict[str, Any], name: str) -> dict[str, Any]:
    for item in acceptance.get("results", []):
        if item.get("name") == name:
            return {
                "status": item.get("status", ""),
                "blocker_type": item.get("blocker_type", ""),
                "warnings": item.get("warnings", []),
            }
    return {}


def safe_json(response) -> dict[str, Any]:
    try:
        return response.json()
    except Exception:
        return {}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
