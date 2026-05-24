import json
import shutil
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.cache.redis_cache import RedisCache, RedisCacheConfig
from app.config import get_settings
from app.models import (
    AcceptanceBreakdownItem,
    AcceptanceChartBar,
    AcceptanceEvidenceItem,
    AcceptanceHighlightItem,
    AcceptanceOverviewResponse,
    AcceptancePanel,
    AcceptanceTraceCase,
    AcceptanceTraceEvent,
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
DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"


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
        return _build_acceptance_overview()

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


def _build_acceptance_overview() -> AcceptanceOverviewResponse:
    panels = [
        _build_provider_panel(),
        _build_multimodal_panel(),
        _build_evaluation_panel(),
        _build_bad_case_panel(),
    ]
    generated_from: list[str] = []
    for panel in panels:
        generated_from.extend(item.path for item in panel.evidence)
    generated_from = list(dict.fromkeys(generated_from))
    overall_status = "ok" if any(panel.status == "passed" for panel in panels) else "warning"
    return AcceptanceOverviewResponse(
        status=overall_status,
        version=APP_VERSION,
        generated_from=generated_from,
        panels=panels,
    )


def _build_provider_panel() -> AcceptancePanel:
    report_path = _latest_doc("A-v2.2_provider_acceptance_report*.json") or _latest_doc(
        "A-v1.4_provider_acceptance_report*.json"
    )
    if report_path is None:
        return AcceptancePanel(
            key="provider",
            title="真实 LLM 主链",
            status="missing",
            summary="未找到 provider 验收报告。",
            metrics={},
        )

    report = _load_json(report_path)
    summary = report.get("summary", {})
    results = report.get("results", [])
    preferred = next((item for item in results if item.get("name") == "deepseek_chat"), None)
    accepted = preferred if preferred and preferred.get("status") == "accepted" else next(
        (item for item in results if item.get("status") == "accepted"), None
    )
    accepted_name = accepted.get("name", "未确定") if accepted else "未确定"
    metrics = {
        "provider_count": str(summary.get("provider_count", 0)),
        "accepted_count": str(summary.get("accepted_count", 0)),
        "blocked_count": str(summary.get("blocked_count", 0)),
        "default_candidate": accepted_name,
    }
    status = "passed" if summary.get("accepted_count", 0) >= 1 else "warning"
    breakdown = [
        AcceptanceBreakdownItem(
            label=item.get("name", "unknown"),
            status=item.get("status", "unknown"),
            summary=(
                "已通过 grounded 验收"
                if item.get("status") == "accepted"
                else f"当前阻塞: {item.get('blocker_type', 'unknown')}"
            ),
            metrics={
                "provider": str(item.get("runtime", {}).get("provider", "")),
                "model": str(item.get("runtime", {}).get("model", "")),
                "direct_llm_connected": str(item.get("direct_llm_connected", False)).lower(),
            },
        )
        for item in results
    ]
    chart = [
        AcceptanceChartBar(
            label="accepted",
            value=float(summary.get("accepted_count", 0)),
            total=float(summary.get("provider_count", 1) or 1),
            tone="success",
        ),
        AcceptanceChartBar(
            label="blocked",
            value=float(summary.get("blocked_count", 0)),
            total=float(summary.get("provider_count", 1) or 1),
            tone="danger",
        ),
    ]
    highlights = [
        AcceptanceHighlightItem(
            title="默认文本主链候选",
            summary=f"{accepted_name} 是当前公开 demo 默认主链；MiMo v2.5 已进入候选对照。",
            status="passed" if accepted else "warning",
            tags=["grounded", "default-provider"],
        )
    ]
    blocker_counts = summary.get("blocker_type_counts", {})
    if blocker_counts:
        highlights.append(
            AcceptanceHighlightItem(
                title="Provider 对比状态",
                summary="A-v2.2 起已使用 token-plan 口径重新验收，MiMo 进入 grounded 可比较状态。",
                status="passed" if summary.get("blocked_count", 0) == 0 else "warning",
                tags=[f"{key}:{value}" for key, value in blocker_counts.items()],
            )
        )
    panel_summary = (
        f"当前已有 {summary.get('accepted_count', 0)} 个真实文本 provider 通过 grounded 验收，"
        f"默认候选为 {accepted_name}。"
    )
    return AcceptancePanel(
        key="provider",
        title="真实 LLM 主链",
        status=status,
        summary=panel_summary,
        metrics=metrics,
        evidence=[AcceptanceEvidenceItem(label="provider 验收报告", path=str(report_path))],
        breakdown=breakdown,
        chart=chart,
        highlights=highlights,
    )


def _build_multimodal_panel() -> AcceptancePanel:
    report_path = _latest_doc("A-v1.5_multimodal_acceptance_report*.json")
    if report_path is None:
        return AcceptancePanel(
            key="multimodal",
            title="真实多模态能力",
            status="missing",
            summary="未找到 A-v1.5 多模态验收报告。",
            metrics={},
        )

    report = _load_json(report_path)
    counts = report.get("summary", {}).get("status_counts", {})
    components = report.get("components", [])
    passed_names = [item["name"] for item in components if item.get("status") == "passed"]
    blocked_names = [item["name"] for item in components if item.get("status") != "passed"]
    status = "passed" if counts.get("passed", 0) >= 2 else "warning"
    panel_summary = (
        f"真实多模态当前已转绿 {counts.get('passed', 0)} 条链路，"
        f"未转绿重点集中在 {', '.join(blocked_names[:2]) or '无'}。"
    )
    metrics = {
        "passed": str(counts.get("passed", 0)),
        "runtime_incompatible": str(counts.get("runtime_incompatible", 0)),
        "runtime_resource_blocked": str(counts.get("runtime_resource_blocked", 0)),
        "passed_components": ", ".join(passed_names) or "无",
    }
    breakdown = [
        AcceptanceBreakdownItem(
            label=item.get("name", "unknown"),
            status=item.get("status", "unknown"),
            summary=_safe_text(item.get("detail", {}).get("diagnosis"))
            or _safe_text(item.get("detail", {}).get("error"))
            or "见验收报告",
            metrics=_stringify_dict(
                {
                    key: value
                    for key, value in item.get("detail", {}).items()
                    if key in {"field_count", "confidence", "next_step", "acceptance_mode"}
                }
            ),
        )
        for item in components
    ]
    chart = [
        AcceptanceChartBar(
            label=status_name,
            value=float(count),
            total=float(report.get("summary", {}).get("component_count", 1) or 1),
            tone=_tone_for_status(status_name),
        )
        for status_name, count in counts.items()
    ]
    evidence = [AcceptanceEvidenceItem(label="A-v1.5 多模态报告", path=str(report_path))]
    paddle_probe = _latest_doc("A-v2.3_paddleocr_compatibility_report*.json") or _latest_doc(
        "A-v1.5_paddleocr_linux_final_probe*.json"
    )
    if paddle_probe is not None:
        evidence.append(AcceptanceEvidenceItem(label="PaddleOCR 兼容性边界", path=str(paddle_probe)))
    highlights = [
        AcceptanceHighlightItem(
            title="已转绿链路",
            summary="Vision LLM 与 MinerU Linux sliced 已经形成正式可讲的绿色链路。",
            status="passed",
            tags=passed_names[:3],
        ),
        AcceptanceHighlightItem(
            title="剩余未绿重点",
            summary="PaddleOCR 已在 A-v2.3 正式定性为 runtime compatibility boundary，不进入默认 demo。",
            status="warning",
            tags=["PaddleOCR", "runtime_incompatible"],
        ),
    ]
    return AcceptancePanel(
        key="multimodal",
        title="真实多模态能力",
        status=status,
        summary=panel_summary,
        metrics=metrics,
        evidence=evidence,
        breakdown=breakdown,
        chart=chart,
        highlights=highlights,
    )


def _build_evaluation_panel() -> AcceptancePanel:
    report_specs = [
        ("回归评测", DOCS_DIR / "A-real-data_regression_report.json"),
        ("RAGAS 评测", DOCS_DIR / "A-real-data_ragas_report.json"),
        ("对抗评测", DOCS_DIR / "A-real-data_adversarial_report.json"),
    ]
    evidence = [AcceptanceEvidenceItem(label=label, path=str(path)) for label, path in report_specs if path.exists()]
    if not evidence:
        return AcceptancePanel(
            key="evaluation",
            title="评测与回归",
            status="missing",
            summary="未找到评测报告。",
            metrics={},
        )

    regression_summary = {}
    regression_path = DOCS_DIR / "A-real-data_regression_report.json"
    if regression_path.exists():
        regression_summary = _load_json(regression_path).get("summary", {})
    ragas_path = DOCS_DIR / "A-real-data_ragas_report.json"
    ragas_summary = _load_json(ragas_path).get("summary", {}) if ragas_path.exists() else {}
    optimized_ragas_path = DOCS_DIR / "A-v1.2_ragas_report.json"
    optimized_ragas = _load_json(optimized_ragas_path) if optimized_ragas_path.exists() else {}
    adversarial_path = DOCS_DIR / "A-real-data_adversarial_report.json"
    adversarial_summary = (
        _load_json(adversarial_path).get("summary", {}) if adversarial_path.exists() else {}
    )
    passed_count = regression_summary.get("passed_count", 0)
    case_count = regression_summary.get("case_count", 0)
    metrics = {
        "regression": f"{passed_count}/{case_count}",
        "source_hit_count": str(regression_summary.get("source_hit_count", 0)),
        "ragas": _format_summary_value(ragas_summary),
        "adversarial": _format_summary_value(adversarial_summary),
    }
    status = "passed" if case_count and passed_count >= case_count - 1 else "warning"
    panel_summary = (
        f"真实回归评测当前通过 {passed_count}/{case_count}，"
        "并保留 RAGAS 与对抗报告作为补充证据。"
    )
    chart = []
    average_scores = ragas_summary.get("average_scores", {})
    for label, value in average_scores.items():
        chart.append(
            AcceptanceChartBar(
                label=label,
                value=float(value),
                total=1.0,
                tone="success" if float(value) >= 0.7 else "warning",
            )
        )
    if case_count:
        chart.append(
            AcceptanceChartBar(
                label="regression_pass_rate",
                value=float(passed_count),
                total=float(case_count),
                tone="success" if passed_count >= case_count - 1 else "warning",
            )
        )
    adv_case_count = adversarial_summary.get("case_count", 0)
    adv_passed_count = adversarial_summary.get("passed_count", 0)
    if adv_case_count:
        chart.append(
            AcceptanceChartBar(
                label="adversarial_pass_rate",
                value=float(adv_passed_count),
                total=float(adv_case_count),
                tone="success" if adv_passed_count == adv_case_count else "warning",
            )
        )
    low_score_cases = optimized_ragas.get("summary", {}).get("low_score_cases", [])[:3]
    trace_cases = _extract_trace_cases(optimized_ragas, low_score_cases)
    highlights = [
        AcceptanceHighlightItem(
            title=str(item.get("id", "unknown")),
            summary=(
                f"likely_issue={item.get('likely_issue', 'unknown')}, "
                f"faithfulness={item.get('faithfulness', 0)}, "
                f"context_precision={item.get('context_precision', 0)}"
            ),
            status="warning",
            tags=[str(item.get("likely_issue", "unknown"))],
        )
        for item in low_score_cases
    ]
    failed_adv = [
        item for item in _load_json(adversarial_path).get("results", []) if not item.get("passed", False)
    ] if adversarial_path.exists() else []
    if failed_adv:
        first_failed = failed_adv[0]
        highlights.append(
            AcceptanceHighlightItem(
                title=str(first_failed.get("id", "unknown")),
                summary="对抗测试仍有失败样例，适合在演示时专门讲安全边界与后处理不足。",
                status="danger",
                tags=[str(first_failed.get("category", "adversarial"))],
            )
        )
    return AcceptancePanel(
        key="evaluation",
        title="评测与回归",
        status=status,
        summary=panel_summary,
        metrics=metrics,
        evidence=evidence,
        chart=chart,
        highlights=highlights,
        trace_cases=trace_cases,
    )


def _build_bad_case_panel() -> AcceptancePanel:
    files = [
        ("真实数据 bad case", DOCS_DIR / "A-real-data_bad_cases.md"),
        ("A-v1.5 bad case", DOCS_DIR / "A-v1.5_bad_cases.md"),
    ]
    evidence = [AcceptanceEvidenceItem(label=label, path=str(path)) for label, path in files if path.exists()]
    if not evidence:
        return AcceptancePanel(
            key="badcases",
            title="Bad Case 与边界",
            status="missing",
            summary="未找到 bad case 记录。",
            metrics={},
        )

    real_case_count = _count_markdown_headings(DOCS_DIR / "A-real-data_bad_cases.md")
    multimodal_case_count = _count_markdown_headings(DOCS_DIR / "A-v1.5_bad_cases.md")
    metrics = {
        "real_data_cases": str(real_case_count),
        "multimodal_cases": str(multimodal_case_count),
    }
    highlights = _extract_markdown_highlights(DOCS_DIR / "A-real-data_bad_cases.md", 3)
    highlights.extend(_extract_markdown_highlights(DOCS_DIR / "A-v1.5_bad_cases.md", 2))
    summary = (
        f"当前已沉淀真实数据 bad case {real_case_count} 条，"
        f"多模态 bad case {multimodal_case_count} 条，可直接用于面试讲边界。"
    )
    return AcceptancePanel(
        key="badcases",
        title="Bad Case 与边界",
        status="passed",
        summary=summary,
        metrics=metrics,
        evidence=evidence,
        highlights=highlights,
    )


def _latest_doc(pattern: str) -> Path | None:
    matches = sorted(DOCS_DIR.glob(pattern))
    return matches[-1] if matches else None


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_summary_value(summary: dict) -> str:
    if not summary:
        return "未生成"
    compact = []
    for key in ("score", "pass_rate", "passed_count", "case_count"):
        if key in summary:
            compact.append(f"{key}={summary[key]}")
    return ", ".join(compact) or "已生成"


def _count_markdown_headings(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8", errors="ignore")
    return sum(1 for line in text.splitlines() if line.startswith("## "))


def _stringify_dict(data: dict) -> dict[str, str]:
    return {str(key): _safe_text(value) for key, value in data.items() if value not in (None, "", [])}


def _safe_text(value) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").strip()
    return text[:180] + "..." if len(text) > 180 else text


def _tone_for_status(status_name: str) -> str:
    if status_name == "passed":
        return "success"
    if status_name in {"runtime_incompatible", "runtime_resource_blocked"}:
        return "danger"
    return "warning"


def _extract_markdown_highlights(path: Path, limit: int) -> list[AcceptanceHighlightItem]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    highlights: list[AcceptanceHighlightItem] = []
    for index, line in enumerate(lines):
        if not line.startswith("## "):
            continue
        title = line[3:].strip()
        summary = ""
        for next_line in lines[index + 1 :]:
            cleaned = next_line.strip()
            if not cleaned or cleaned.startswith("## "):
                if cleaned.startswith("## "):
                    break
                continue
            summary = cleaned
            break
        highlights.append(
            AcceptanceHighlightItem(
                title=title,
                summary=_safe_text(summary) or "见 bad case 文档。",
                status="warning",
                tags=["bad-case"],
            )
        )
        if len(highlights) >= limit:
            break
    return highlights


def _extract_trace_cases(report: dict, low_score_cases: list[dict]) -> list[AcceptanceTraceCase]:
    if not report:
        return []
    result_map = {item.get("id"): item for item in report.get("results", [])}
    trace_cases: list[AcceptanceTraceCase] = []
    for item in low_score_cases:
        case_id = item.get("id")
        full_case = result_map.get(case_id)
        if not full_case:
            continue
        trace = full_case.get("trace", {})
        events = []
        for event in trace.get("events", [])[:6]:
            event_name = str(event.get("name", "unknown"))
            event_summary = _summarize_trace_event(event)
            events.append(
                AcceptanceTraceEvent(
                    name=event_name,
                    summary=event_summary,
                    inputs=_summarize_trace_map(event.get("inputs", {})),
                    outputs=_summarize_trace_map(event.get("outputs", {})),
                    metadata=_summarize_trace_map(event.get("metadata", {})),
                )
            )
        trace_cases.append(
            AcceptanceTraceCase(
                case_id=str(case_id),
                title=_safe_text(full_case.get("question")) or str(case_id),
                issue=str(item.get("likely_issue", "unknown")),
                events=events,
                raw_trace=trace,
            )
        )
    return trace_cases


def _summarize_trace_event(event: dict) -> str:
    outputs = event.get("outputs", {})
    metadata = event.get("metadata", {})
    if isinstance(outputs, dict):
        for key in ("decision", "route", "answer_source", "retrieval_queries"):
            if key in outputs:
                return _safe_text(outputs[key])
    if isinstance(metadata, dict):
        for key in ("accepted", "selected_count", "llm_used", "reason"):
            if key in metadata:
                return f"{key}={_safe_text(metadata[key])}"
    return "见原始 trace 事件。"


def _summarize_trace_map(data: dict) -> dict[str, str]:
    if not isinstance(data, dict):
        return {}
    summary: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, (str, int, float, bool)):
            summary[str(key)] = _safe_text(value)
        elif isinstance(value, list):
            preview = ", ".join(_safe_text(item) for item in value[:3])
            summary[str(key)] = preview
        elif isinstance(value, dict):
            compact = ", ".join(f"{nested_key}={_safe_text(nested_value)}" for nested_key, nested_value in list(value.items())[:3])
            summary[str(key)] = compact
    return summary


app = create_app()
