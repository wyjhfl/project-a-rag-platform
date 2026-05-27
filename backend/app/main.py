import json
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.acceptance.service import build_acceptance_overview
from app.cache.redis_cache import RedisCache, RedisCacheConfig
from app.config import get_settings
from app.models import (
    AcceptanceOverviewResponse,
    ChatRequest,
    ChatResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    IngestRequest,
    IngestResponse,
    SessionChatRequest,
    SessionChatResponse,
    SystemStatusResponse,
    TicketCloseRequest,
    TicketResumeRequest,
    TicketStartRequest,
    UploadResponse,
)
from app.rag.conversation import ConversationMemory
from app.rag.graph import Neo4jGraphRetriever
from app.rag.llm import LLMConfig
from app.rag.pipeline import RagPipeline
from app.rag.vector_factory import build_vector_store
from app.storage.factory import build_store
from app.ticketing.models import TicketRecord, TicketWorkflowResult
from app.ticketing.workflow import TicketWorkflowService

APP_VERSION = "v2.0"


def create_app(
    database_path: Path | None = None,
    chroma_dir: Path | None = None,
    seed_docs_dir: Path | None = None,
    real_docs_dir: Path | None = None,
    uploaded_docs_dir: Path | None = None,
) -> FastAPI:
    settings = get_settings()
    store = build_store(settings, database_path=database_path)
    cache = _build_cache(settings)
    pipeline = RagPipeline(
        chroma_dir=chroma_dir or settings.chroma_dir,
        store=store,
        prompt_path=settings.prompt_path,
        llm_config=LLMConfig(
            provider=settings.llm_provider,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        ),
        graph_retriever=_build_graph_retriever(settings),
        cache=cache,
        vector_store=build_vector_store(settings),
    )
    docs_sources = {
        "seed_docs": seed_docs_dir or settings.seed_docs_dir,
        "real_manuals_sanitized": real_docs_dir or settings.real_docs_dir,
        "uploaded_docs": uploaded_docs_dir or settings.uploaded_docs_dir,
    }

    app = FastAPI(title=f"Project A {APP_VERSION} Enterprise RAG")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.pipeline = pipeline
    app.state.docs_sources = docs_sources
    app.state.current_docs_source = "seed_docs"
    app.state.conversation_memory = ConversationMemory(cache=cache)
    app.state.ticket_workflow = TicketWorkflowService(store=store, rag_pipeline=pipeline)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": APP_VERSION}

    @app.get("/api/v1/system/status", response_model=SystemStatusResponse)
    def system_status() -> SystemStatusResponse:
        return SystemStatusResponse(
            status="ok",
            version=APP_VERSION,
            llm_provider=settings.llm_provider,
            llm_model=settings.llm_model,
            llm_enabled=app.state.pipeline.llm_generator.is_enabled,
            vector_store_ready=app.state.pipeline.hybrid_retriever is not None,
            docs_sources=list(app.state.docs_sources.keys()),
        )

    @app.get("/api/v1/acceptance/overview", response_model=AcceptanceOverviewResponse)
    def acceptance_overview() -> AcceptanceOverviewResponse:
        return build_acceptance_overview(version=APP_VERSION)

    @app.post("/api/v1/documents/ingest", response_model=IngestResponse)
    def ingest_documents(request: IngestRequest | None = None) -> IngestResponse:
        request = request or IngestRequest()
        docs_dir = _resolve_docs_dir(app, request.docs_source)
        app.state.current_docs_source = request.docs_source
        return app.state.pipeline.ingest_directory(docs_dir)

    @app.post("/api/v1/documents/upload", response_model=UploadResponse)
    def upload_document(file: Annotated[UploadFile, File()]) -> UploadResponse:
        target_dir = app.state.docs_sources["uploaded_docs"]
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(file.filename or "uploaded.txt").name
        if Path(filename).suffix.lower() not in {
            ".txt",
            ".md",
            ".csv",
            ".pdf",
            ".docx",
            ".xlsx",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
        }:
            raise ValueError("Unsupported file type")
        target_path = target_dir / filename
        with target_path.open("wb") as output:
            shutil.copyfileobj(file.file, output)
        return UploadResponse(filename=filename, path=str(target_path))

    @app.post("/api/v1/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        return app.state.pipeline.answer(request.question)

    @app.post("/api/v1/chat/session", response_model=SessionChatResponse)
    def session_chat(request: SessionChatRequest) -> SessionChatResponse:
        resolved_question = app.state.conversation_memory.resolve_question(
            request.session_id,
            request.question,
        )
        response = app.state.pipeline.answer(resolved_question)
        return SessionChatResponse(
            session_id=request.session_id,
            resolved_question=resolved_question,
            answer=response.answer,
            citations=response.citations,
        )

    @app.post("/api/v1/chat/stream")
    def chat_stream(request: ChatRequest) -> StreamingResponse:
        def events():
            for token in app.state.pipeline.stream_answer(request.question):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    @app.post("/api/v1/tickets/start", response_model=TicketWorkflowResult)
    def start_ticket(request: TicketStartRequest) -> TicketWorkflowResult:
        return app.state.ticket_workflow.start(
            question=request.question,
            idempotency_key=request.idempotency_key,
        )

    @app.post("/api/v1/tickets/{ticket_id}/resume", response_model=TicketWorkflowResult)
    def resume_ticket(ticket_id: str, request: TicketResumeRequest) -> TicketWorkflowResult:
        return app.state.ticket_workflow.resume_after_human_review(
            ticket_id=ticket_id,
            reviewer=request.reviewer,
            decision=request.decision,
        )

    @app.post("/api/v1/tickets/{ticket_id}/close", response_model=TicketRecord)
    def close_ticket(ticket_id: str, request: TicketCloseRequest) -> TicketRecord:
        return app.state.ticket_workflow.close_ticket(
            ticket_id=ticket_id,
            closed_by=request.closed_by,
        )

    @app.get("/api/v1/tickets", response_model=list[TicketRecord])
    def list_tickets() -> list[TicketRecord]:
        return app.state.ticket_workflow.list_tickets()

    @app.post("/api/v1/evaluations/run", response_model=EvaluationRunResponse)
    def run_evaluation(request: EvaluationRunRequest) -> EvaluationRunResponse:
        docs_dir = _resolve_docs_dir(app, request.docs_source)
        app.state.pipeline.ingest_directory(docs_dir)
        cases = json.loads(Path(request.cases_path).read_text(encoding="utf-8"))
        if request.evaluation_type == "regression":
            results = []
            for case in cases:
                response = app.state.pipeline.answer(case["question"])
                text = response.answer + "\n" + "\n".join(c.content for c in response.citations)
                hits = [kw for kw in case.get("expected_keywords", []) if kw in text]
                results.append({"id": case["id"], "passed": bool(hits), "hits": hits})
            summary = {
                "case_count": len(results),
                "passed_count": sum(1 for result in results if result["passed"]),
            }
        else:
            script_map = {
                "ragas": "evaluate_ragas.py",
                "adversarial": "run_adversarial.py",
            }
            summary = {
                "case_count": len(cases),
                "script": script_map[request.evaluation_type],
                "message": "Use backend script for full report generation.",
            }
        return EvaluationRunResponse(summary=summary)

    return app


def _resolve_docs_dir(app: FastAPI, docs_source: str) -> Path:
    if docs_source not in app.state.docs_sources:
        raise ValueError(f"Unknown docs_source: {docs_source}")
    return Path(app.state.docs_sources[docs_source])


def _build_graph_retriever(settings):
    if not settings.graph_retrieval_enabled:
        return None
    if not (settings.neo4j_uri and settings.neo4j_username and settings.neo4j_password):
        raise ValueError(
            "GRAPH_RETRIEVAL_ENABLED=true requires NEO4J_URI, "
            "NEO4J_USERNAME and NEO4J_PASSWORD."
        )
    return Neo4jGraphRetriever(
        uri=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )


def _build_cache(settings):
    if not settings.cache_enabled:
        return None
    return RedisCache(
        RedisCacheConfig(
            enabled=settings.cache_enabled,
            url=settings.redis_url,
            ttl_seconds=settings.cache_ttl_seconds,
        )
    )


app = create_app()
