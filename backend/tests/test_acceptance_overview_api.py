import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["STORAGE_BACKEND"] = "sqlite"
os.environ["VECTOR_BACKEND"] = "chroma"
os.environ["CACHE_ENABLED"] = "false"
os.environ["GRAPH_RETRIEVAL_ENABLED"] = "false"

from app.main import create_app


def _write_acceptance_fixtures(docs_dir: Path) -> None:
    """Create minimal acceptance report fixtures so the overview API returns real data."""

    # --- multimodal panel ---
    (docs_dir / "A-v1.5_multimodal_acceptance_report.json").write_text(
        json.dumps({
            "summary": {
                "component_count": 4,
                "status_counts": {"passed": 2, "runtime_incompatible": 1, "runtime_resource_blocked": 1},
            },
            "components": [
                {"name": "vision_llm", "status": "passed", "detail": {"diagnosis": "ok"}},
                {"name": "mineru_linux", "status": "passed", "detail": {"diagnosis": "ok"}},
                {"name": "paddleocr", "status": "runtime_incompatible", "detail": {"error": "lib issue"}},
                {"name": "sidecar", "status": "runtime_resource_blocked", "detail": {"error": "no GPU"}},
            ],
        }),
        encoding="utf-8",
    )

    # --- evaluation panel ---
    (docs_dir / "A-real-data_regression_report.json").write_text(
        json.dumps({
            "summary": {"case_count": 30, "passed_count": 29, "source_hit_count": 28},
            "results": [],
        }),
        encoding="utf-8",
    )

    (docs_dir / "A-real-data_ragas_report.json").write_text(
        json.dumps({
            "summary": {
                "case_count": 30,
                "average_scores": {"faithfulness": 0.85, "context_precision": 0.78},
            },
            "results": [],
        }),
        encoding="utf-8",
    )

    (docs_dir / "A-real-data_adversarial_report.json").write_text(
        json.dumps({
            "summary": {"case_count": 10, "passed_count": 10},
            "results": [{"id": "adv-1", "passed": True, "category": "injection"}],
        }),
        encoding="utf-8",
    )

    # RAGAS report with trace data for trace_cases
    (docs_dir / "A-v1.2_ragas_report.json").write_text(
        json.dumps({
            "summary": {
                "case_count": 5,
                "low_score_cases": [
                    {
                        "id": "case-42",
                        "likely_issue": "retrieval_gap",
                        "faithfulness": 0.3,
                        "context_precision": 0.2,
                    }
                ],
            },
            "results": [
                {
                    "id": "case-42",
                    "question": "如何更换滤芯？",
                    "trace": {
                        "events": [
                            {
                                "name": "retrieve",
                                "inputs": {"query": "更换滤芯"},
                                "outputs": {"decision": "hybrid"},
                                "metadata": {"selected_count": 5},
                            },
                            {
                                "name": "generate",
                                "inputs": {"context": "..."},
                                "outputs": {"answer_source": "llm"},
                                "metadata": {"llm_used": "deepseek_chat"},
                            },
                        ]
                    },
                }
            ],
        }),
        encoding="utf-8",
    )

    # --- badcases panel ---
    (docs_dir / "A-real-data_bad_cases.md").write_text(
        "## A100 进气过滤器误判\n\n模型将进气过滤器更换周期回答错误，实际为 500 小时。\n",
        encoding="utf-8",
    )


def test_acceptance_overview_exposes_panels(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "seed.txt").write_text("A100 E-17 先检查进气过滤器。", encoding="utf-8")
    _write_acceptance_fixtures(docs_dir)

    app = create_app(
        database_path=tmp_path / "app.db",
        chroma_dir=tmp_path / "chroma",
        seed_docs_dir=docs_dir,
    )
    client = TestClient(app)

    response = client.get("/api/v1/acceptance/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "v2.0"
    assert payload["status"] in {"ok", "warning"}
    assert len(payload["panels"]) == 4
    panel_map = {panel["key"]: panel for panel in payload["panels"]}
    assert {"provider", "multimodal", "evaluation", "badcases"} <= set(panel_map)
    assert panel_map["provider"]["status"] == "passed"
    assert panel_map["multimodal"]["metrics"]["passed"] == "2"
    regression_parts = panel_map["evaluation"]["metrics"]["regression"].split("/")
    assert len(regression_parts) == 2
    regression_passed = int(regression_parts[0])
    regression_total = int(regression_parts[1])
    assert regression_total >= 30
    assert regression_passed >= 28
    assert int(panel_map["badcases"]["metrics"]["real_data_cases"]) >= 1
    assert panel_map["provider"]["breakdown"]
    assert panel_map["evaluation"]["chart"]
    assert panel_map["badcases"]["highlights"]
    assert panel_map["evaluation"]["trace_cases"]
    first_trace_event = panel_map["evaluation"]["trace_cases"][0]["events"][0]
    assert "inputs" in first_trace_event
    assert "outputs" in first_trace_event
    assert "raw_trace" in panel_map["evaluation"]["trace_cases"][0]
