from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

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
    "鍐掔儫",
    "寮傚懗",
    "榧撳寘",
    "楂樺帇",
    "甯﹀帇",
    "閲嶅惎",
]


class DiagnosisAgent:
    def __init__(self, pipeline, store, ticket_workflow) -> None:
        self.pipeline = pipeline
        self.store = store
        self.ticket_workflow = ticket_workflow

    def diagnose(
        self,
        *,
        question: str,
        top_k: int = 4,
        session_id: str | None = None,
        create_ticket_on_escalation: bool = True,
    ) -> AgentDiagnoseResponse:
        started = time.monotonic()
        tool_calls: list[AgentToolCall] = []
        plan = [
            "Inspect prompt-injection and authorization intent.",
            "Route and enhance the retrieval query.",
            "Search the grounded knowledge base.",
            "Check operational risk and decide answer/refuse/escalate.",
        ]

        security = self.pipeline.security_guard.inspect(question)
        tool_calls.append(
            AgentToolCall(
                tool="security_check",
                status="blocked" if security.decision == SecurityDecision.BLOCK else "passed",
                summary=security.decision.value,
                inputs={"question": question},
                outputs={"decision": security.decision.value},
            )
        )
        if security.decision == SecurityDecision.BLOCK:
            answer = "Request refused because it looks like prompt injection or an override instruction."
            return self._finish(
                question=question,
                decision="refuse",
                answer=answer,
                plan=plan,
                tool_calls=tool_calls,
                citations=[],
                risk_level="low",
                latency_ms=self._elapsed_ms(started),
                raw_trace={},
            )

        enhanced = self.pipeline.query_router.build_enhanced_query(
            question,
            self.pipeline.query_enhancer,
        )
        tool_calls.append(
            AgentToolCall(
                tool="query_route",
                status="completed",
                summary=enhanced.route.value,
                inputs={"question": question},
                outputs={
                    "route": enhanced.route.value,
                    "retrieval_queries": enhanced.retrieval_queries,
                },
            )
        )

        chunks = self.pipeline.search(question, top_k=top_k)
        agentic = self.pipeline.last_agentic_result
        if agentic and agentic.retried:
            get_metrics().record_rag_retrieval_retry()
        tool_calls.append(
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
            )
        )

        response = self.pipeline.answer(question, top_k=top_k)
        raw_trace = self.pipeline.last_trace or {}
        risk_level = self._risk_level(question, response.answer)
        tool_calls.append(
            AgentToolCall(
                tool="risk_check",
                status="completed",
                summary=risk_level,
                inputs={"question": question},
                outputs={"risk_level": risk_level},
            )
        )

        if response.insufficient or not response.citations:
            decision = "refuse"
        elif risk_level == "high":
            decision = "escalate"
        else:
            decision = "answer"

        ticket_id = None
        if decision == "escalate" and create_ticket_on_escalation:
            ticket = self.ticket_workflow.start(
                question=question,
                idempotency_key=f"agent-{session_id or uuid.uuid4().hex}",
            )
            ticket_id = ticket.ticket.ticket_id
            tool_calls.append(
                AgentToolCall(
                    tool="ticket_escalation",
                    status="created",
                    summary=ticket.next_action,
                    inputs={"question": question},
                    outputs={"ticket_id": ticket_id, "next_action": ticket.next_action},
                )
            )

        return self._finish(
            question=question,
            decision=decision,
            answer=response.answer,
            plan=plan,
            tool_calls=tool_calls,
            citations=response.citations,
            risk_level=risk_level,
            latency_ms=self._elapsed_ms(started),
            raw_trace=raw_trace,
            ticket_id=ticket_id,
            insufficient=response.insufficient,
            safety_warning=response.safety_warning,
        )

    def _finish(
        self,
        *,
        question: str,
        decision: str,
        answer: str,
        plan: list[str],
        tool_calls: list[AgentToolCall],
        citations: list[Citation],
        risk_level: str,
        latency_ms: float,
        raw_trace: dict,
        ticket_id: str | None = None,
        insufficient: bool = False,
        safety_warning: bool = False,
    ) -> AgentDiagnoseResponse:
        agentic = self.pipeline.last_agentic_result
        trace = self._build_trace(
            question=question,
            decision=decision,
            tool_calls=tool_calls,
            citations=citations,
            latency_ms=latency_ms,
            raw_trace=raw_trace,
            insufficient=insufficient,
            safety_warning=safety_warning,
        )
        trace_id = self.store.save_rag_trace(trace)
        get_metrics().record_agent_decision(decision)
        get_metrics().record_rag_trace()
        return AgentDiagnoseResponse(
            decision=decision,
            answer=answer,
            plan=plan,
            tool_calls=tool_calls,
            citations=citations,
            quality=AgentQuality(
                retrieval_score=agentic.quality_score if agentic else 0.0,
                citation_count=len(citations),
                faithfulness_hint="grounded" if citations and decision != "refuse" else "insufficient",
                risk_level=risk_level,
            ),
            trace_id=trace_id,
            ticket_id=ticket_id,
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

    def _risk_level(self, question: str, answer: str) -> str:
        text = f"{question}\n{answer}".lower()
        return "high" if any(term.lower() in text for term in HIGH_RISK_TERMS) else "low"

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return round((time.monotonic() - started) * 1000, 2)
