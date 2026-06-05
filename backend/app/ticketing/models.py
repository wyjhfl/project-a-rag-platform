from enum import StrEnum

from pydantic import BaseModel, Field

from app.models import Citation


class TicketStatus(StrEnum):
    NEW = "NEW"
    DIAGNOSED = "DIAGNOSED"
    NEED_PARTS = "NEED_PARTS"
    NEED_HUMAN = "NEED_HUMAN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PartCandidate(BaseModel):
    part_id: str
    name: str
    device_model: str
    reason: str


class TicketRecord(BaseModel):
    ticket_id: str
    idempotency_key: str
    question: str
    diagnosis: str
    citations: list[Citation] = Field(default_factory=list)
    device_model: str | None = None
    fault_code: str | None = None
    risk_level: RiskLevel = RiskLevel.LOW
    status: TicketStatus = TicketStatus.NEW
    required_parts: list[PartCandidate] = Field(default_factory=list)
    human_required: bool = False
    human_decision: str | None = None
    human_reviewer: str | None = None
    created_at: str
    updated_at: str
    closed_by: str | None = None
    closed_at: str | None = None


class TicketWorkflowResult(BaseModel):
    ticket: TicketRecord
    next_action: str
