from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_DIR / "docs"
DEFAULT_PROVIDER_REPORT = DOCS_DIR / "A-v1.3_provider_acceptance_report.json"
DEFAULT_OUTPUT = DOCS_DIR / "A-v1.3_acceptance_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-report", default=str(DEFAULT_PROVIDER_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    provider_report = load_json(Path(args.provider_report))
    components = build_acceptance_components(provider_report)
    report = {
        "version": "A-v1.3",
        "generated_on": date.today().isoformat(),
        "summary": summarize_components(components),
        "components": components,
    }
    output_path = Path(args.output)
    output_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    output_path.write_text(output_text, encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_acceptance_components(provider_report: dict) -> list[dict]:
    components: list[dict] = []
    provider_results = {item["name"]: item for item in provider_report.get("results", [])}

    default_provider = provider_results.get("default_env")
    if default_provider:
        components.append(
            {
                "name": "default_llm_provider",
                "area": "provider",
                "status": normalize_provider_status(default_provider["status"]),
                "evidence": ["docs/A-v1.3_provider_acceptance_report.json"],
                "detail": build_provider_detail(default_provider),
            }
        )

    for name, result in provider_results.items():
        if name == "default_env":
            continue
        components.append(
            {
                "name": f"candidate_provider_{name}",
                "area": "provider",
                "status": normalize_provider_status(result["status"]),
                "evidence": ["docs/A-v1.3_provider_acceptance_report.json"],
                "detail": build_provider_detail(result),
            }
        )

    postgres_text = load_text(DOCS_DIR / "A-v1.0_postgresql_真实存储验收.md")
    components.append(
        {
            "name": "postgresql_structured_store",
            "area": "enterprise_enhancement",
            "status": "passed"
            if "postgres_ready= 1" in postgres_text and "ticket_status= 200" in postgres_text
            else "blocked",
            "evidence": ["docs/A-v1.0_postgresql_真实存储验收.md"],
            "detail": "真实 PostgreSQL 存储、工单与聊天记录已完成 API 级验收。",
        }
    )

    redis_text = load_text(DOCS_DIR / "A-v1.0_redis_真实缓存验收.md")
    components.append(
        {
            "name": "redis_cache",
            "area": "enterprise_enhancement",
            "status": "passed"
            if "redis_connected= True" in redis_text and "chat_statuses= 200 200" in redis_text
            else "blocked",
            "evidence": ["docs/A-v1.0_redis_真实缓存验收.md"],
            "detail": "Redis 缓存、docs_version 和会话状态已完成真实验收。",
        }
    )

    neo4j_text = load_text(DOCS_DIR / "A-v1.0_neo4j_真实联网验收.md")
    components.append(
        {
            "name": "neo4j_graph_retrieval",
            "area": "enterprise_enhancement",
            "status": "passed"
            if "neo4j_connected= True" in neo4j_text and "answer_has_citations= True" in neo4j_text
            else "blocked",
            "evidence": ["docs/A-v1.0_neo4j_真实联网验收.md"],
            "detail": "Neo4j 已完成外部连接、图谱写入和真实资料回查验收。",
        }
    )

    multimodal_text = load_text(DOCS_DIR / "A-v1.0_milvus_multimodal_真实验收.md")
    components.extend(build_multimodal_components(multimodal_text))
    return components


def build_multimodal_components(multimodal_text: str) -> list[dict]:
    return [
        {
            "name": "milvus_vector_store",
            "area": "enterprise_enhancement",
            "status": "passed"
            if "milvus_api_ingest_status= 200" in multimodal_text
            and "milvus_api_chat_status= 200" in multimodal_text
            else "blocked",
            "evidence": ["docs/A-v1.0_milvus_multimodal_真实验收.md"],
            "detail": "Milvus 向量库已完成真实 API 级验收。",
        },
        {
            "name": "mineru_real_pdf_parsing",
            "area": "multimodal",
            "status": "blocked" if "502 Bad Gateway" in multimodal_text else "passed",
            "evidence": ["docs/A-v1.0_milvus_multimodal_真实验收.md"],
            "detail": "MinerU 代码入口已完成，但当前本机 API health 仍被 502 阻塞。",
        },
        {
            "name": "paddleocr_real_runtime",
            "area": "multimodal",
            "status": "blocked" if "NotImplementedError" in multimodal_text else "passed",
            "evidence": ["docs/A-v1.0_milvus_multimodal_真实验收.md"],
            "detail": "PaddleOCR 已进入真实推理路径，但当前 Windows CPU 运行时仍阻塞。",
        },
        {
            "name": "vision_llm_real_runtime",
            "area": "multimodal",
            "status": "blocked" if "401 Unauthorized" in multimodal_text else "passed",
            "evidence": ["docs/A-v1.0_milvus_multimodal_真实验收.md"],
            "detail": "Vision LLM 真实接口已接入，但当前凭证认证失败。",
        },
    ]


def normalize_provider_status(status: str) -> str:
    if status == "accepted":
        return "passed"
    if status == "unstable":
        return "unstable"
    return "blocked"


def build_provider_detail(result: dict) -> str:
    runtime = result.get("runtime", {})
    provider = runtime.get("provider", "")
    model = runtime.get("model", "")
    if result["status"] == "accepted":
        return f"{provider}/{model} 已通过 grounded 主链验收。"
    if result["status"] == "unstable":
        return f"{provider}/{model} 可直连，但 grounded 主链仍不稳定。"
    return f"{provider}/{model} 当前仍未通过最小 grounded 验收。"


def summarize_components(components: list[dict]) -> dict:
    counts = {"passed": 0, "unstable": 0, "blocked": 0}
    for component in components:
        counts[component["status"]] = counts.get(component["status"], 0) + 1
    return {
        "component_count": len(components),
        "passed_count": counts["passed"],
        "unstable_count": counts["unstable"],
        "blocked_count": counts["blocked"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
