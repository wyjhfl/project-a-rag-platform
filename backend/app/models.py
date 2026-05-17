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


class TicketStartRequest(BaseModel):
    question: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


class TicketResumeRequest(BaseModel):
    reviewer: str = Field(min_length=1)
    decision: str = Field(min_length=1)


class TicketCloseRequest(BaseModel):
    closed_by: str = Field(min_length=1)
