import re
import uuid
from datetime import UTC, datetime
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.models import Citation
from app.rag.pipeline import RagPipeline
from app.storage.base import Store
from app.ticketing.models import (
    PartCandidate,
    RiskLevel,
    TicketRecord,
    TicketStatus,
    TicketWorkflowResult,
)
from app.ticketing.parts import query_parts

HIGH_RISK_KEYWORDS = [
    "冒烟",
    "异味",
    "鼓包",
    "烧焦",
    "强电",
    "触电",
    "电池",
    "泄漏",
    "旁路",
    "带压",
]


class TicketGraphState(TypedDict, total=False):
    question: str
    idempotency_key: str
    diagnosis: str
    citations: list[Citation]
    device_model: str | None
    fault_code: str | None
    risk_level: RiskLevel
    required_parts: list[PartCandidate]
    human_required: bool
    status: TicketStatus
    ticket: TicketRecord
    next_action: str


class TicketWorkflowService:
    def __init__(self, store: Store, rag_pipeline: RagPipeline) -> None:
        self.store = store
        self.rag_pipeline = rag_pipeline
        self.graph = self._build_graph()

    def start(self, question: str, idempotency_key: str) -> TicketWorkflowResult:
        existing = self.store.get_ticket_by_idempotency_key(idempotency_key)
        if existing:
            ticket = TicketRecord.model_validate(existing)
            return TicketWorkflowResult(ticket=ticket, next_action=self._next_action(ticket))

        state = self.graph.invoke({"question": question, "idempotency_key": idempotency_key})
        return TicketWorkflowResult(ticket=state["ticket"], next_action=state["next_action"])

    def _diagnose_node(self, state: TicketGraphState) -> TicketGraphState:
        question = state["question"]
        diagnosis = self.rag_pipeline.answer(question)
        combined_text = f"{question}\n{diagnosis.answer}"
        return {
            "diagnosis": diagnosis.answer,
            "citations": diagnosis.citations,
            "device_model": self._extract_device_model(question)
            or self._extract_device_model(combined_text),
            "fault_code": self._extract_fault_code(question)
            or self._extract_fault_code(combined_text),
        }

    def _route_node(self, state: TicketGraphState) -> TicketGraphState:
        question = state["question"]
        risk_level = self._classify_risk(question)
        required_parts = query_parts(state.get("device_model"), question)
        human_required = risk_level == RiskLevel.HIGH
        status = self._initial_status(human_required=human_required, has_parts=bool(required_parts))
        return {
            "risk_level": risk_level,
            "required_parts": required_parts,
            "human_required": human_required,
            "status": status,
        }

    def _persist_node(self, state: TicketGraphState) -> TicketGraphState:
        now = self._now()

        ticket = TicketRecord(
            ticket_id=f"TCK-{uuid.uuid4().hex[:12].upper()}",
            idempotency_key=state["idempotency_key"],
            question=state["question"],
            diagnosis=state["diagnosis"],
            citations=state["citations"],
            device_model=state.get("device_model"),
            fault_code=state.get("fault_code"),
            risk_level=state["risk_level"],
            status=state["status"],
            required_parts=state["required_parts"],
            human_required=state["human_required"],
            created_at=now,
            updated_at=now,
        )
        self.store.upsert_ticket(ticket.model_dump(mode="json"))
        return {"ticket": ticket, "next_action": self._next_action(ticket)}

    def _build_graph(self):
        graph = StateGraph(TicketGraphState)
        graph.add_node("diagnose", self._diagnose_node)
        graph.add_node("route", self._route_node)
        graph.add_node("persist", self._persist_node)
        graph.add_edge(START, "diagnose")
        graph.add_edge("diagnose", "route")
        graph.add_edge("route", "persist")
        graph.add_edge("persist", END)
        return graph.compile()

    def resume_after_human_review(
        self,
        ticket_id: str,
        reviewer: str,
        decision: str,
    ) -> TicketWorkflowResult:
        ticket = self._get_ticket(ticket_id)
        ticket.human_reviewer = reviewer
        ticket.human_decision = decision
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.updated_at = self._now()
        self.store.upsert_ticket(ticket.model_dump(mode="json"))
        return TicketWorkflowResult(ticket=ticket, next_action=self._next_action(ticket))

    def close_ticket(self, ticket_id: str, closed_by: str) -> TicketRecord:
        ticket = self._get_ticket(ticket_id)
        now = self._now()
        ticket.status = TicketStatus.CLOSED
        ticket.closed_by = closed_by
        ticket.closed_at = now
        ticket.updated_at = now
        self.store.upsert_ticket(ticket.model_dump(mode="json"))
        return ticket

    def list_tickets(self) -> list[TicketRecord]:
        return [TicketRecord.model_validate(row) for row in self.store.list_tickets()]

    def _get_ticket(self, ticket_id: str) -> TicketRecord:
        ticket = self.store.get_ticket(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket not found: {ticket_id}")
        return TicketRecord.model_validate(ticket)

    @staticmethod
    def _extract_device_model(text: str) -> str | None:
        patterns = [r"UPS-30K", r"A100", r"CW200", r"PLC-X200"]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(0).upper()
        return None

    @staticmethod
    def _extract_fault_code(text: str) -> str | None:
        match = re.search(r"\b[A-Z]-\d+\b", text, flags=re.IGNORECASE)
        return match.group(0).upper() if match else None

    @staticmethod
    def _classify_risk(text: str) -> RiskLevel:
        if any(keyword in text for keyword in HIGH_RISK_KEYWORDS):
            return RiskLevel.HIGH
        if any(keyword in text for keyword in ["停机", "报警", "高压"]):
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @staticmethod
    def _initial_status(human_required: bool, has_parts: bool) -> TicketStatus:
        if human_required:
            return TicketStatus.NEED_HUMAN
        if has_parts:
            return TicketStatus.NEED_PARTS
        return TicketStatus.IN_PROGRESS

    @staticmethod
    def _next_action(ticket: TicketRecord) -> str:
        if ticket.status == TicketStatus.NEED_HUMAN:
            return "wait_for_human"
        if ticket.status == TicketStatus.NEED_PARTS:
            return "confirm_parts"
        if ticket.status == TicketStatus.CLOSED:
            return "none"
        return "continue_work"

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()
