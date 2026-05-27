import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["STORAGE_BACKEND"] = "sqlite"
os.environ["VECTOR_BACKEND"] = "chroma"
os.environ["CACHE_ENABLED"] = "false"
os.environ["GRAPH_RETRIEVAL_ENABLED"] = "false"

from app.main import create_app


def test_acceptance_overview_exposes_panels(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "seed.txt").write_text("A100 E-17 先检查进气过滤器。", encoding="utf-8")

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
