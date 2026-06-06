"""Worker concurrency tests using SQLite.

Tests that SqliteStore + JobService handle concurrent job claiming,
timeout recovery, cancellation, worker isolation, and terminal states
correctly under multi-threaded conditions.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

# Ensure backend is on sys.path so ``app.*`` imports work.
_BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.jobs import JobService, _safe_error  # noqa: E402
from app.storage.sqlite_store import SqliteStore  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path: Path) -> SqliteStore:
    """Create a SqliteStore backed by a temp database."""
    db_path = tmp_path / "test_jobs.db"
    return SqliteStore(db_path)


@pytest.fixture()
def service(store: SqliteStore) -> JobService:
    """Create a JobService with inprocess execution disabled (manual claim)."""
    return JobService(store, execution_mode="manual")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWorkerConcurrency:
    """Concurrency tests for job claiming and completion."""

    def test_concurrent_claim_no_duplicates(self, service: JobService) -> None:
        """Multiple threads claim jobs; no job is claimed by more than one worker."""
        num_jobs = 20
        num_workers = 5

        # Create jobs
        for _i in range(num_jobs):
            service.create_job(job_type="concurrency_test")

        claimed: dict[str, str] = {}  # job_id -> worker_id
        lock = threading.Lock()
        errors: list[str] = []

        def worker(worker_id: str) -> None:
            while True:
                job = service.claim_next_job(worker_id)
                if job is None:
                    break
                jid = job["job_id"] if isinstance(job, dict) else job.job_id
                with lock:
                    if jid in claimed:
                        errors.append(
                            f"Duplicate claim: job {jid} claimed by both "
                            f"{claimed[jid]} and {worker_id}"
                        )
                    claimed[jid] = worker_id
                # Complete the job
                service.complete_job(jid, worker_id, {"done": True})

        threads = [
            threading.Thread(target=worker, args=(f"worker-{i}",))
            for i in range(num_workers)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, f"Duplicate claims detected: {errors}"
        assert len(claimed) == num_jobs, (
            f"Expected {num_jobs} claimed jobs, got {len(claimed)}"
        )

    def test_claim_timeout_recovery(self, service: JobService) -> None:
        """Timed-out jobs with exhausted retries become FAILED."""
        # Create a job with max_retries=1 so timeout goes directly to FAILED
        record = service.create_job(job_type="timeout_test", max_retries=1)
        job_id = record.job_id
        service.claim_next_job("worker-A")

        # Simulate timeout: the job is RUNNING but heartbeat is stale
        job = service.get_job(job_id)
        assert job is not None
        # Manually set heartbeat to the past
        stale_time = "2020-01-01T00:00:00+00:00"
        job_dict = job.to_dict() if hasattr(job, "to_dict") else job
        job_dict["heartbeat_at"] = stale_time
        service._store.update_job(job_dict)

        # Timeout stale jobs
        count = service.timeout_stale_jobs(timeout_seconds=1)
        assert count >= 1, "Expected at least one timed-out job"

        # The job should now be FAILED
        job = service.get_job(job_id)
        job_dict = job.to_dict() if hasattr(job, "to_dict") else job
        assert job_dict["status"] == "FAILED"

    def test_cancel_during_running(self, service: JobService) -> None:
        """Cancelling a RUNNING job sets status to CANCELLED."""
        record = service.create_job(job_type="cancel_test")
        job_id = record.job_id

        # Claim the job (sets it to RUNNING)
        service.claim_next_job("worker-A")

        # Cancel the running job
        result = service.cancel_running_job(job_id, worker_id="worker-A")
        assert result is not None

        # Verify status is CANCELLED
        job = service.get_job(job_id)
        job_dict = job.to_dict() if hasattr(job, "to_dict") else job
        assert job_dict["status"] == "CANCELLED"

    def test_wrong_worker_cannot_complete(self, service: JobService) -> None:
        """Worker A cannot complete Worker B's job (wrong locked_by)."""
        record = service.create_job(job_type="isolation_test")
        job_id = record.job_id

        service.claim_next_job("worker-A")

        assert not service.complete_job(job_id, "worker-B", {"done": True})
        job = service.get_job(job_id)
        job_dict = job.to_dict() if hasattr(job, "to_dict") else job
        assert job_dict["locked_by"] == "worker-A"
        assert job_dict["status"] == "RUNNING"

        claim_result = service.claim_next_job("worker-B")
        assert claim_result is None

    def test_unclaimed_job_cannot_be_completed_failed_or_heartbeated(
        self,
        service: JobService,
    ) -> None:
        """Worker-only state transitions require an explicit lock owner."""
        record = service.create_job(job_type="owner_required")

        assert not service.complete_job(record.job_id, "worker-A", {"done": True})
        assert not service.fail_job(record.job_id, "worker-A", "should not fail")
        assert not service.heartbeat(record.job_id, "worker-A")

        job = service.get_job(record.job_id)
        job_dict = job.to_dict() if hasattr(job, "to_dict") else job
        assert job_dict["status"] == "PENDING"
        assert job_dict["locked_by"] is None
        assert job_dict["heartbeat_at"] is None

    def test_wrong_worker_cannot_fail_or_heartbeat(self, service: JobService) -> None:
        """Non-owner workers cannot mutate RUNNING jobs."""
        record = service.create_job(job_type="wrong_worker_mutation")
        service.claim_next_job("worker-A")

        assert not service.fail_job(record.job_id, "worker-B", "wrong worker")
        assert not service.heartbeat(record.job_id, "worker-B")

        job = service.get_job(record.job_id)
        job_dict = job.to_dict() if hasattr(job, "to_dict") else job
        assert job_dict["status"] == "RUNNING"
        assert job_dict["locked_by"] == "worker-A"
        assert job_dict["error"] is None

    def test_sqlite_persists_finished_at_for_terminal_jobs(
        self,
        service: JobService,
    ) -> None:
        """SQLite job records expose finished_at consistently with PostgreSQL."""
        record = service.create_job(job_type="finished_at_test")
        service.claim_next_job("worker-A")

        assert service.complete_job(record.job_id, "worker-A", {"done": True})

        job = service.get_job(record.job_id)
        job_dict = job.to_dict() if hasattr(job, "to_dict") else job
        assert job_dict["status"] == "SUCCEEDED"
        assert job_dict["finished_at"]

    def test_all_jobs_reach_terminal_state(self, service: JobService) -> None:
        """All jobs eventually reach SUCCEEDED, FAILED, or CANCELLED."""
        num_jobs = 10
        job_ids: list[str] = []

        # Create jobs with max_retries=1 so fail_job goes directly to FAILED
        for _i in range(num_jobs):
            record = service.create_job(job_type="terminal_test")
            # Set max_retries=1 so first failure goes to FAILED
            job = service.get_job(record.job_id)
            job_dict = job.to_dict() if hasattr(job, "to_dict") else job
            job_dict["max_retries"] = 1
            service._update_job(job_dict)
            job_ids.append(record.job_id)

        # Claim and process all jobs sequentially
        claimed_ids: list[str] = []
        for i in range(num_jobs):
            result = service.claim_next_job(f"worker-{i}")
            if result is not None:
                cid = result.get("job_id") if isinstance(result, dict) else getattr(result, "job_id", None)
                claimed_ids.append(cid)

        # Transition claimed jobs to terminal states
        for i, cid in enumerate(claimed_ids):
            if i < 5:
                service.complete_job(cid, f"worker-{i}", {"ok": True})
            elif i < 8:
                service.fail_job(cid, f"worker-{i}", "intentional failure")
            else:
                service.cancel_running_job(cid, f"worker-{i}")

        # Verify all claimed jobs are in terminal states
        terminal_states = {"SUCCEEDED", "FAILED", "CANCELLED"}
        for cid in claimed_ids:
            job = service.get_job(cid)
            job_dict = job.to_dict() if hasattr(job, "to_dict") else job
            assert job_dict["status"] in terminal_states, (
                f"Job {cid} is in non-terminal state: {job_dict['status']}"
            )


class TestJobErrorSanitization:
    def test_safe_error_removes_newlines_traceback_and_paths(self) -> None:
        text = _safe_error(
            "Traceback (most recent call last):\n"
            "File C:\\Users\\Administrator\\secret\\app.py\n"
            "File /home/project/secret/app.py"
        )

        assert "\n" not in text
        assert "\r" not in text
        assert "Traceback" not in text
        assert "C:\\Users" not in text
        assert "/home/project" not in text
        assert "<path>" in text

    def test_safe_error_truncates_to_300_chars(self) -> None:
        assert len(_safe_error("x" * 500)) == 300
