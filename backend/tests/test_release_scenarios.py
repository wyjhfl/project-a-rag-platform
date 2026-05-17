import json
from pathlib import Path

from app.main import create_app
from fastapi.testclient import TestClient

PROJECT_DIR = Path(__file__).resolve().parents[2]
REAL_DOCS_DIR = PROJECT_DIR / "data" / "real_manuals_sanitized"
SCENARIOS_PATH = PROJECT_DIR / "data" / "eval" / "release_scenarios_v1.json"


def _client(tmp_path: Path) -> TestClient:
    app = create_app(
        database_path=tmp_path / "release.db",
        chroma_dir=tmp_path / "release_chroma",
        real_docs_dir=REAL_DOCS_DIR,
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/documents/ingest",
        json={"docs_source": "real_manuals_sanitized"},
    )
    assert response.status_code == 200
    assert response.json()["document_count"] >= 5
    return client


def _scenario(flow: str) -> dict:
    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    return next(item for item in scenarios if item["flow"] == flow)


def test_release_scenarios_file_covers_required_enterprise_flows():
    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))

    assert {item["flow"] for item in scenarios} == {
        "normal_diagnosis",
        "high_risk_hitl",
        "unknown_model_refusal",
        "parts_ticket",
        "session_resolution",
    }
    assert all(item["id"].startswith("release-") for item in scenarios)


def test_normal_fault_diagnosis_returns_same_device_citation(tmp_path: Path):
    client = _client(tmp_path)
    scenario = _scenario("normal_diagnosis")

    response = client.post("/api/v1/chat", json={"question": scenario["question"]})

    assert response.status_code == 200
    payload = response.json()
    joined = payload["answer"] + "\n" + "\n".join(c["content"] for c in payload["citations"])
    assert payload["citations"]
    assert "A100" in joined
    assert "E-17" in joined
    assert "过滤器" in joined
    assert payload["citations"][0]["source"] == "real_air_compressor_a100_faults.md"


def test_high_risk_ups_flow_adds_safety_warning_and_pauses_ticket(tmp_path: Path):
    client = _client(tmp_path)
    scenario = _scenario("high_risk_hitl")

    chat = client.post("/api/v1/chat", json={"question": scenario["question"]})
    ticket = client.post(
        "/api/v1/tickets/start",
        json={
            "question": scenario["question"],
            "idempotency_key": "release-high-risk-ups",
        },
    )

    assert chat.status_code == 200
    answer = chat.json()["answer"]
    assert "禁止" in answer
    assert "停机" in answer
    assert "人工" in answer
    assert ticket.status_code == 200
    ticket_payload = ticket.json()
    assert ticket_payload["ticket"]["status"] == "NEED_HUMAN"
    assert ticket_payload["next_action"] == "wait_for_human"


def test_unknown_model_is_rejected_as_insufficient_material(tmp_path: Path):
    client = _client(tmp_path)
    scenario = _scenario("unknown_model_refusal")

    response = client.post("/api/v1/chat", json={"question": scenario["question"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["insufficient"] is True
    assert "资料不足" in payload["answer"]
    assert payload["citations"] == []


def test_parts_ticket_uses_inventory_candidates_and_can_close(tmp_path: Path):
    client = _client(tmp_path)
    scenario = _scenario("parts_ticket")

    start = client.post(
        "/api/v1/tickets/start",
        json={
            "question": scenario["question"],
            "idempotency_key": "release-parts-cw200",
        },
    )

    assert start.status_code == 200
    started = start.json()
    ticket = started["ticket"]
    assert ticket["device_model"] == "CW200"
    assert ticket["status"] == "NEED_PARTS"
    assert any(part["name"] == "压力传感器" for part in ticket["required_parts"])

    close = client.post(
        f"/api/v1/tickets/{ticket['ticket_id']}/close",
        json={"closed_by": "李工"},
    )

    assert close.status_code == 200
    assert close.json()["status"] == "CLOSED"
    assert close.json()["closed_by"] == "李工"


def test_session_question_resolves_pronoun_to_previous_device_and_fault(tmp_path: Path):
    client = _client(tmp_path)
    scenario = _scenario("session_resolution")
    first_question, second_question = scenario["questions"]

    first = client.post(
        "/api/v1/chat/session",
        json={"session_id": "release-session-a100", "question": first_question},
    )
    second = client.post(
        "/api/v1/chat/session",
        json={"session_id": "release-session-a100", "question": second_question},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert "A100" in second.json()["resolved_question"]
    assert "E-17" in second.json()["resolved_question"]
