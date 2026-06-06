"""Job management service for Project A RAG Platform."""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("project_a")

_TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "CANCELLED"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_error(error: Any) -> str:
    text = str(error).replace("\r", " ").replace("\n", " ")
    return text[:300]


class JobRecord:
    def __init__(self, **kwargs):
        now = _now()
        self.job_id = kwargs.get("job_id", f"JOB-{uuid.uuid4().hex[:8]}")
        self.job_type = kwargs.get("job_type", "")
        self.status = kwargs.get("status", "PENDING")
        self.payload = kwargs.get("payload", {})
        self.result = kwargs.get("result", {})
        self.error = kwargs.get("error")
        self.retry_count = kwargs.get("retry_count", 0)
        self.max_retries = kwargs.get("max_retries", 3)
        self.locked_by = kwargs.get("locked_by")
        self.locked_at = kwargs.get("locked_at")
        self.heartbeat_at = kwargs.get("heartbeat_at")
        self.timeout_seconds = kwargs.get("timeout_seconds", 300)
        self.cancel_requested = kwargs.get("cancel_requested", False)
        self.created_at = kwargs.get("created_at", now)
        self.updated_at = kwargs.get("updated_at", now)
        self.started_at = kwargs.get("started_at")
        self.finished_at = kwargs.get("finished_at")

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}


