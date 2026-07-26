from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.metrics import get_metrics
from app.models import (
    AgentDiagnoseResponse,
    AgentQuality,
    AgentToolCall,
    Citation,
)
from app.rag.security import SecurityDecision
from app.rag.tracing import summarize_chunks

HIGH_RISK_TERMS = [
    "smoke",
    "odor",
    "burning",
    "high voltage",
    "battery swelling",
    "restart",
    "冒烟",
    "异味",
    "鼓包",
    "高压",
    "带电",
    "重启",
]

DEFAULT_PLAN = [
    "Inspect prompt-injection and authorization intent.",
    "Route and enhance the retrieval query.",
    "Search the grounded knowledge base.",
    "Check operational risk and decide answer/refuse/escalate.",
]

_PLAN_PROMPT = (
    "你是设备售后诊断 Agent 的规划器。针对下面的故障咨询，"
    "输出 3 到 5 步简短的诊断计划，每行一步，不要编号以外的内容，"
    "步骤覆盖：安全校验、检索策略、证据核对、风险决策。\n"
    "故障咨询：{question}\n"
    "只输出步骤本身，每行一步。"
)

_RISK_PROMPT = (
    "你是设备售后安全审查员。判断下面的问题与回答是否涉及高风险现场操作"
    "（例如冒烟、异味、电池鼓包、带电、高压、强制重启、继续带载运行）。\n"
    "问题：{question}\n"
    "回答：{answer}\n"
    "只输出一个词：high 或 low。"
)


class DiagnosisState(TypedDict, total=False):
    question: str
    top_k: int
    session_id: str | None
    create_ticket_on_escalation: bool
    started: float
    plan: list[str]
    plan_source: str
    tool_calls: list[AgentToolCall]
    security_blocked: bool
    answer: str
    citations: list[Citation]
    insufficient: bool
    safety_warning: bool
    raw_trace: dict
    risk_level: str
    risk_source: str
    decision: str
    ticket_id: str | None


