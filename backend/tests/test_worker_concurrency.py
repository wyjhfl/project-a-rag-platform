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

    def test_cancel_requested_running_job_cannot_complete_or_fail(
        self,
        service: JobService,
    ) -> None:
        """Cancellation requests win over normal worker terminal transitions."""
        record = service.create_job(job_type="cancel_requested")
        service.claim_next_job("worker-A")
        service.cancel_job(record.job_id)

        assert not service.complete_job(record.job_id, "worker-A", {"done": True})
        assert not service.fail_job(record.job_id, "worker-A", "should not retry")

        job = service.get_job(record.job_id)
        job_dict = job.to_dict() if hasattr(job, "to_dict") else job
        assert job_dict["status"] == "RUNNING"
        assert job_dict["cancel_requested"] is True
        assert job_dict["retry_count"] == 0

    def test_non_running_job_cannot_be_completed_failed_or_heartbeated(
        self,
        service: JobService,
    ) -> None:
        """Owner checks alone are insufficient; worker mutations require RUNNING."""
        record = service.create_job(job_type="not_running")
        job = service.get_job(record.job_id)
        job_dict = job.to_dict() if hasattr(job, "to_dict") else job
        job_dict["status"] = "RETRYING"
        job_dict["locked_by"] = "worker-A"
        service._store.update_job(job_dict)

        assert not service.complete_job(record.job_id, "worker-A", {"done": True})
        assert not service.fail_job(record.job_id, "worker-A", "should not fail")
        assert not service.heartbeat(record.job_id, "worker-A")

        final = service.get_job(record.job_id)
        final_dict = final.to_dict() if hasattr(final, "to_dict") else final
        assert final_dict["status"] == "RETRYING"
        assert final_dict["retry_count"] == 0

    def test_sqlite_claim_skips_cancel_requested_pending_jobs(
        self,
        service: JobService,
    ) -> None:
        """Workers should not claim jobs that were cancelled before execution."""
        cancelled = service.create_job(job_type="cancelled_pending")
        available = service.create_job(job_type="available_pending")
        assert service.cancel_job(cancelled.job_id) is not None

        claimed = service.claim_next_job("worker-A")

        assert claimed is not None
        assert claimed["job_id"] == available.job_id
        skipped = service.get_job(cancelled.job_id)
        skipped_dict = skipped.to_dict() if hasattr(skipped, "to_dict") else skipped
        assert skipped_dict["status"] == "CANCELLED"
        assert skipped_dict["locked_by"] is None

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