class JobService:
    def __init__(self, store, execution_mode: str = "inprocess"):
        self._store = store
        self._execution_mode = execution_mode

    def create_job(
        self,
        job_type,
        payload=None,
        runner=None,
        actor_role="",
        on_succeeded=None,
        on_failed=None,
        max_retries=3,
    ):
        record = JobRecord(job_type=job_type, payload=payload or {}, max_retries=max_retries)
        if hasattr(self._store, "create_job"):
            self._store.create_job(record.to_dict())

        if self._execution_mode == "inprocess" and runner:
            self._run_inprocess(record, runner, on_succeeded, on_failed)

        return record

    def _run_inprocess(self, record, runner, on_succeeded, on_failed):
        record.status = "RUNNING"
        record.started_at = _now()
        self._update_job(record)
        try:
            result = runner()
            record.status = "SUCCEEDED"
            record.result = result
            record.finished_at = _now()
            self._update_job(record)
            if on_succeeded:
                self._safe_callback(on_succeeded, record.to_dict())
        except Exception as exc:
            record.retry_count += 1
            record.error = _safe_error(exc)
            if record.retry_count >= record.max_retries:
                record.status = "FAILED"
                record.finished_at = _now()
            else:
                record.status = "PENDING"
            self._update_job(record)
            if on_failed and record.status == "FAILED":
                self._safe_callback(on_failed, record.to_dict())

    @staticmethod
    def _safe_callback(callback, job: dict) -> None:
        try:
            callback(job)
        except Exception:
            logger.warning("Job callback failed", exc_info=True)

    def get_job(self, job_id):
        if hasattr(self._store, "get_job"):
            result = self._store.get_job(job_id)
            if result is None:
                return None
            if isinstance(result, JobRecord):
                return result
            if isinstance(result, dict):
                return result
            return result
        return None

    def list_jobs(self, limit=100):
        if hasattr(self._store, "list_jobs"):
            return self._store.list_jobs(limit=limit)
        return []

    def cancel_job(self, job_id):
        job = self.get_job(job_id)
        if job is None:
            return None
        status = self._get(job, "status", "")
        if status in _TERMINAL_STATUSES:
            return None
        if status == "RUNNING":
            self._set(job, "cancel_requested", True)
        else:
            self._set(job, "status", "CANCELLED")
            self._set(job, "cancel_requested", True)
            self._set(job, "finished_at", _now())
        self._update_job(job)
        return job if isinstance(job, dict) else job.to_dict()

    def claim_next_job(self, worker_id):
        if hasattr(self._store, "claim_next_job"):
            result = self._store.claim_next_job(worker_id)
            if result:
                if isinstance(result, dict):
                    return result
                return result.to_dict() if hasattr(result, "to_dict") else result
        return None

    claim_job = claim_next_job

    def complete_job(self, job_id, worker_id, result):
        job = self.get_job(job_id)
        if job is None or not self._is_owner(job, worker_id):
            return False
        now = _now()
        self._set(job, "status", "SUCCEEDED")
        self._set(job, "result", result)
        self._set(job, "locked_by", None)
        self._set(job, "locked_at", None)
        self._set(job, "heartbeat_at", None)
        self._set(job, "finished_at", now)
        self._update_job(job)
        return True

    def fail_job(self, job_id, worker_id, error):
        job = self.get_job(job_id)
        if job is None or not self._is_owner(job, worker_id):
            return False
        retry_count = int(self._get(job, "retry_count", 0)) + 1
        max_retries = int(self._get(job, "max_retries", 3))
        if retry_count >= max_retries:
            self._set(job, "status", "FAILED")
            self._set(job, "finished_at", _now())
        else:
            self._set(job, "status", "RETRYING")
        self._set(job, "retry_count", retry_count)
        self._set(job, "error", _safe_error(error))
        self._set(job, "locked_by", None)
        self._set(job, "locked_at", None)
        self._set(job, "heartbeat_at", None)
        self._update_job(job)
        return True

    def heartbeat(self, job_id, worker_id):
        job = self.get_job(job_id)
        if job is None or not self._is_owner(job, worker_id):
            return False
        self._set(job, "heartbeat_at", _now())
        self._update_job(job)
        return True

    def timeout_stale_jobs(self, timeout_seconds=300):
        count = 0
        jobs = self.list_jobs(limit=1000)
        now = time.time()
        for job in jobs:
            if self._get(job, "status", "") != "RUNNING":
                continue
            ts = self._get(job, "heartbeat_at") or self._get(job, "locked_at")
            if not ts:
                continue
            try:
                last_seen = datetime.fromisoformat(ts).timestamp()
            except (ValueError, TypeError):
                continue
            if now - last_seen <= timeout_seconds:
                continue
            retry_count = int(self._get(job, "retry_count", 0)) + 1
            max_retries = int(self._get(job, "max_retries", 3))
            self._set(job, "retry_count", retry_count)
            if retry_count >= max_retries:
                self._set(job, "status", "FAILED")
                self._set(job, "finished_at", _now())
            else:
                self._set(job, "status", "RETRYING")
            self._set(job, "error", "Job timed out")
            self._set(job, "locked_by", None)
            self._set(job, "locked_at", None)
            self._set(job, "heartbeat_at", None)
            self._update_job(job)
            count += 1
        return count

    def cancel_running_job(self, job_id: str, worker_id: str = "", reason=None) -> bool:
        """Cancel a RUNNING job, bypassing retry (goes directly to CANCELLED)."""
        job = self.get_job(job_id)
        if job is None:
            return False
        if self._get(job, "status", "") != "RUNNING":
            return False
        if self._get(job, "locked_by") != worker_id:
            return False
        self._set(job, "status", "CANCELLED")
        self._set(job, "cancel_requested", True)
        self._set(job, "locked_by", None)
        self._set(job, "locked_at", None)
        self._set(job, "heartbeat_at", None)
        self._set(job, "finished_at", _now())
        if reason is not None:
            self._set(job, "error", _safe_error(reason))
        self._update_job(job)
        return True

    def _update_job(self, job):
        self._set(job, "updated_at", _now())
        if hasattr(self._store, "update_job"):
            self._store.update_job(job if isinstance(job, dict) else job.to_dict())

    @staticmethod
    def _get(job, name: str, default=None):
        if isinstance(job, dict):
            return job.get(name, default)
        return getattr(job, name, default)

    @staticmethod
    def _set(job, name: str, value) -> None:
        if isinstance(job, dict):
            job[name] = value
        else:
            setattr(job, name, value)

    def _is_owner(self, job, worker_id: str) -> bool:
        locked_by = self._get(job, "locked_by")
        return locked_by is None or locked_by == "" or locked_by == worker_id


def cancel_running_job(store, job_id: str, worker_id: str = "", reason=None) -> dict | None:
    """Cancel a RUNNING job, bypassing retry (goes directly to CANCELLED)."""
    service = JobService(store, execution_mode="worker")
    if not service.cancel_running_job(job_id, worker_id, reason):
        return None
    return service.get_job(job_id)