class DiagnosisAgent:
    """LangGraph-driven diagnosis controller.

    The graph wires security -> plan -> route -> retrieve -> risk with conditional
    edges for refuse/escalate outcomes. When an LLM provider is configured the
    plan and risk assessment are LLM-driven; without one the agent degrades to
    deterministic heuristics so offline demos and CI stay reproducible. The
    keyword risk floor is always applied: an LLM can raise the risk level but
    never lower it below the deterministic assessment.
    """

    def __init__(self, pipeline, store, ticket_workflow) -> None:
        self.pipeline = pipeline
        self.store = store
        self.ticket_workflow = ticket_workflow
        self.graph = self._build_graph()

    def diagnose(
        self,
        *,
        question: str,
        top_k: int = 4,
        session_id: str | None = None,
        create_ticket_on_escalation: bool = True,
    ) -> AgentDiagnoseResponse:
        state: DiagnosisState = self.graph.invoke(
            {
                "question": question,
                "top_k": top_k,
                "session_id": session_id,
                "create_ticket_on_escalation": create_ticket_on_escalation,
                "started": time.monotonic(),
                "plan": list(DEFAULT_PLAN),
                "plan_source": "static",
                "tool_calls": [],
                "citations": [],
                "raw_trace": {},
                "risk_level": "low",
                "ticket_id": None,
            }
        )
        return self._finish(state)

    # --- graph assembly -------------------------------------------------

    def _build_graph(self):
        graph = StateGraph(DiagnosisState)
        graph.add_node("security", self._security_node)
        graph.add_node("plan", self._plan_node)
        graph.add_node("route", self._route_node)
        graph.add_node("retrieve", self._retrieve_node)
        graph.add_node("risk", self._risk_node)
        graph.add_node("escalate", self._escalate_node)

        graph.add_edge(START, "security")
        graph.add_conditional_edges(
            "security",
            lambda state: "blocked" if state.get("security_blocked") else "passed",
            {"blocked": END, "passed": "plan"},
        )
        graph.add_edge("plan", "route")
        graph.add_edge("route", "retrieve")
        graph.add_edge("retrieve", "risk")
        graph.add_conditional_edges(
            "risk",
            lambda state: state.get("decision", "answer"),
            {"answer": END, "refuse": END, "escalate": "escalate"},
        )
        graph.add_edge("escalate", END)
        return graph.compile()

    # --- nodes -----------------------------------------------------------

    def _security_node(self, state: DiagnosisState) -> DiagnosisState:
        question = state["question"]
        security = self.pipeline.security_guard.inspect(question)
        blocked = security.decision == SecurityDecision.BLOCK
        tool_calls = [
            *state["tool_calls"],
            AgentToolCall(
                tool="security_check",
                status="blocked" if blocked else "passed",
                summary=security.decision.value,
                inputs={"question": question},
                outputs={"decision": security.decision.value},
            ),
        ]
        update: DiagnosisState = {
            "tool_calls": tool_calls,
            "security_blocked": blocked,
        }
        if blocked:
            update.update(
                decision="refuse",
                answer=(
                    "Request refused because it looks like prompt injection "
                    "or an override instruction."
                ),
                citations=[],
                risk_level="low",
            )
        return update

    def _plan_node(self, state: DiagnosisState) -> DiagnosisState:
        plan = self._llm_plan(state["question"])
        if plan:
            return {"plan": plan, "plan_source": "llm"}
        return {"plan": list(DEFAULT_PLAN), "plan_source": "static"}

    def _route_node(self, state: DiagnosisState) -> DiagnosisState:
        question = state["question"]
        enhanced = self.pipeline.query_router.build_enhanced_query(
            question,
            self.pipeline.query_enhancer,
        )
        tool_calls = [
            *state["tool_calls"],
            AgentToolCall(
                tool="query_route",
                status="completed",
                summary=enhanced.route.value,
                inputs={"question": question},
                outputs={
                    "route": enhanced.route.value,
                    "retrieval_queries": enhanced.retrieval_queries,
                },
            ),
        ]
        return {"tool_calls": tool_calls}

    def _retrieve_node(self, state: DiagnosisState) -> DiagnosisState:
        question = state["question"]
        top_k = state["top_k"]
        chunks = self.pipeline.search(question, top_k=top_k)
        agentic = self.pipeline.last_agentic_result
        if agentic and agentic.retried:
            get_metrics().record_rag_retrieval_retry()
        tool_calls = [
            *state["tool_calls"],
            AgentToolCall(
                tool="knowledge_search",
                status="completed" if chunks else "empty",
                summary=f"{len(chunks)} chunks retrieved",
                inputs={"question": question, "top_k": top_k},
                outputs={
                    "chunks": summarize_chunks(chunks),
                    "retrieval_score": agentic.quality_score if agentic else 0.0,
                    "retrieval_attempts": agentic.retrieval_attempts if agentic else 1,
                    "retry_reason": agentic.retry_reason if agentic else "",
                    "context_sufficient": agentic.context_sufficient if agentic else bool(chunks),
                    "rewritten_query": agentic.rewritten_query if agentic else "",
                },
            ),
        ]

        response = self.pipeline.answer(question, top_k=top_k)
        return {
            "tool_calls": tool_calls,
            "answer": response.answer,
            "citations": response.citations,
            "insufficient": response.insufficient,
            "safety_warning": response.safety_warning,
            "raw_trace": self.pipeline.last_trace or {},
        }

    def _risk_node(self, state: DiagnosisState) -> DiagnosisState:
        question = state["question"]
        answer = state.get("answer", "")
        keyword_level = self._keyword_risk_level(question, answer)
        llm_level = self._llm_risk_level(question, answer)
        risk_level = "high" if "high" in (keyword_level, llm_level) else "low"
        risk_source = "llm+keyword" if llm_level else "keyword"

        tool_calls = [
            *state["tool_calls"],
            AgentToolCall(
                tool="risk_check",
                status="completed",
                summary=risk_level,
                inputs={"question": question},
                outputs={"risk_level": risk_level, "classifier": risk_source},
            ),
        ]

        if state.get("insufficient") or not state.get("citations"):
            decision = "refuse"
        elif risk_level == "high":
            decision = "escalate"
        else:
            decision = "answer"

        return {
            "tool_calls": tool_calls,
            "risk_level": risk_level,
            "risk_source": risk_source,
            "decision": decision,
        }

    def _escalate_node(self, state: DiagnosisState) -> DiagnosisState:
        if not state.get("create_ticket_on_escalation", True):
            return {}
        question = state["question"]
        ticket = self.ticket_workflow.start(
            question=question,
            idempotency_key=f"agent-{state.get('session_id') or uuid.uuid4().hex}",
        )
        ticket_id = ticket.ticket.ticket_id
        tool_calls = [
            *state["tool_calls"],
            AgentToolCall(
                tool="ticket_escalation",
                status="created",
                summary=ticket.next_action,
                inputs={"question": question},
                outputs={"ticket_id": ticket_id, "next_action": ticket.next_action},
            ),
        ]
        return {"tool_calls": tool_calls, "ticket_id": ticket_id}

    # --- LLM-in-the-loop helpers ------------------------------------------

    def _llm_plan(self, question: str) -> list[str]:
        generator = getattr(self.pipeline, "llm_generator", None)
        if not generator or not generator.is_enabled:
            return []
        result = generator.generate(
            question=question,
            context="",
            prompt=_PLAN_PROMPT.format(question=question),
        )
        if result.error or not result.answer.strip():
            return []
        steps = []
        for line in result.answer.splitlines():
            step = line.strip().lstrip("-*").strip()
            step = step.lstrip("0123456789.、) ").strip()
            if step:
                steps.append(step)
        if len(steps) < 3:
            return []
        return steps[:5]

    def _llm_risk_level(self, question: str, answer: str) -> str:
        generator = getattr(self.pipeline, "llm_generator", None)
        if not generator or not generator.is_enabled:
            return ""
        result = generator.generate(
            question=question,
            context="",
            prompt=_RISK_PROMPT.format(question=question, answer=answer[:800]),
        )
        if result.error:
            return ""
        verdict = result.answer.strip().lower()
        if "high" in verdict:
            return "high"
        if "low" in verdict:
            return "low"
        return ""

    def _keyword_risk_level(self, question: str, answer: str) -> str:
        text = f"{question}\n{answer}".lower()
        return "high" if any(term.lower() in text for term in HIGH_RISK_TERMS) else "low"

    # --- response assembly -------------------------------------------------

    def _finish(self, state: DiagnosisState) -> AgentDiagnoseResponse:
        question = state["question"]
        decision = state.get("decision", "answer")
        citations = state.get("citations", [])
        latency_ms = self._elapsed_ms(state["started"])
        agentic = self.pipeline.last_agentic_result if not state.get("security_blocked") else None
        trace = self._build_trace(
            question=question,
            decision=decision,
            tool_calls=state["tool_calls"],
            citations=citations,
            latency_ms=latency_ms,
            raw_trace=state.get("raw_trace", {}),
            insufficient=state.get("insufficient", False),
            safety_warning=state.get("safety_warning", False),
        )
        trace_id = self.store.save_rag_trace(trace)
        get_metrics().record_agent_decision(decision)
        get_metrics().record_rag_trace()
        return AgentDiagnoseResponse(
            decision=decision,
            answer=state.get("answer", ""),
            plan=state.get("plan", list(DEFAULT_PLAN)),
            tool_calls=state["tool_calls"],
            citations=citations,
            quality=AgentQuality(
                retrieval_score=agentic.quality_score if agentic else 0.0,
                citation_count=len(citations),
                faithfulness_hint="grounded" if citations and decision != "refuse" else "insufficient",
                risk_level=state.get("risk_level", "low"),
            ),
            trace_id=trace_id,
            ticket_id=state.get("ticket_id"),
        )

    def _build_trace(
        self,
        *,
        question: str,
        decision: str,
        tool_calls: list[AgentToolCall],
        citations: list[Citation],
        latency_ms: float,
        raw_trace: dict,
        insufficient: bool,
        safety_warning: bool,
    ) -> dict:
        route = ""
        rewritten_query = ""
        retrieved_chunks: list[dict[str, Any]] = []
        selected_chunks: list[dict[str, Any]] = []
        for event in raw_trace.get("events", []):
            if event.get("name") == "query_route":
                route = str(event.get("outputs", {}).get("route", ""))
            if event.get("name") == "agentic_search":
                outputs = event.get("outputs", {})
                rewritten_query = str(outputs.get("rewritten_query", ""))
                retrieved_chunks = list(outputs.get("chunks", []))
            if event.get("name") == "answer_context_filter":
                selected_chunks = list(event.get("outputs", {}).get("selected_chunks", []))

        if not selected_chunks:
            selected_chunks = [
                {
                    "source": citation.source,
                    "chunk_index": citation.chunk_index,
                    "preview": citation.content[:120],
                }
                for citation in citations
            ]

        return {
            "trace_id": f"TRACE-{uuid.uuid4().hex[:12].upper()}",
            "question": question,
            "decision": decision,
            "route": route,
            "rewritten_query": rewritten_query,
            "retrieved_chunks": retrieved_chunks,
            "selected_chunks": selected_chunks,
            "citations": [citation.model_dump() for citation in citations],
            "tool_calls": [call.model_dump() for call in tool_calls],
            "latency_ms": latency_ms,
            "token_usage": {},
            "safety_warning": safety_warning,
            "insufficient": insufficient,
            "raw_trace": raw_trace,
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        }

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return round((time.monotonic() - started) * 1000, 2)
