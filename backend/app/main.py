import json
import logging
import tomllib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from app.acceptance.service import build_acceptance_overview
from app.audit import build_audit_event, record_audit_event
from app.auth import require_role
from app.cache.redis_cache import RedisCache, RedisCacheConfig
from app.config import get_settings
from app.errors import AppError, install_exception_handlers
from app.jobs import JobService
from app.metrics import get_metrics
from app.models import (
    AcceptanceOverviewResponse,
    AgentDiagnoseRequest,
    AgentDiagnoseResponse,
    AuditEventResponse,
    ChatRequest,
    ChatResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    GraphRelationRecord,
    IngestRequest,
    IngestResponse,
    JobCancelRequest,
    JobCreateResponse,
    JobEvaluationRequest,
    JobIngestRequest,
    JobRecord,
    SessionChatRequest,
    SessionChatResponse,
    SystemStatusResponse,
    TicketCloseRequest,
    TicketResumeRequest,
    TicketStartRequest,
    UploadResponse,
)
from app.observability import RequestContextMiddleware, configure_logging
from app.rag.conversation import ConversationMemory
from app.rag.diagnosis_agent import DiagnosisAgent
from app.rag.graph import LocalGraphRetriever, Neo4jGraphRetriever
from app.rag.llm import LLMConfig
from app.rag.pipeline import RagPipeline
from app.rag.vector_factory import build_vector_store
from app.rate_limit import MemoryRateLimiter, RateLimitMiddleware, RedisRateLimiter
from app.storage.factory import build_store
from app.ticketing.models import TicketRecord, TicketWorkflowResult
from app.ticketing.workflow import TicketWorkflowService
from app.upload_security import safe_save_upload


def _resolve_app_version() -> str:
    try:
        pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        version = data.get("project", {}).get("version")
        if isinstance(version, str) and version:
            return f"v{version}"
    except (OSError, tomllib.TOMLDecodeError):
        return "v1.0.5"
    return "v1.0.5"


APP_VERSION = _resolve_app_version()
RELEASE_URL = "https://github.com/wyjhfl/project-a-rag-platform/releases/tag/v1.0.5"

logger = logging.getLogger("project_a")


_OPTIONAL_CONFIG_KEYWORDS = ("REDIS_URL", "NEO4J_", "RATE_LIMIT_REDIS_URL")


def _check_config(settings) -> dict:
    errors = settings.validate()
    if not errors:
        return {"status": "ok", "provider": settings.llm_provider}
    core_errors = [e for e in errors if not any(kw in e for kw in _OPTIONAL_CONFIG_KEYWORDS)]
    if core_errors:
        return {"status": "error", "errors": errors}
    return {"status": "degraded", "errors": errors, "provider": settings.llm_provider}


def _check_storage(settings, store) -> dict:
    try:
        store.list_chat_records()
        return {"status": "ok", "backend": settings.storage_backend}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


def _check_vector_store(pipeline) -> dict:
    try:
        if pipeline.hybrid_retriever is not None:
            return {"status": "ok"}
        return {"status": "degraded", "reason": "hybrid_retriever not initialized"}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


def _check_optional_dependencies(settings, cache, rate_limiter=None) -> dict:
    checks: dict[str, str] = {}
    if settings.cache_enabled:
        try:
            if cache is not None and hasattr(cache, "client"):
                cache.client.ping()
                checks["redis"] = "ok"
            else:
                checks["redis"] = "degraded: client not initialized"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
    else:
        checks["redis"] = "disabled"
    if settings.vector_backend.strip().lower() == "milvus":
        try:
            from pymilvus import MilvusClient

            MilvusClient(uri=settings.milvus_uri, token=settings.milvus_token or None)
            checks["milvus"] = "ok"
        except Exception as exc:
            checks["milvus"] = f"error: {exc}"
    else:
        checks["milvus"] = "disabled"
    if settings.graph_retrieval_enabled:
        checks["neo4j"] = "enabled"
    else:
        checks["neo4j"] = "disabled"
    if settings.rate_limit_backend == "redis":
        try:
            if rate_limiter is not None and isinstance(rate_limiter, RedisRateLimiter):
                if rate_limiter.ping():
                    checks["rate_limit_redis"] = "ok"
                else:
                    checks["rate_limit_redis"] = "error: ping failed"
            else:
                checks["rate_limit_redis"] = "error: limiter not initialized"
        except Exception as exc:
            checks["rate_limit_redis"] = f"error: {exc}"
    else:
        checks["rate_limit_redis"] = "disabled"
    return checks