class TestAtomicStoreTransitions:
    def test_sqlite_timeout_stale_jobs_retries_or_fails_atomically(
        self,
        store: SqliteStore,
    ) -> None:
        service = JobService(store, execution_mode="worker")
        retrying = service.create_job(job_type="timeout_retry", max_retries=2)
        failed = service.create_job(job_type="timeout_fail", max_retries=1)
        service.claim_next_job("worker-1")
        service.claim_next_job("worker-2")
        stale = "2020-01-01T00:00:00+00:00"
        for job_id in (retrying.job_id, failed.job_id):
            job = store.get_job(job_id)
            assert job is not None
            job["heartbeat_at"] = stale
            store.update_job(job)

        count = store.timeout_stale_jobs(
            timeout_seconds=1,
            now="2026-01-01T00:00:00+00:00",
        )

        assert count == 2
        retrying_final = store.get_job(retrying.job_id)
        failed_final = store.get_job(failed.job_id)
        assert retrying_final is not None
        assert failed_final is not None
        assert retrying_final["status"] == "RETRYING"
        assert retrying_final["retry_count"] == 1
        assert retrying_final["finished_at"] is None
        assert failed_final["status"] == "FAILED"
        assert failed_final["retry_count"] == 1
        assert failed_final["finished_at"] == "2026-01-01T00:00:00+00:00"

    def test_sqlite_timeout_stale_jobs_cancels_cancel_requested_running(
        self,
        store: SqliteStore,
    ) -> None:
        service = JobService(store, execution_mode="worker")
        record = service.create_job(job_type="timeout_cancel_requested", max_retries=3)
        service.claim_next_job("worker-1")
        assert service.cancel_job(record.job_id) is not None
        job = store.get_job(record.job_id)
        assert job is not None
        job["heartbeat_at"] = "2020-01-01T00:00:00+00:00"
        store.update_job(job)

        count = store.timeout_stale_jobs(
            timeout_seconds=1,
            now="2026-01-01T00:00:00+00:00",
        )

        assert count == 1
        final = store.get_job(record.job_id)
        assert final is not None
        assert final["status"] == "CANCELLED"
        assert final["cancel_requested"] is True
        assert final["retry_count"] == 0
        assert final["finished_at"] == "2026-01-01T00:00:00+00:00"

    def test_sqlite_timeout_stale_jobs_does_not_touch_fresh_or_terminal_jobs(
        self,
        store: SqliteStore,
    ) -> None:
        service = JobService(store, execution_mode="worker")
        fresh = service.create_job(job_type="timeout_fresh")
        terminal = service.create_job(job_type="timeout_terminal")
        service.claim_next_job("worker-1")
        service.claim_next_job("worker-2")
        assert store.try_complete_job(
            terminal.job_id,
            "worker-2",
            {"done": True},
            "2026-01-01T00:00:00+00:00",
        )

        count = store.timeout_stale_jobs(
            timeout_seconds=300,
            now="2026-01-01T00:00:01+00:00",
        )

        assert count == 0
        fresh_final = store.get_job(fresh.job_id)
        terminal_final = store.get_job(terminal.job_id)
        assert fresh_final is not None
        assert terminal_final is not None
        assert fresh_final["status"] == "RUNNING"
        assert terminal_final["status"] == "SUCCEEDED"

    def test_sqlite_try_request_cancel_job_marks_running_without_terminal_overwrite(
        self,
        store: SqliteStore,
    ) -> None:
        service = JobService(store, execution_mode="worker")
        record = service.create_job(job_type="atomic_request_cancel")
        service.claim_next_job("worker-1")

        result = store.try_request_cancel_job(record.job_id, "2026-01-01T00:00:00+00:00")

        assert result is not None
        assert result["status"] == "RUNNING"
        assert result["cancel_requested"] is True
        assert result["locked_by"] == "worker-1"
        assert result["finished_at"] is None

        assert not store.try_complete_job(
            record.job_id,
            "worker-1",
            {"done": True},
            "2026-01-01T00:00:01+00:00",
        )
        final = store.get_job(record.job_id)
        assert final is not None
        assert final["status"] == "RUNNING"
        assert final["result"] == {}

    def test_sqlite_try_request_cancel_job_cancels_pending(
        self,
        store: SqliteStore,
    ) -> None:
        service = JobService(store, execution_mode="worker")
        record = service.create_job(job_type="atomic_cancel_pending")

        result = store.try_request_cancel_job(record.job_id, "2026-01-01T00:00:00+00:00")

        assert result is not None
        assert result["status"] == "CANCELLED"
        assert result["cancel_requested"] is True
        assert result["finished_at"] == "2026-01-01T00:00:00+00:00"
        assert service.claim_next_job("worker-1") is None

    def test_sqlite_try_request_cancel_job_does_not_overwrite_terminal(
        self,
        store: SqliteStore,
    ) -> None:
        service = JobService(store, execution_mode="worker")
        record = service.create_job(job_type="atomic_cancel_terminal")
        service.claim_next_job("worker-1")
        assert store.try_complete_job(
            record.job_id,
            "worker-1",
            {"done": True},
            "2026-01-01T00:00:00+00:00",
        )

        assert store.try_request_cancel_job(record.job_id, "2026-01-01T00:00:01+00:00") is None
        final = store.get_job(record.job_id)
        assert final is not None
        assert final["status"] == "SUCCEEDED"
        assert final["cancel_requested"] is False
        assert final["result"] == {"done": True}

    def test_sqlite_try_complete_requires_running_owner_and_no_cancel(self, store: SqliteStore) -> None:
        service = JobService(store, execution_mode="worker")
        record = service.create_job(job_type="atomic_complete")

        assert not store.try_complete_job(record.job_id, "worker-1", {"done": True}, "2026-01-01T00:00:00+00:00")

        service.claim_next_job("worker-1")
        assert not store.try_complete_job(record.job_id, "worker-2", {"done": True}, "2026-01-01T00:00:00+00:00")
        assert store.try_complete_job(record.job_id, "worker-1", {"done": True}, "2026-01-01T00:00:01+00:00")

        final = store.get_job(record.job_id)
        assert final is not None
        assert final["status"] == "SUCCEEDED"
        assert final["result"] == {"done": True}
        assert final["locked_by"] is None
        assert final["finished_at"] == "2026-01-01T00:00:01+00:00"

    def test_sqlite_try_fail_retries_then_fails_atomically(self, store: SqliteStore) -> None:
        service = JobService(store, execution_mode="worker")
        record = service.create_job(job_type="atomic_fail", max_retries=2)
        service.claim_next_job("worker-1")

        assert store.try_fail_job(record.job_id, "worker-1", "first", "2026-01-01T00:00:00+00:00")
        retrying = store.get_job(record.job_id)
        assert retrying is not None
        assert retrying["status"] == "RETRYING"
        assert retrying["retry_count"] == 1
        assert retrying["finished_at"] is None

        service.claim_next_job("worker-2")
        assert store.try_fail_job(record.job_id, "worker-2", "second", "2026-01-01T00:00:01+00:00")
        failed = store.get_job(record.job_id)
        assert failed is not None
        assert failed["status"] == "FAILED"
        assert failed["retry_count"] == 2
        assert failed["finished_at"] == "2026-01-01T00:00:01+00:00"

    def test_sqlite_try_cancel_running_requires_owner(self, store: SqliteStore) -> None:
        service = JobService(store, execution_mode="worker")
        record = service.create_job(job_type="atomic_cancel")
        service.claim_next_job("worker-1")

        assert not store.try_cancel_running_job(record.job_id, "worker-2", "wrong", "2026-01-01T00:00:00+00:00")
        assert store.try_cancel_running_job(record.job_id, "worker-1", "cancelled", "2026-01-01T00:00:01+00:00")

        final = store.get_job(record.job_id)
        assert final is not None
        assert final["status"] == "CANCELLED"
        assert final["error"] == "cancelled"
        assert final["locked_by"] is None

    def test_job_service_uses_atomic_store_transition(self, store: SqliteStore) -> None:
        service = JobService(store, execution_mode="worker")
        record = service.create_job(job_type="service_atomic")
        service.claim_next_job("worker-1")
        service.cancel_job(record.job_id)

        assert not service.complete_job(record.job_id, "worker-1", {"done": True})
        final = service.get_job(record.job_id)
        assert final is not None
        assert final["status"] == "RUNNING"
        assert final["cancel_requested"] is True
        assert final["result"] == {}
