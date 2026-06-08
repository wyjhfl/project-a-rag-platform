from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)


class Citation(BaseModel):
    source: str
    chunk_index: int
    content: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    llm_used: bool = False
    insufficient: bool = False
    safety_warning: bool = False


class SessionChatRequest(BaseModel):
    session_id: str = Field(min_length=1)
    question: str = Field(min_length=1)


class SessionChatResponse(ChatResponse):
    session_id: str
    resolved_question: str


class IngestResponse(BaseModel):
    document_count: int
    chunk_count: int


class IngestRequest(BaseModel):
    docs_source: str = "seed_docs"


class UploadResponse(BaseModel):
    filename: str
    path: str


class SystemStatusResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
    llm_model: str
    llm_enabled: bool
    vector_store_ready: bool
    docs_sources: list[str]


class EvaluationRunRequest(BaseModel):
    evaluation_type: str = Field(pattern="^(ragas|regression|adversarial)$")
    cases_path: str
    docs_source: str = "seed_docs"


class EvaluationRunResponse(BaseModel):
    summary: dict
    report_path: str | None = None


class AcceptanceEvidenceItem(BaseModel):
    label: str
    path: str


class AcceptanceBreakdownItem(BaseModel):
    label: str
    status: str
    summary: str
    metrics: dict[str, str] = Field(default_factory=dict)


class AcceptanceChartBar(BaseModel):
    label: str
    value: float
    total: float = 1.0
    tone: str = "info"


class AcceptanceHighlightItem(BaseModel):
    title: str
    summary: str
    status: str
    tags: list[str] = Field(default_factory=list)


class AcceptanceTraceEvent(BaseModel):
    name: str
    summary: str
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, str] = Field(default_factory=dict)


class AcceptanceTraceCase(BaseModel):
    case_id: str
    title: str
    issue: str
    events: list[AcceptanceTraceEvent] = Field(default_factory=list)
    raw_trace: dict = Field(default_factory=dict)


class AcceptancePanel(BaseModel):
    key: str
    title: str
    status: str
    summary: str
    metrics: dict[str, str]
    evidence: list[AcceptanceEvidenceItem] = Field(default_factory=list)
    breakdown: list[AcceptanceBreakdownItem] = Field(default_factory=list)
    chart: list[AcceptanceChartBar] = Field(default_factory=list)
    highlights: list[AcceptanceHighlightItem] = Field(default_factory=list)
    trace_cases: list[AcceptanceTraceCase] = Field(default_factory=list)


class AcceptanceOverviewResponse(BaseModel):
    status: str
    version: str
    generated_from: list[str]
    panels: list[AcceptancePanel]


class TicketStartRequest(BaseModel):
    question: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class TicketResumeRequest(BaseModel):
    reviewer: str = Field(min_length=1)
    decision: str = Field(min_length=1)


class TicketCloseRequest(BaseModel):
    closed_by: str = Field(min_length=1)


class AuditEventResponse(BaseModel):
    action: str
    actor_role: str = ""
    resource_type: str = ""
    resource_id: str = ""
    summary: str = ""
    metadata: dict = {}
    timestamp: str = ""


class JobCreateResponse(BaseModel):
    job: dict


class JobRecord(BaseModel):
    job_id: str
    job_type: str = ""
    status: str = "PENDING"
    payload: dict = {}
    result: dict = {}
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    locked_by: Optional[str] = None
    locked_at: Optional[str] = None
    heartbeat_at: Optional[str] = None
    timeout_seconds: int = 300
    cancel_requested: bool = False
    created_at: str = ""
    updated_at: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class JobCancelRequest(BaseModel):
    reason: str = ""


class JobIngestRequest(BaseModel):
    docs_source: str = "seed_docs"


class JobEvaluationRequest(BaseModel):
    evaluation_type: str = "regression"
    cases_path: str = ""
    docs_source: str = "seed_docs"
