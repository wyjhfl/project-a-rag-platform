import os
from pathlib import Path

os.environ["STORAGE_BACKEND"] = "sqlite"
os.environ["VECTOR_BACKEND"] = "chroma"
os.environ["CACHE_ENABLED"] = "false"
os.environ["GRAPH_RETRIEVAL_ENABLED"] = "false"

from app.main import create_app
from fastapi.testclient import TestClient


def test_system_status_reports_llm_disabled_without_api_key(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "xiaomi_mimo")
    monkeypatch.setenv("LLM_MODEL", "mimo-test")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("LLM_BASE_URL", "")

    app = create_app(
        database_path=tmp_path / "app.db",
        chroma_dir=tmp_path / "chroma",
        seed_docs_dir=tmp_path / "missing_seed",
    )
    client = TestClient(app)

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "v1.0.5"
    assert payload["release_url"] == "https://github.com/wyjhfl/project-a-rag-platform/releases/tag/v1.0.5"
    assert payload["llm_provider"] == "xiaomi_mimo"
    assert payload["llm_model"] == "mimo-test"
    assert payload["llm_enabled"] is False


def test_ingest_can_select_real_manuals_directory(tmp_path: Path):
    seed_dir = tmp_path / "seed"
    real_dir = tmp_path / "real"
    seed_dir.mkdir()
    real_dir.mkdir()
    (seed_dir / "seed.txt").write_text("A100 E-17 供压异常。", encoding="utf-8")
    (real_dir / "real.txt").write_text("VFD580 A2B1 过流应检查电机负载。", encoding="utf-8")

    app = create_app(
        database_path=tmp_path / "app.db",
        chroma_dir=tmp_path / "chroma",
        seed_docs_dir=seed_dir,
        real_docs_dir=real_dir,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/documents/ingest",
        json={"docs_source": "real_manuals_sanitized"},
    )

    assert response.status_code == 200
    assert response.json()["document_count"] == 1
    chat = client.post("/api/v1/chat", json={"question": "VFD580 A2B1 怎么排查？"})
    assert "VFD580" in chat.json()["citations"][0]["content"]


def test_unknown_device_question_returns_insufficient_answer(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "a100.txt").write_text("A100 E-17 供压异常，检查过滤器。", encoding="utf-8")

    app = create_app(
        database_path=tmp_path / "app.db",
        chroma_dir=tmp_path / "chroma",
        seed_docs_dir=docs_dir,
    )
    client = TestClient(app)
    client.post("/api/v1/documents/ingest")

    response = client.post("/api/v1/chat", json={"question": "ZX-999 出现 Q-00 报警怎么修？"})

    assert response.status_code == 200
    payload = response.json()
    assert "资料不足" in payload["answer"] or "无法确认" in payload["answer"]
    assert payload["citations"] == []


def test_dangerous_operation_answer_is_safety_hardened(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ups.txt").write_text(
        "UPS-30K 电池冒烟属于高风险，需要人工确认。",
        encoding="utf-8",
    )

    app = create_app(
        database_path=tmp_path / "app.db",
        chroma_dir=tmp_path / "chroma",
        seed_docs_dir=docs_dir,
    )
    client = TestClient(app)
    client.post("/api/v1/documents/ingest")

    response = client.post(
        "/api/v1/chat",
        json={"question": "UPS-30K 电池冒烟，可以直接重启吗？"},
    )

    answer = response.json()["answer"]
    assert "禁止" in answer or "不要" in answer
    assert "人工" in answer


def test_ticket_list_and_evaluation_api_are_available(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "ups.txt").write_text(
        "UPS-30K 电池冒烟属于高风险，需要人工确认。",
        encoding="utf-8",
    )
    cases = tmp_path / "cases.json"
    cases.write_text(
        '[{"id":"case-1","question":"UPS-30K 电池冒烟怎么办？",'
        '"expected_keywords":["电池"],"expected_source":"ups.txt","category":"safety"}]',
        encoding="utf-8",
    )

    app = create_app(
        database_path=tmp_path / "app.db",
        chroma_dir=tmp_path / "chroma",
        seed_docs_dir=docs_dir,
    )
    client = TestClient(app)
    client.post("/api/v1/documents/ingest")
    client.post(
        "/api/v1/tickets/start",
        json={"question": "UPS-30K 电池冒烟怎么办？", "idempotency_key": "list-ticket"},
    )

    tickets = client.get("/api/v1/tickets")
    evaluation = client.post(
        "/api/v1/evaluations/run",
        json={
            "evaluation_type": "regression",
            "cases_path": str(cases),
            "docs_source": "seed_docs",
        },
    )

    assert tickets.status_code == 200
    assert len(tickets.json()) == 1
    assert evaluation.status_code == 200
    assert evaluation.json()["summary"]["case_count"] == 1
