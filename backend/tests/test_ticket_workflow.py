from pathlib import Path

from app.rag.pipeline import RagPipeline
from app.storage.sqlite_store import SQLiteStore
from app.ticketing.models import TicketStatus
from app.ticketing.workflow import TicketWorkflowService


def _build_service(tmp_path: Path) -> TicketWorkflowService:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "air_compressor_a100.txt").write_text(
        "A100空压机 E-17 表示供压异常。排查步骤：检查过滤器、压力传感器和管路泄漏。",
        encoding="utf-8",
    )
    (docs_dir / "chiller_cw200.txt").write_text(
        "CW200 冷水机高压报警时，应检查冷凝器散热、冷凝风机、压力传感器和过滤网。",
        encoding="utf-8",
    )
    (docs_dir / "ups_30k.txt").write_text(
        "UPS-30K 电池异味、冒烟或鼓包属于高风险故障，应停机并升级人工处理。",
        encoding="utf-8",
    )

    store = SQLiteStore(tmp_path / "app.db")
    pipeline = RagPipeline(chroma_dir=tmp_path / "chroma", store=store)
    pipeline.ingest_directory(docs_dir)
    return TicketWorkflowService(store=store, rag_pipeline=pipeline)


def test_creates_normal_ticket_from_rag_diagnosis(tmp_path: Path):
    service = _build_service(tmp_path)

    result = service.start(
        question="A100 出现 E-17 报警，现场供压不稳定，应该怎么处理？",
        idempotency_key="normal-a100-e17",
    )

    assert result.ticket.status == TicketStatus.IN_PROGRESS
    assert result.ticket.human_required is False
    assert result.ticket.required_parts == []
    assert "过滤器" in result.ticket.diagnosis
    assert result.ticket.citations[0].source == "air_compressor_a100.txt"


def test_queries_parts_before_creating_parts_ticket(tmp_path: Path):
    service = _build_service(tmp_path)

    result = service.start(
        question="CW200 高压报警，需要检查或更换压力传感器和过滤网。",
        idempotency_key="parts-cw200-pressure",
    )

    part_names = [part.name for part in result.ticket.required_parts]
    assert result.ticket.status == TicketStatus.NEED_PARTS
    assert "压力传感器" in part_names
    assert "过滤网" in part_names


def test_high_risk_ticket_pauses_for_human_and_resumes(tmp_path: Path):
    service = _build_service(tmp_path)

    paused = service.start(
        question="UPS-30K 电池有异味并且冒烟，现场想重启设备。",
        idempotency_key="hitl-ups-smoke",
    )

    assert paused.ticket.status == TicketStatus.NEED_HUMAN
    assert paused.ticket.human_required is True
    assert paused.next_action == "wait_for_human"

    resumed = service.resume_after_human_review(
        ticket_id=paused.ticket.ticket_id,
        reviewer="王工",
        decision="approved",
    )

    assert resumed.ticket.status == TicketStatus.IN_PROGRESS
    assert resumed.ticket.human_decision == "approved"
    assert resumed.ticket.human_reviewer == "王工"


def test_ticket_creation_is_idempotent(tmp_path: Path):
    service = _build_service(tmp_path)

    first = service.start(
        question="A100 出现 E-17 报警，现场供压不稳定。",
        idempotency_key="duplicate-a100-e17",
    )
    second = service.start(
        question="A100 出现 E-17 报警，现场供压不稳定。",
        idempotency_key="duplicate-a100-e17",
    )

    assert second.ticket.ticket_id == first.ticket.ticket_id
    assert len(service.list_tickets()) == 1


def test_closes_ticket_with_confirmer_and_time(tmp_path: Path):
    service = _build_service(tmp_path)
    created = service.start(
        question="A100 出现 E-17 报警，现场供压不稳定。",
        idempotency_key="close-a100-e17",
    )

    closed = service.close_ticket(ticket_id=created.ticket.ticket_id, closed_by="李工")

    assert closed.status == TicketStatus.CLOSED
    assert closed.closed_by == "李工"
    assert closed.closed_at is not None
