import os
from pathlib import Path

os.environ["STORAGE_BACKEND"] = "sqlite"
os.environ["VECTOR_BACKEND"] = "chroma"
os.environ["CACHE_ENABLED"] = "false"
os.environ["GRAPH_RETRIEVAL_ENABLED"] = "false"

from app.main import create_app
from app.rag.agentic import AgenticRetriever
from app.rag.diagnosis_agent import DEFAULT_PLAN
from app.rag.llm import LLMGenerationResult
from fastapi.testclient import TestClient


class FakeLLMGenerator:
    """Deterministic stand-in for an OpenAI-compatible chat provider."""

    def __init__(self, risk_verdict: str = "low") -> None:
        self.risk_verdict = risk_verdict
        self.prompts: list[str] = []

    @property
    def is_enabled(self) -> bool:
        return True

    def generate(self, question: str, context: str, prompt: str = "") -> LLMGenerationResult:
        self.prompts.append(prompt)
        if "诊断计划" in prompt:
            return LLMGenerationResult(
                answer="1. 校验请求安全性\n2. 检索设备知识库\n3. 核对引用证据\n4. 输出风险决策"
            )
        if "high 或 low" in prompt:
            return LLMGenerationResult(answer=self.risk_verdict)
        return LLMGenerationResult(answer="", error="answer generation disabled in test")


def _client_with_docs(tmp_path: Path, text: str, filename: str = "manual.txt") -> TestClient:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / filename).write_text(text, encoding="utf-8")
    app = create_app(
        database_path=tmp_path / "app.db",
        chroma_dir=tmp_path / "chroma",
        seed_docs_dir=docs_dir,
    )
    client = TestClient(app)
    assert client.post("/api/v1/documents/ingest").status_code == 200
    return client


def test_llm_plan_replaces_static_plan(tmp_path: Path):
    client = _client_with_docs(
        tmp_path,
        "VFD-4500 fault OC-17: inspect motor load, output cable, and cooling fan.",
        "vfd_4500.txt",
    )
    fake_llm = FakeLLMGenerator()
    client.app.state.pipeline.llm_generator = fake_llm

    response = client.post(
        "/api/v1/agent/diagnose",
        json={"question": "VFD-4500 has OC-17 alarm. What should I inspect?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "answer"
    assert payload["plan"] == [
        "校验请求安全性",
        "检索设备知识库",
        "核对引用证据",
        "输出风险决策",
    ]
    assert payload["plan"] != list(DEFAULT_PLAN)
    assert any("诊断计划" in prompt for prompt in fake_llm.prompts)


def test_llm_risk_classifier_escalates_beyond_keyword_floor(tmp_path: Path):
    client = _client_with_docs(
        tmp_path,
        "CW200 chiller water temperature 90 degrees: check condenser fan and water pump.",
        "cw200.txt",
    )
    client.app.state.pipeline.llm_generator = FakeLLMGenerator(risk_verdict="high")

    response = client.post(
        "/api/v1/agent/diagnose",
        json={
            "question": "CW200 water temperature reached 90 degrees, can it keep running?",
            "create_ticket_on_escalation": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "escalate"
    assert payload["ticket_id"]
    assert payload["quality"]["risk_level"] == "high"
    risk_call = next(call for call in payload["tool_calls"] if call["tool"] == "risk_check")
    assert risk_call["outputs"]["classifier"] == "llm+keyword"


def test_keyword_floor_still_escalates_when_llm_says_low(tmp_path: Path):
    client = _client_with_docs(
        tmp_path,
        "UPS-30K battery smoke and odor are high risk. Stop operation and escalate to human review.",
        "ups_30k.txt",
    )
    client.app.state.pipeline.llm_generator = FakeLLMGenerator(risk_verdict="low")

    response = client.post(
        "/api/v1/agent/diagnose",
        json={"question": "UPS-30K battery has smoke and odor. Can I restart it?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "escalate"
    assert payload["quality"]["risk_level"] == "high"


def test_agentic_retriever_prefers_llm_rewriter_with_heuristic_fallback():
    preferred = AgenticRetriever(llm_rewriter=lambda question: "CW200 冷凝器 压差 报警 排查")
    assert preferred.rewrite_query("冷水机压差不稳") == "CW200 冷凝器 压差 报警 排查"

    def broken_rewriter(question: str) -> str:
        raise RuntimeError("provider down")

    degraded = AgenticRetriever(llm_rewriter=broken_rewriter)
    heuristic = degraded.rewrite_query("A100 空压机过热跳停")
    assert "A100 空压机过热跳停" in heuristic

    blank = AgenticRetriever(llm_rewriter=lambda question: "")
    assert blank.rewrite_query("UPS 电池鼓包") == AgenticRetriever().rewrite_query("UPS 电池鼓包")
