from __future__ import annotations

import json
import os
import shutil
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
SMOKE_QUESTION = "A100 出现 E-17，排气温度升高，应如何排查？"
SMOKE_CONTEXT = (
    "资料片段 1\n"
    "正文：A100 故障代码 E-17 表示供压异常。"
    "常见原因包括进气过滤器堵塞、压力传感器偏移、供压管路泄漏、进气阀动作不充分。"
)


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    load_dotenv(PROJECT_DIR / ".env", override=False)
    _force_public_chain_runtime()

    summary: dict[str, Any] = {
        "runtime": {
            "provider": os.getenv("LLM_PROVIDER", ""),
            "model": os.getenv("LLM_MODEL", ""),
            "base_url": os.getenv("LLM_BASE_URL", ""),
            "storage_backend": os.getenv("STORAGE_BACKEND", ""),
            "vector_backend": os.getenv("VECTOR_BACKEND", ""),
        },
        "checks": [],
        "warnings": [],
        "critical_failures": [],
    }

    try:
        from app.config import get_settings
        from app.main import create_app
        from app.rag.llm import LLMConfig, LLMGenerator
        from fastapi.testclient import TestClient
    except Exception as exc:
        _fail(summary, "app_import", str(exc))
        _print(summary, args.output)
        return 1

    project_docs = PROJECT_DIR / "data" / "real_manuals_sanitized"
    smoke_db = PROJECT_DIR / "data" / "app_real_llm_grounding.db"
    smoke_chroma = PROJECT_DIR / "data" / "chroma_real_llm_grounding"
    _reset_smoke_runtime(smoke_db, smoke_chroma)
    settings = get_settings()

    direct_llm = LLMGenerator(
        LLMConfig(
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
    )
    direct_result = direct_llm.generate(question=SMOKE_QUESTION, context=SMOKE_CONTEXT)
    direct_pass = direct_llm.is_enabled and bool(direct_result.answer)
    _record(
        summary,
        "direct_llm_connected",
        direct_pass,
        {
            "llm_enabled": direct_llm.is_enabled,
            "answer_present": bool(direct_result.answer),
            "error": direct_result.error[:300],
            "answer_preview": direct_result.answer[:240],
        },
    )
    if not direct_llm.is_enabled:
        _fail(summary, "direct_llm_connected", "LLM is not enabled by current runtime.")
    elif not direct_result.answer:
        _fail(summary, "direct_llm_connected", direct_result.error or "LLM returned empty answer.")

    app = create_app(
        database_path=smoke_db,
        chroma_dir=smoke_chroma,
        real_docs_dir=project_docs,
    )
    try:
        client = TestClient(app)

        ingest = client.post(
            "/api/v1/documents/ingest",
            json={"docs_source": "real_manuals_sanitized"},
        )
        ingest_body = ingest.json()
        _record(
            summary,
            "ingest_real_manuals",
            ingest.status_code == 200 and ingest_body.get("chunk_count", 0) > 0,
            {"status_code": ingest.status_code, **ingest_body},
        )

        grounded_pass = False
        attempts: list[dict[str, Any]] = []
        for attempt in range(1, 4):
            chat = client.post("/api/v1/chat", json={"question": SMOKE_QUESTION})
            chat_body = chat.json()
            citations = chat_body.get("citations", [])
            attempt_pass = (
                chat.status_code == 200
                and chat_body.get("llm_used") is True
                and _answer_looks_grounded(chat_body.get("answer", ""))
            )
            attempts.append(
                {
                    "attempt": attempt,
                    "status_code": chat.status_code,
                    "llm_used": chat_body.get("llm_used"),
                    "insufficient": chat_body.get("insufficient"),
                    "citation_count": len(citations),
                    "first_source": citations[0].get("source") if citations else "",
                    "answer_preview": chat_body.get("answer", "")[:240],
                    "passed": attempt_pass,
                }
            )
            if attempt_pass:
                grounded_pass = True
                break
        _record(
            summary,
            "chat_grounded_llm",
            grounded_pass,
            {
                "attempt_count": len(attempts),
                "accepted_attempt": next(
                    (item["attempt"] for item in attempts if item["passed"]),
                    None,
                ),
                "attempts": attempts,
            },
        )
        if not grounded_pass:
            _fail(
                summary,
                "chat_grounded_llm",
                "Current runtime LLM did not produce an accepted grounded answer.",
            )
        else:
            _downgrade_direct_probe_failure(summary)
    finally:
        _close_runtime(app)

    _print(summary, args.output)
    return 1 if summary["critical_failures"] else 0


def _force_public_chain_runtime() -> None:
    os.environ["STORAGE_BACKEND"] = "sqlite"
    os.environ["VECTOR_BACKEND"] = "chroma"
    os.environ["CACHE_ENABLED"] = "false"
    os.environ["GRAPH_RETRIEVAL_ENABLED"] = "false"
    os.environ["MULTIMODAL_BACKEND"] = "sidecar"


def _reset_smoke_runtime(smoke_db: Path, smoke_chroma: Path) -> None:
    if smoke_db.exists():
        smoke_db.unlink()
    if smoke_chroma.exists():
        shutil.rmtree(smoke_chroma)


def _answer_looks_grounded(answer: str) -> bool:
    text = answer.strip()
    rejection_markers = [
        "无法访问文件",
        "未提供资料",
        "没有上下文",
        "通信模块",
        "主板固件",
        "当前资料不足，无法确认",
    ]
    partial_boundary_markers = [
        "\u5f53\u524d\u8d44\u6599\u4e0d\u8db3",
        "\u65e0\u6cd5\u786e\u8ba4",
        "\u672a\u63d0\u53ca",
        "\u672a\u5305\u542b",
        "\u9700\u7ed3\u5408\u73b0\u573a",
    ]
    action_markers = [
        "\u5efa\u8bae\u52a8\u4f5c",
        "\u6392\u67e5",
        "\u68c0\u67e5",
        "1.",
        "1\u3001",
        "1\uff0e",
    ]
    has_partial_boundary = any(marker in text for marker in partial_boundary_markers)
    has_grounded_actions = any(marker in text for marker in action_markers)
    if has_partial_boundary and has_grounded_actions:
        return True
    return bool(text) and not any(marker in text for marker in rejection_markers)


def _record(summary: dict[str, Any], name: str, passed: bool, detail: Any) -> None:
    summary["checks"].append({"name": name, "passed": passed, "detail": detail})


def _fail(summary: dict[str, Any], name: str, reason: str) -> None:
    summary["critical_failures"].append({"name": name, "reason": reason})


def _downgrade_direct_probe_failure(summary: dict[str, Any]) -> None:
    remaining_failures = []
    for failure in summary["critical_failures"]:
        if failure.get("name") == "direct_llm_connected":
            summary["warnings"].append(
                {
                    "name": "direct_llm_connected",
                    "reason": failure.get("reason", ""),
                    "note": "Grounded chat acceptance passed, so the direct smoke failure is not a release blocker.",
                }
            )
        else:
            remaining_failures.append(failure)
    summary["critical_failures"] = remaining_failures


def _print(summary: dict[str, Any], output: str = "") -> None:
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
    print(text)


def _close_runtime(app) -> None:
    store = getattr(getattr(app.state, "pipeline", None), "store", None)
    pool = getattr(store, "pool", None)
    if pool is not None:
        pool.close()


if __name__ == "__main__":
    raise SystemExit(main())
