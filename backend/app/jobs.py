"""Job management service for Project A RAG Platform."""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("project_a")

class JobRecord:
    def __init__(self, **kwargs):
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
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc).isoformat())
        self.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc).isoformat())
        self.started_at = kwargs.get("started_at")

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

class JobService:
    def __init__(self, store, execution_mode: str = "inprocess"):
        self._store = store
        self._execution_mode = execution_mode

    def create_job(self, job_type, payload=None, runner=None, actor_role="", on_succeeded=None, on_failed=None):
        record = JobRecord(job_type=job_type, payload=payload or {})
        if hasattr(self._store, "create_job"):
            self._store.create_job(record.to_dict())

        if self._execution_mode == "inprocess" and runner:
            self._run_inprocess(record, runner, on_succeeded, on_failed)

        return record

    def _run_inprocess(self, record, runner, on_succeeded, on_failed):
        record.status = "RUNNING"
        record.started_at = datetime.now(timezone.utc).isoformat()
        self._update_job(record)
        try:
            result = runner()
            record.status = "SUCCEEDED"
            record.result = result
            self._update_job(record)
            if on_succeeded:
                on_succeeded(record.to_dict())
        except Exception as exc:
            record.retry_count += 1
            if record.retry_count >= record.max_retries:
                record.status = "FAILED"
                record.error = str(exc)
            else:
                record.status = "PENDING"
                record.error = str(exc)
            self._update_job(record)
            if on_failed and record.status == "FAILED":
                on_failed(record.to_dict())

    def get_job(self, job_id):
        if hasattr(self._store, "get_job"):
            result = self._store.get_job(job_id)
            if result is None:
                return None
            if isinstance(result, JobRecord):
                return result
            return JobRecord(**result) if isinstance(result, dict) else result
        return None

    def list_jobs(self, limit=100):
        if hasattr(self._store, "list_jobs"):
            return self._store.list_jobs(limit=limit)
        return []

    def cancel_job(self, job_id):
        job = self.get_job(job_id)
        if job is None:
            return None
        if isinstance(job, dict):
            status = job.get("status", "")
        else:
            status = getattr(job, "status", "")
        if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
            return None
        if isinstance(job, dict):
            job["status"] = "CANCELLED"
        else:
            job.status = "CANCELLED"
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

    def complete_job(self, job_id, worker_id, result):
        job = self.get_job(job_id)
        if job is None:
            return None
        if isinstance(job, dict):
            job["status"] = "SUCCEEDED"
            job["result"] = result
        else:
            job.status = "SUCCEEDED"
            job.result = result
        self._update_job(job)
        return job if isinstance(job, dict) else job.to_dict()

    def fail_job(self, job_id, worker_id, error):
        job = self.get_job(job_id)
        if job is None:
            return None
        if isinstance(job, dict):
            retry_count = job.get("retry_count", 0) + 1
            max_retries = job.get("max_retries", 3)
            if retry_count >= max_retries:
                job["status"] = "FAILED"
            else:
                job["status"] = "PENDING"
            job["retry_count"] = retry_count
            job["error"] = str(error)
        else:
            job.retry_count += 1
            if job.retry_count >= job.max_retries:
                job.status = "FAILED"
            else:
                job.status = "PENDING"
            job.error = str(error)
        self._update_job(job)
        return job if isinstance(job, dict) else job.to_dict()

    def heartbeat(self, job_id, worker_id):
        job = self.get_job(job_id)
        if job is None:
            return False
        now = datetime.now(timezone.utc).isoformat()
        if isinstance(job, dict):
            job["heartbeat_at"] = now
        else:
            job.heartbeat_at = now
        self._update_job(job)
        return True

    def timeout_stale_jobs(self, timeout_seconds):
        count = 0
        jobs = self.list_jobs(limit=1000)
        now = time.time()
        for job in jobs:
            if isinstance(job, dict):
                status = job.get("status", "")
                heartbeat_at = job.get("heartbeat_at")
            else:
                status = getattr(job, "status", "")
                heartbeat_at = getattr(job, "heartbeat_at", None)
            if status == "RUNNING" and heartbeat_at:
                try:
                    ht = datetime.fromisoformat(heartbeat_at).timestamp()
                    if now - ht > timeout_seconds:
                        if isinstance(job, dict):
                            job["status"] = "FAILED"
                            job["error"] = "Job timed out"
                        else:
                            job.status = "FAILED"
                            job.error = "Job timed out"
                        self._update_job(job)
                        count += 1
                except (ValueError, TypeError):
                    pass
        return count

    def cancel_running_job(self, job_id: str, worker_id: str = "") -> dict | None:
        """Cancel a RUNNING job, bypassing retry (goes directly to CANCELLED)."""
        job = self.get_job(job_id)
        if job is None:
            return None
        if isinstance(job, dict):
            status = job.get("status", "")
        else:
            status = getattr(job, "status", "")
        if status != "RUNNING":
            return None
        if isinstance(job, dict):
            job["status"] = "CANCELLED"
            job["cancel_requested"] = True
        else:
            job.status = "CANCELLED"
            job.cancel_requested = True
        self._update_job(job)
        return job if isinstance(job, dict) else job.to_dict()

    def _update_job(self, job):
        if isinstance(job, dict):
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            if hasattr(self._store, "update_job"):
                self._store.update_job(job)
        elif hasattr(job, "to_dict"):
            job.updated_at = datetime.now(timezone.utc).isoformat()
            if hasattr(self._store, "update_job"):
                self._store.update_job(job.to_dict())


def cancel_running_job(store, job_id: str) -> dict | None:
    """Cancel a RUNNING job, bypassing retry (goes directly to CANCELLED)."""
    job = store.get_job(job_id) if hasattr(store, "get_job") else None
    if job is None:
        return None
    if isinstance(job, dict):
        status = job.get("status", "")
    else:
        status = getattr(job, "status", "")
    if status != "RUNNING":
        return None
    if isinstance(job, dict):
        job["status"] = "CANCELLED"
        job["cancel_requested"] = True
    else:
        job.status = "CANCELLED"
        job.cancel_requested = True
    if hasattr(store, "update_job"):
        store.update_job(job if isinstance(job, dict) else job.to_dict())
    return job if isinstance(job, dict) else job.to_dict()
