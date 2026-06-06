"""Job worker execution for Project A RAG Platform."""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Callable

logger = logging.getLogger("project_a")

JobExecutor = Callable[[dict], dict | None]


def _execute_job(job: dict, settings=None, store=None) -> dict | None:
    """Execute a job based on its type.

    This lightweight function is kept for unit tests and standalone smoke paths.
    The production worker uses ``_execute_app_job`` so it can reuse the configured
    FastAPI pipeline and document sources.
    """
    if job.get("cancel_requested"):
        logger.info("Job %s cancelled before execution", job.get("job_id"))
        return None

    job_type = job.get("job_type", "")
    payload = job.get("payload", {})

    if job_type == "document.ingest":
        return _run_document_ingest(payload, store)
    if job_type == "evaluation.run":
        return _run_evaluation(payload, store)

    logger.warning("Unknown job type: %s", job_type)
    return None


def _execute_app_job(job: dict, app) -> dict | None:
    """Execute a claimed job using the configured FastAPI app state."""
    if job.get("cancel_requested"):
        logger.info("Job %s cancelled before execution", job.get("job_id"))
        return None

    job_type = job.get("job_type", "")
    payload = job.get("payload", {})

    if job_type == "document.ingest":
        docs_source = payload.get("docs_source", "seed_docs")
        docs_dir = _resolve_docs_dir(app, docs_source)
        app.state.current_docs_source = docs_source
        result = app.state.pipeline.ingest_directory(docs_dir)
        return {
            "document_count": result.document_count,
            "chunk_count": result.chunk_count,
            "docs_source": docs_source,
        }

    if job_type == "evaluation.run":
        from app.main import _run_evaluation_sync
        from app.models import EvaluationRunRequest

        request = EvaluationRunRequest(
            evaluation_type=payload.get("evaluation_type", "regression"),
            cases_path=payload.get("cases_path", ""),
            docs_source=payload.get("docs_source", "seed_docs"),
        )
        result = _run_evaluation_sync(app, request)
        return {
            "summary": result.summary,
            "evaluation_type": request.evaluation_type,
            "docs_source": request.docs_source,
        }

    logger.warning("Unknown job type: %s", job_type)
    return None


def _resolve_docs_dir(app, docs_source: str) -> Path:
    docs_sources = getattr(app.state, "docs_sources", {})
    if docs_source not in docs_sources:
        raise ValueError(f"Unknown docs_source: {docs_source}")
    return Path(docs_sources[docs_source])


def process_one_job(service, worker_id: str, executor: JobExecutor) -> bool:
    """Claim and process one job. Returns True if a job was claimed."""
    job = service.claim_next_job(worker_id)
    if job is None:
        return False

    job_id = job["job_id"]
    job_type = job.get("job_type", "")

    try:
        if job.get("cancel_requested"):
            _cancel_running_or_warn(service, job_id, worker_id, job_type, "Job cancelled before execution")
            return True

        result = executor(job)
        latest = service.get_job(job_id) or job
        if isinstance(latest, dict) and latest.get("cancel_requested"):
            _cancel_running_or_warn(service, job_id, worker_id, job_type, "Job cancelled during execution")
            return True

        if result is None:
            _fail_running_or_warn(service, job_id, worker_id, job_type, f"Unknown or cancelled job type: {job_type}")
            return True

        if not service.complete_job(job_id, worker_id, result):
            logger.warning("Worker could not complete job: job_id=%s worker_id=%s", job_id, worker_id)
            final = service.get_job(job_id) or {}
            _record_worker_job_metric(job_type, final.get("status", "NOT_COMPLETED"))
            return True
        _record_worker_job_metric(job_type, "SUCCEEDED")
        return True
    except Exception as exc:
        logger.exception("Job execution failed: %s", job_id)
        _fail_running_or_warn(service, job_id, worker_id, job_type, str(exc)[:300])
        return True


def _cancel_running_or_warn(service, job_id: str, worker_id: str, job_type: str, reason: str) -> None:
    if not service.cancel_running_job(job_id, worker_id, reason):
        logger.warning("Worker could not cancel job: job_id=%s worker_id=%s", job_id, worker_id)
    final = service.get_job(job_id) or {}
    _record_worker_job_metric(job_type, final.get("status", "NOT_CANCELLED"))


def _fail_running_or_warn(service, job_id: str, worker_id: str, job_type: str, error: str) -> None:
    if not service.fail_job(job_id, worker_id, error):
        logger.warning("Worker could not fail job: job_id=%s worker_id=%s", job_id, worker_id)
    final = service.get_job(job_id) or {}
    _record_worker_job_metric(job_type, final.get("status", "NOT_FAILED"))


def _record_worker_job_metric(job_type: str, status: str) -> None:
    try:
        from app.metrics import get_metrics

        get_metrics().record_job(job_type or "unknown", status)
    except Exception:
        logger.warning("Failed to record worker job metric", exc_info=True)


def run_forever() -> None:
    """Run the production worker loop."""
    from app.main import app as fastapi_app

    settings = fastapi_app.state._settings
    service = fastapi_app.state.job_service
    worker_id = os.getenv("WORKER_ID", "worker-1")
    poll_interval = max(1, int(getattr(settings, "job_poll_interval_seconds", 5)))

    logger.info("Project A job worker started: worker_id=%s", worker_id)
    while True:
        claimed = process_one_job(
            service=service,
            worker_id=worker_id,
            executor=lambda job: _execute_app_job(job, fastapi_app),
        )
        if not claimed:
            time.sleep(poll_interval)


def run_job(job_type: str, payload: dict, store=None) -> dict | None:
    """Execute a job based on its type (simplified interface)."""
    if payload.get("cancel_requested"):
        logger.info("Job %s cancelled before execution", job_type)
        return None

    if job_type == "document.ingest":
        return _run_document_ingest(payload, store)
    if job_type == "evaluation.run":
        return _run_evaluation(payload, store)
    raise ValueError(f"Unknown job type: {job_type}")


def _run_document_ingest(payload: dict, store=None) -> dict:
    docs_source = payload.get("docs_source", "seed_docs")
    result = {"status": "completed", "docs_source": docs_source}

    if store is not None and hasattr(store, "add_document"):
        pass

    logger.info("Document ingest completed: source=%s", docs_source)
    return result


def _run_evaluation(payload: dict, store=None) -> dict:
    evaluation_type = payload.get("evaluation_type", "regression")
    result = {"status": "completed", "evaluation_type": evaluation_type}
    logger.info("Evaluation completed: type=%s", evaluation_type)
    return result


def main() -> None:
    try:
        run_forever()
    except KeyboardInterrupt:
        logger.info("Project A job worker stopped")


if __name__ == "__main__":
    main()
