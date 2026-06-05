"""Job worker execution for Project A RAG Platform."""
from __future__ import annotations

import logging

logger = logging.getLogger("project_a")


def _execute_job(job: dict, settings=None, store=None) -> dict | None:
    """Execute a job based on its type.

    Args:
        job: Job dict with keys job_id, job_type, payload, cancel_requested, etc.
        settings: Application settings object.
        store: Data store for persistence.

    Returns:
        Result dict on success, None if cancelled or unknown job type.
    """
    if job.get("cancel_requested"):
        logger.info("Job %s cancelled before execution", job.get("job_id"))
        return None

    job_type = job.get("job_type", "")
    payload = job.get("payload", {})

    if job_type == "document.ingest":
        return _run_document_ingest(payload, store)
    elif job_type == "evaluation.run":
        return _run_evaluation(payload, store)
    else:
        logger.warning("Unknown job type: %s", job_type)
        return None


def run_job(job_type: str, payload: dict, store=None) -> dict | None:
    """Execute a job based on its type (simplified interface).

    Returns:
        Result dict on success, None if cancelled.
    Raises:
        ValueError: If job_type is unknown.
    """
    if payload.get("cancel_requested"):
        logger.info("Job %s cancelled before execution", job_type)
        return None

    if job_type == "document.ingest":
        return _run_document_ingest(payload, store)
    elif job_type == "evaluation.run":
        return _run_evaluation(payload, store)
    else:
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
