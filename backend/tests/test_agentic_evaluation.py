import os
from pathlib import Path

os.environ["STORAGE_BACKEND"] = "sqlite"
os.environ["VECTOR_BACKEND"] = "chroma"
os.environ["CACHE_ENABLED"] = "false"
os.environ["GRAPH_RETRIEVAL_ENABLED"] = "false"

from app.main import create_app
from fastapi.testclient import TestClient


def test_agentic_evaluation_reports_decision_trace_and_retry_metrics(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "vfd_4500.txt").write_text(
        "VFD-4500 fault OC-17: inspect motor load and output cable.",
        encoding="utf-8",
    )
    (docs_dir / "ups_30k.txt").write_text(
        "UPS-30K battery smoke and odor are high risk. Stop operation and escalate to human review.",
        encoding="utf-8",
    )
    cases = tmp_path / "agentic_cases.json"
    cases.write_text(
        """[
          {"id":"ok","question":"VFD-4500 OC-17 alarm","expected_decision":"answer"},
          {"id":"risk","question":"UPS-30K battery smoke and odor","expected_decision":"escalate"},
          {"id":"unknown","question":"ZX-999 Q-00 alarm","expected_decision":"refuse"}
        ]""",
        encoding="utf-8",
    )

    app = create_app(
        database_path=tmp_path / "app.db",
        chroma_dir=tmp_path / "chroma",
        seed_docs_dir=docs_dir,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/evaluations/run",
        json={
            "evaluation_type": "agentic",
            "cases_path": str(cases),
            "docs_source": "seed_docs",
        },
    )

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary["case_count"] == 3
    assert "citation_accuracy" in summary
    assert "refusal_accuracy" in summary
    assert "escalation_accuracy" in summary
    assert "trace_completeness" in summary
    assert "retrieval_retry_rate" in summary