def _run_evaluation_sync(app: FastAPI, request: EvaluationRunRequest) -> EvaluationRunResponse:
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
    elif request.evaluation_type == "agentic":
        results = []
        for case in cases:
            response = app.state.diagnosis_agent.diagnose(
                question=case["question"],
                create_ticket_on_escalation=False,
            )
            text = response.answer + "\n" + "\n".join(c.content for c in response.citations)
            expected_keywords = case.get("expected_keywords", [])
            expected_decision = case.get("expected_decision")
            hits = [kw for kw in expected_keywords if kw in text]
            trace = app.state._store.get_rag_trace(response.trace_id) or {}
            results.append(
                {
                    "id": case.get("id", ""),
                    "decision": response.decision,
                    "expected_decision": expected_decision,
                    "decision_match": not expected_decision or response.decision == expected_decision,
                    "citation_ok": bool(response.citations) if response.decision == "answer" else True,
                    "refusal_ok": response.decision == "refuse" if expected_decision == "refuse" else True,
                    "escalation_ok": response.decision == "escalate" if expected_decision == "escalate" else True,
                    "trace_ok": bool(trace.get("tool_calls")) and bool(trace.get("trace_id")),
                    "retried": any(
                        call.outputs.get("retrieval_attempts", 1) > 1
                        for call in response.tool_calls
                        if call.tool == "knowledge_search"
                    ),
                    "hits": hits,
                }
            )

        def _rate(key: str) -> float:
            if not results:
                return 0.0
            return round(sum(1 for item in results if item[key]) / len(results), 4)

        summary = {
            "case_count": len(results),
            "passed_count": sum(1 for item in results if item["decision_match"]),
            "citation_accuracy": _rate("citation_ok"),
            "refusal_accuracy": _rate("refusal_ok"),
            "escalation_accuracy": _rate("escalation_ok"),
            "trace_completeness": _rate("trace_ok"),
            "retrieval_retry_rate": round(
                sum(1 for item in results if item["retried"]) / len(results),
                4,
            ) if results else 0.0,
            "results": results,
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


class _MetricsMiddleware:
    """ASGI middleware to record request metrics."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time as _time

        from app.config import get_settings as _get_settings
        from app.metrics import get_metrics as _get_metrics

        settings = _get_settings()
        if not settings.metrics_enabled:
            await self.app(scope, receive, send)
            return

        start = _time.monotonic()
        status_code = 200

        async def send_with_status(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        await self.app(scope, receive, send_with_status)
        duration_ms = (_time.monotonic() - start) * 1000
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        _get_metrics().record_request(method, path, status_code, duration_ms)


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
        vector_store=build_vector_store(settings, chroma_dir=chroma_dir),
    )
    docs_sources = {
        "seed_docs": seed_docs_dir or settings.seed_docs_dir,
        "real_manuals_sanitized": real_docs_dir or settings.real_docs_dir,
        "uploaded_docs": uploaded_docs_dir or settings.uploaded_docs_dir,
    }

    # Rate limiter (shared between middleware and health checks)
    if settings.rate_limit_backend == "redis" and settings.rate_limit_redis_url:
        rate_limiter = RedisRateLimiter(
            redis_url=settings.rate_limit_redis_url,
            requests_per_minute=settings.rate_limit_requests_per_minute,
            burst=settings.rate_limit_burst,
        )
    else:
        rate_limiter = MemoryRateLimiter(
            requests_per_minute=settings.rate_limit_requests_per_minute,
            burst=settings.rate_limit_burst,
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Project A starting up (version %s)", APP_VERSION)
        config_errors = settings.validate()
        if config_errors:
            for err in config_errors:
                logger.warning("config validation: %s", err)
        else:
            logger.info("config validation: all checks passed")
        yield
        logger.info("Project A shutting down")
        if cache is not None and hasattr(cache, "client"):
            try:
                cache.client.close()
            except Exception:
                pass

    app = FastAPI(title=f"Project A {APP_VERSION} Enterprise RAG", lifespan=lifespan)
    install_exception_handlers(app)
    app.add_middleware(_MetricsMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
    )
    app.add_middleware(
        RateLimitMiddleware,
        enabled=settings.rate_limit_enabled,
        requests_per_minute=settings.rate_limit_requests_per_minute,
        burst=settings.rate_limit_burst,
        exempt_paths=set(settings.rate_limit_exempt_paths) if settings.rate_limit_exempt_paths else None,
        backend=settings.rate_limit_backend,
        redis_url=settings.rate_limit_redis_url,
    )
    app.state.pipeline = pipeline
    app.state.docs_sources = docs_sources
    app.state.current_docs_source = "seed_docs"
    app.state.acceptance_docs_dir = seed_docs_dir or settings.seed_docs_dir
    app.state.conversation_memory = ConversationMemory(cache=cache)
    app.state.ticket_workflow = TicketWorkflowService(store=store, rag_pipeline=pipeline)
    app.state.diagnosis_agent = DiagnosisAgent(
        pipeline=pipeline,
        store=store,
        ticket_workflow=app.state.ticket_workflow,
    )
    app.state._settings = settings
    app.state._store = store
    app.state._cache = cache
    app.state._rate_limiter = rate_limiter
    app.state.job_service = JobService(store, execution_mode=settings.job_execution_mode)

    configure_logging(settings.log_level)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "project-a-rag-platform",
            "version": APP_VERSION,
            "release_url": RELEASE_URL,
        }

    @app.get("/readyz")
    def readyz():
        s = app.state._settings
        st = app.state._store
        c = app.state._cache
        p = app.state.pipeline
        config_check = _check_config(s)
        storage_check = _check_storage(s, st)
        vector_check = _check_vector_store(p)
        optional_checks = _check_optional_dependencies(s, c, app.state._rate_limiter)
        checks = {
            "config": config_check,
            "storage": storage_check,
            "vector_store": vector_check,
            "optional_dependencies": optional_checks,
        }
        core_has_error = (
            config_check["status"] == "error"
            or storage_check["status"] == "error"
            or vector_check["status"] == "error"
        )
        if core_has_error:
            overall = "error"
            return JSONResponse(
                status_code=503,
                content={"status": overall, "version": APP_VERSION, "release_url": RELEASE_URL, "checks": checks},
            )
        all_core_ok = (
            config_check["status"] in ("ok", "degraded")
            and storage_check["status"] == "ok"
            and vector_check["status"] in ("ok", "degraded")
        )
        config_degraded = config_check["status"] == "degraded"
        opt_degraded = config_degraded or any(
            v.startswith("error:") or v.startswith("degraded:")
            for v in optional_checks.values()
        )
        rate_limit_error = (
            optional_checks.get("rate_limit_redis", "").startswith("error:")
        )
        if all_core_ok and not opt_degraded and not rate_limit_error:
            overall = "ok"
        elif all_core_ok and (opt_degraded or rate_limit_error):
            overall = "degraded"
        else:
            overall = "error"
        return {"status": overall, "version": APP_VERSION, "release_url": RELEASE_URL, "checks": checks}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": APP_VERSION, "release_url": RELEASE_URL}

    @app.get("/metrics")
    def metrics_endpoint() -> PlainTextResponse:
        if not settings.metrics_enabled:
            return PlainTextResponse("# Metrics disabled\n", media_type="text/plain")
        return PlainTextResponse(get_metrics().generate(), media_type="text/plain")

    @app.get("/api/v1/system/status", response_model=SystemStatusResponse)
    def system_status(_role: str = Depends(require_role("viewer"))) -> SystemStatusResponse:
        return SystemStatusResponse(
            status="ok",
            version=APP_VERSION,
            release_url=RELEASE_URL,
            llm_provider=settings.llm_provider,
            llm_model=settings.llm_model,
            llm_enabled=app.state.pipeline.llm_generator.is_enabled,
            vector_store_ready=app.state.pipeline.hybrid_retriever is not None,
            docs_sources=list(app.state.docs_sources.keys()),
        )

    @app.get("/api/v1/acceptance/overview", response_model=AcceptanceOverviewResponse)
    def acceptance_overview(_role: str = Depends(require_role("viewer"))) -> AcceptanceOverviewResponse:
        acceptance_docs = getattr(app.state, "acceptance_docs_dir", None)
        return build_acceptance_overview(docs_dir=acceptance_docs, version=APP_VERSION, llm_provider=settings.llm_provider)

    @app.post("/api/v1/documents/ingest", response_model=IngestResponse)
    def ingest_documents(request: IngestRequest | None = None, _role: str = Depends(require_role("operator"))) -> IngestResponse:
        request = request or IngestRequest()
        docs_dir = _resolve_docs_dir(app, request.docs_source)
        app.state.current_docs_source = request.docs_source
        result = app.state.pipeline.ingest_directory(docs_dir)
        record_audit_event(
            store,
            build_audit_event(
                action="document.ingest",
                actor_role=_role,
                resource_type="document_source",
                resource_id=request.docs_source,
                summary="ingested documents",
                metadata={
                    "document_count": result.document_count,
                    "chunk_count": result.chunk_count,
                },
            ),
        )
        return result

    @app.post("/api/v1/documents/upload", response_model=UploadResponse)
    def upload_document(file: Annotated[UploadFile, File()], _role: str = Depends(require_role("operator"))) -> UploadResponse:
        target_dir = app.state.docs_sources["uploaded_docs"]
        filename, saved_path = safe_save_upload(
            file=file,
            target_dir=target_dir,
            max_bytes=settings.upload_max_bytes,
        )
        record_audit_event(
            store,
            build_audit_event(
                action="document.upload",
                actor_role=_role,
                resource_type="document",
                resource_id=filename,
                summary="uploaded document",
                metadata={
                    "filename": filename,
                    "content_type": file.content_type or "",
                    "size_bytes": file.size if hasattr(file, "size") and file.size else 0,
                },
            ),
        )
        return UploadResponse(filename=filename, path=str(saved_path))

    @app.post("/api/v1/chat", response_model=ChatResponse)
    def chat(request: ChatRequest, _role: str = Depends(require_role("viewer"))) -> ChatResponse:
        return app.state.pipeline.answer(request.question)

    @app.post("/api/v1/chat/session", response_model=SessionChatResponse)
    def session_chat(request: SessionChatRequest, _role: str = Depends(require_role("viewer"))) -> SessionChatResponse:
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
    def chat_stream(request: ChatRequest, _role: str = Depends(require_role("viewer"))) -> StreamingResponse:
        def events():
            for token in app.state.pipeline.stream_answer(request.question):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    @app.post("/api/v1/agent/diagnose", response_model=AgentDiagnoseResponse)
    def agent_diagnose(
        request: AgentDiagnoseRequest,
        _role: str = Depends(require_role("viewer")),
    ) -> AgentDiagnoseResponse:
        return app.state.diagnosis_agent.diagnose(
            question=request.question,
            top_k=request.top_k,
            session_id=request.session_id,
            create_ticket_on_escalation=request.create_ticket_on_escalation,
        )

    @app.get("/api/v1/rag/traces", response_model=list[dict])
    def list_rag_traces(
        limit: int = Query(default=50, ge=1, le=200),
        _role: str = Depends(require_role("viewer")),
    ) -> list[dict]:
        return app.state._store.list_rag_traces(limit=limit)

    @app.get("/api/v1/rag/traces/{trace_id}", response_model=dict)
    def get_rag_trace(
        trace_id: str,
        _role: str = Depends(require_role("viewer")),
    ) -> dict:
        trace = app.state._store.get_rag_trace(trace_id)
        if trace is None:
            raise AppError(code="not_found", message="RAG trace not found", status_code=404)
        return trace

    @app.get("/api/v1/rag/graph/relations", response_model=list[GraphRelationRecord])
    def list_graph_relations(_role: str = Depends(require_role("viewer"))) -> list[GraphRelationRecord]:
        graph_retriever = getattr(app.state.pipeline, "graph_retriever", None)
        if graph_retriever is None or not hasattr(graph_retriever, "relations"):
            hybrid = getattr(app.state.pipeline, "hybrid_retriever", None)
            keyword = getattr(hybrid, "keyword_retriever", None)
            chunks = getattr(keyword, "chunks", [])
            graph_retriever = LocalGraphRetriever()
            graph_retriever.index_chunks(chunks)
        return [
            GraphRelationRecord(
                source=source,
                relation=relation,
                target=target,
                weight=1.0,
                evidence_source="local_graph",
            )
            for source, relation, target in sorted(graph_retriever.relations())
        ]

    @app.post("/api/v1/tickets/start", response_model=TicketWorkflowResult)
    def start_ticket(request: TicketStartRequest, _role: str = Depends(require_role("operator"))) -> TicketWorkflowResult:
        result = app.state.ticket_workflow.start(
            question=request.question,
            idempotency_key=request.idempotency_key,
        )
        record_audit_event(
            store,
            build_audit_event(
                action="ticket.start",
                actor_role=_role,
                resource_type="ticket",
                resource_id=result.ticket.ticket_id,
                summary="started ticket",
                metadata={
                    "risk_level": result.ticket.risk_level,
                    "status": result.ticket.status,
                    "human_required": result.ticket.human_required,
                    "question_length": len(request.question),
                },
            ),
        )
        return result

    @app.post("/api/v1/tickets/{ticket_id}/resume", response_model=TicketWorkflowResult)
    def resume_ticket(ticket_id: str, request: TicketResumeRequest, _role: str = Depends(require_role("operator"))) -> TicketWorkflowResult:
        result = app.state.ticket_workflow.resume_after_human_review(
            ticket_id=ticket_id,
            reviewer=request.reviewer,
            decision=request.decision,
        )
        record_audit_event(
            store,
            build_audit_event(
                action="ticket.resume",
                actor_role=_role,
                resource_type="ticket",
                resource_id=ticket_id,
                summary="resumed ticket after human review",
                metadata={
                    "reviewer": request.reviewer[:80],
                    "decision": request.decision[:80],
                    "status": result.ticket.status,
                },
            ),
        )
        return result

    @app.post("/api/v1/tickets/{ticket_id}/close", response_model=TicketRecord)
    def close_ticket(ticket_id: str, request: TicketCloseRequest, _role: str = Depends(require_role("operator"))) -> TicketRecord:
        result = app.state.ticket_workflow.close_ticket(
            ticket_id=ticket_id,
            closed_by=request.closed_by,
        )
        record_audit_event(
            store,
            build_audit_event(
                action="ticket.close",
                actor_role=_role,
                resource_type="ticket",
                resource_id=ticket_id,
                summary="closed ticket",
                metadata={
                    "closed_by": request.closed_by[:80],
                    "status": str(result.status),
                },
            ),
        )
        return result

    @app.get("/api/v1/tickets", response_model=list[TicketRecord])
    def list_tickets(_role: str = Depends(require_role("viewer"))) -> list[TicketRecord]:
        return app.state.ticket_workflow.list_tickets()

    @app.post("/api/v1/evaluations/run", response_model=EvaluationRunResponse)
    def run_evaluation(request: EvaluationRunRequest, _role: str = Depends(require_role("admin"))) -> EvaluationRunResponse:
        result = _run_evaluation_sync(app, request)
        record_audit_event(
            store,
            build_audit_event(
                action="evaluation.run",
                actor_role=_role,
                resource_type="evaluation",
                resource_id=request.evaluation_type,
                summary="ran evaluation",
                metadata={
                    "docs_source": request.docs_source,
                    "case_count": result.summary.get("case_count", 0),
                    "passed_count": result.summary.get("passed_count"),
                },
            ),
        )
        return result

    @app.get("/api/v1/admin/audit/events", response_model=list[AuditEventResponse])
    def list_audit_events(
        limit: int = Query(default=100, ge=1, le=500),
        _role: str = Depends(require_role("admin")),
    ) -> list[AuditEventResponse]:
        events = app.state._store.list_audit_events(limit=limit)
        return [AuditEventResponse(**event) for event in events]

    @app.post("/api/v1/jobs/ingest", response_model=JobCreateResponse)
    def create_ingest_job(request: JobIngestRequest, _role: str = Depends(require_role("operator"))) -> JobCreateResponse:
        job_service = app.state.job_service

        def runner():
            docs_dir = _resolve_docs_dir(app, request.docs_source)
            app.state.current_docs_source = request.docs_source
            result = app.state.pipeline.ingest_directory(docs_dir)
            return {
                "document_count": result.document_count,
                "chunk_count": result.chunk_count,
                "docs_source": request.docs_source,
            }

        def _on_succeeded(job: dict) -> None:
            record_audit_event(
                store,
                build_audit_event(
                    action="job.succeeded",
                    actor_role=_role,
                    resource_type="job",
                    resource_id=job["job_id"],
                    summary="ingest job succeeded",
                    metadata={
                        "job_type": job["job_type"],
                        "status": job["status"],
                        "document_count": job["result"].get("document_count"),
                        "chunk_count": job["result"].get("chunk_count"),
                        "docs_source": job["result"].get("docs_source"),
                    },
                ),
            )

        def _on_failed(job: dict) -> None:
            record_audit_event(
                store,
                build_audit_event(
                    action="job.failed",
                    actor_role=_role,
                    resource_type="job",
                    resource_id=job["job_id"],
                    summary="ingest job failed",
                    metadata={
                        "job_type": job["job_type"],
                        "status": job["status"],
                        "error": job["error"],
                    },
                ),
            )

        record = job_service.create_job(
            job_type="document.ingest",
            payload={"docs_source": request.docs_source},
            runner=runner,
            actor_role=_role,
            on_succeeded=_on_succeeded,
            on_failed=_on_failed,
            timeout_seconds=settings.job_default_timeout_seconds,
        )
        record_audit_event(
            store,
            build_audit_event(
                action="job.create",
                actor_role=_role,
                resource_type="job",
                resource_id=record.job_id,
                summary="created ingest job",
                metadata={"job_type": "document.ingest", "status": record.status},
            ),
        )
        return JobCreateResponse(job=record.to_dict() if hasattr(record, "to_dict") else record)

    @app.post("/api/v1/jobs/evaluations", response_model=JobCreateResponse)
    def create_evaluation_job(request: JobEvaluationRequest, _role: str = Depends(require_role("admin"))) -> JobCreateResponse:
        job_service = app.state.job_service

        def runner():
            eval_request = EvaluationRunRequest(
                evaluation_type=request.evaluation_type,
                cases_path=request.cases_path,
                docs_source=request.docs_source,
            )
            result = _run_evaluation_sync(app, eval_request)
            return {
                "summary": result.summary,
                "evaluation_type": request.evaluation_type,
                "docs_source": request.docs_source,
            }

        def _on_succeeded(job: dict) -> None:
            result = job.get("result", {})
            summary = result.get("summary", {})
            record_audit_event(
                store,
                build_audit_event(
                    action="job.succeeded",
                    actor_role=_role,
                    resource_type="job",
                    resource_id=job["job_id"],
                    summary="evaluation job succeeded",
                    metadata={
                        "job_type": job["job_type"],
                        "status": job["status"],
                        "evaluation_type": result.get("evaluation_type"),
                        "docs_source": result.get("docs_source"),
                        "case_count": summary.get("case_count"),
                    },
                ),
            )

        def _on_failed(job: dict) -> None:
            record_audit_event(
                store,
                build_audit_event(
                    action="job.failed",
                    actor_role=_role,
                    resource_type="job",
                    resource_id=job["job_id"],
                    summary="evaluation job failed",
                    metadata={
                        "job_type": job["job_type"],
                        "status": job["status"],
                        "error": job["error"],
                    },
                ),
            )

        record = job_service.create_job(
            job_type="evaluation.run",
            payload={
                "evaluation_type": request.evaluation_type,
                "cases_path": request.cases_path,
                "docs_source": request.docs_source,
            },
            runner=runner,
            actor_role=_role,
            on_succeeded=_on_succeeded,
            on_failed=_on_failed,
            timeout_seconds=settings.job_default_timeout_seconds,
        )
        record_audit_event(
            store,
            build_audit_event(
                action="job.create",
                actor_role=_role,
                resource_type="job",
                resource_id=record.job_id,
                summary="created evaluation job",
                metadata={"job_type": "evaluation.run", "status": record.status},
            ),
        )
        return JobCreateResponse(job=record.to_dict() if hasattr(record, "to_dict") else record)

    @app.get("/api/v1/jobs/{job_id}", response_model=JobRecord)
    def get_job(job_id: str, _role: str = Depends(require_role("viewer"))) -> JobRecord:
        record = app.state.job_service.get_job(job_id)
        if record is None:
            raise AppError(code="not_found", message="Job not found", status_code=404)
        return record

    @app.get("/api/v1/jobs", response_model=list[JobRecord])
    def list_jobs(
        limit: int = Query(default=100, ge=1, le=500),
        _role: str = Depends(require_role("viewer")),
    ) -> list[JobRecord]:
        return app.state.job_service.list_jobs(limit=limit)

    @app.post("/api/v1/jobs/{job_id}/cancel", response_model=JobRecord)
    def cancel_job(job_id: str, request: JobCancelRequest, _role: str = Depends(require_role("operator"))) -> JobRecord:
        job = app.state.job_service.get_job(job_id)
        if job is None:
            raise AppError(code="not_found", message="Job not found", status_code=404)
        job_type = job.get("job_type", "") if isinstance(job, dict) else job.job_type
        if _role == "operator" and job_type != "document.ingest":
            raise AppError(code="forbidden", message="Operators can only cancel ingest jobs", status_code=403)
        if _role == "viewer":
            raise AppError(code="forbidden", message="Viewers cannot cancel jobs", status_code=403)
        result = app.state.job_service.cancel_job(job_id)
        if result is None:
            raise AppError(code="conflict", message="Job cannot be cancelled", status_code=409)
        record_audit_event(
            store,
            build_audit_event(
                action="job.cancelled",
                actor_role=_role,
                resource_type="job",
                resource_id=job_id,
                summary="job cancelled",
                metadata={"reason": request.reason[:200] if request.reason else ""},
            ),
        )
        return JobRecord(**result)

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
