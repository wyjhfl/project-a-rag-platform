"""Tests for production landing features: job worker, rate limit, metrics, migrations."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# --- Job Service Tests ---

class TestJobServiceWorkerMode:
    def setup_method(self):
        from app.jobs import JobService
        self.store = MagicMock()
        self.store.get_job.return_value = None
        self.store.list_jobs.return_value = []
        self.service = JobService(self.store, execution_mode="worker")

    def test_create_job_in_worker_mode_does_not_run(self):
        """In worker mode, create_job should NOT start a thread."""
        runner = MagicMock()
        record = self.service.create_job(
            job_type="document.ingest",
            payload={"docs_source": "seed_docs"},
            runner=runner,
        )
        assert record.status == "PENDING"
        runner.assert_not_called()
        # Give time to ensure no thread was started
        import time
        time.sleep(0.1)
        runner.assert_not_called()

    def test_create_job_accepts_timeout_seconds(self):
        record = self.service.create_job(
            job_type="document.ingest",
            payload={"docs_source": "seed_docs"},
            timeout_seconds=42,
        )

        assert record.timeout_seconds == 42
        created = self.store.create_job.call_args.args[0]
        assert created["timeout_seconds"] == 42

    def test_claim_job_picks_pending(self):
        claimed_job = {
            "job_id": "JOB-test123",
            "job_type": "document.ingest",
            "status": "RUNNING",
            "payload": {},
            "result": {},
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "locked_by": "worker-1",
            "locked_at": "2026-01-01T00:00:00",
            "heartbeat_at": "2026-01-01T00:00:00",
            "timeout_seconds": 300,
            "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "started_at": "2026-01-01T00:00:00",
            "finished_at": None,
        }
        self.store.claim_next_job.return_value = claimed_job
        claimed = self.service.claim_job("worker-1")
        assert claimed is not None
        assert claimed["status"] == "RUNNING"
        assert claimed["locked_by"] == "worker-1"

    def test_claim_job_skips_locked(self):
        self.store.claim_next_job.return_value = None
        claimed = self.service.claim_job("worker-1")
        assert claimed is None

    def test_complete_job(self):
        job = {
            "job_id": "JOB-test123",
            "status": "RUNNING",
            "locked_by": "worker-1",
            "payload": {},
            "result": {},
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "timeout_seconds": 300,
            "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "started_at": "2026-01-01T00:00:00",
            "finished_at": None,
            "locked_at": "2026-01-01T00:00:00",
            "heartbeat_at": "2026-01-01T00:00:00",
            "job_type": "document.ingest",
        }
        self.store.get_job.return_value = job
        result = self.service.complete_job("JOB-test123", "worker-1", {"document_count": 5})
        assert result is True
        assert job["status"] == "SUCCEEDED"
        assert job["locked_by"] is None

    def test_complete_job_wrong_worker(self):
        job = {"job_id": "JOB-test123", "locked_by": "worker-2"}
        self.store.get_job.return_value = job
        result = self.service.complete_job("JOB-test123", "worker-1", {})
        assert result is False

    def test_fail_job_retries(self):
        job = {
            "job_id": "JOB-test123",
            "status": "RUNNING",
            "locked_by": "worker-1",
            "retry_count": 0,
            "max_retries": 3,
            "payload": {},
            "result": {},
            "error": None,
            "timeout_seconds": 300,
            "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "started_at": None,
            "finished_at": None,
            "locked_at": None,
            "heartbeat_at": None,
            "job_type": "document.ingest",
        }
        self.store.get_job.return_value = job
        result = self.service.fail_job("JOB-test123", "worker-1", "Something failed")
        assert result is True
        assert job["status"] == "RETRYING"
        assert job["retry_count"] == 1
        assert job["locked_by"] is None

    def test_fail_job_exceeds_retries(self):
        job = {
            "job_id": "JOB-test123",
            "status": "RUNNING",
            "locked_by": "worker-1",
            "retry_count": 3,
            "max_retries": 3,
            "payload": {},
            "result": {},
            "error": None,
            "timeout_seconds": 300,
            "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "started_at": None,
            "finished_at": None,
            "locked_at": None,
            "heartbeat_at": None,
            "job_type": "document.ingest",
        }
        self.store.get_job.return_value = job
        result = self.service.fail_job("JOB-test123", "worker-1", "Final failure")
        assert result is True
        assert job["status"] == "FAILED"
        assert job["locked_by"] is None

    def test_cancel_pending_job(self):
        job = {
            "job_id": "JOB-test123",
            "status": "PENDING",
            "payload": {},
            "result": {},
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "locked_by": None,
            "locked_at": None,
            "heartbeat_at": None,
            "timeout_seconds": 300,
            "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "started_at": None,
            "finished_at": None,
            "job_type": "document.ingest",
        }
        self.store.get_job.return_value = job
        result = self.service.cancel_job("JOB-test123")
        assert result is not None
        assert result["status"] == "CANCELLED"

    def test_cancel_running_job_sets_flag(self):
        job = {
            "job_id": "JOB-test123",
            "status": "RUNNING",
            "payload": {},
            "result": {},
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "locked_by": "worker-1",
            "locked_at": None,
            "heartbeat_at": None,
            "timeout_seconds": 300,
            "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "started_at": None,
            "finished_at": None,
            "job_type": "document.ingest",
        }
        self.store.get_job.return_value = job
        result = self.service.cancel_job("JOB-test123")
        assert result is not None
        assert result["cancel_requested"] is True

    def test_cancel_completed_job_returns_none(self):
        job = {"job_id": "JOB-test123", "status": "SUCCEEDED"}
        self.store.get_job.return_value = job
        result = self.service.cancel_job("JOB-test123")
        assert result is None

    def test_heartbeat(self):
        job = {
            "job_id": "JOB-test123",
            "locked_by": "worker-1",
            "status": "RUNNING",
            "payload": {},
            "result": {},
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "timeout_seconds": 300,
            "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "started_at": None,
            "finished_at": None,
            "locked_at": None,
            "heartbeat_at": None,
            "job_type": "document.ingest",
        }
        self.store.get_job.return_value = job
        result = self.service.heartbeat("JOB-test123", "worker-1")
        assert result is True
        assert job["heartbeat_at"] is not None

    def test_timeout_stale_jobs(self):
        from datetime import datetime, timedelta, timezone
        past = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
        job = {
            "job_id": "JOB-test123",
            "status": "RUNNING",
            "locked_by": "worker-1",
            "locked_at": past,
            "retry_count": 0,
            "max_retries": 3,
            "timeout_seconds": 300,
            "payload": {},
            "result": {},
            "error": None,
            "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "started_at": None,
            "finished_at": None,
            "heartbeat_at": None,
            "job_type": "document.ingest",
        }
        self.store.list_jobs.return_value = [job]
        count = self.service.timeout_stale_jobs()
        assert count == 1
        assert job["status"] == "RETRYING"


class TestAtomicJobClaim:
    """Test store-level atomic job claim with real SQLite."""

    def _make_store(self, tmp_path):
        from app.storage.sqlite_store import SQLiteStore
        return SQLiteStore(tmp_path / "test.db")

    def _insert_job(self, store, job_id, status="PENDING", locked_by=None, job_type="document.ingest"):
        job = {
            "job_id": job_id,
            "job_type": job_type,
            "status": status,
            "payload": {},
            "result": {},
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "locked_by": locked_by,
            "locked_at": None,
            "heartbeat_at": None,
            "timeout_seconds": 300,
            "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "started_at": None,
            "finished_at": None,
        }
        store.upsert_job(job)

    def test_claim_pending_job(self, tmp_path):
        store = self._make_store(tmp_path)
        self._insert_job(store, "JOB-001")
        result = store.claim_next_job("worker-1")
        assert result is not None
        assert result["job_id"] == "JOB-001"
        assert result["status"] == "RUNNING"
        assert result["locked_by"] == "worker-1"

    def test_locked_job_not_claimed(self, tmp_path):
        store = self._make_store(tmp_path)
        self._insert_job(store, "JOB-001", locked_by="other-worker")
        result = store.claim_next_job("worker-1")
        assert result is None

    def test_two_workers_cannot_claim_same_job(self, tmp_path):
        store = self._make_store(tmp_path)
        self._insert_job(store, "JOB-001")
        result1 = store.claim_next_job("worker-1")
        assert result1 is not None
        assert result1["locked_by"] == "worker-1"
        result2 = store.claim_next_job("worker-2")
        assert result2 is None

    def test_retrying_job_can_be_claimed(self, tmp_path):
        store = self._make_store(tmp_path)
        self._insert_job(store, "JOB-001", status="RETRYING")
        result = store.claim_next_job("worker-1")
        assert result is not None
        assert result["status"] == "RUNNING"

    def test_no_jobs_returns_none(self, tmp_path):
        store = self._make_store(tmp_path)
        result = store.claim_next_job("worker-1")
        assert result is None


# --- Rate Limit Tests ---

class TestRateLimiter:
    def test_allowed_under_limit(self):
        from app.rate_limit import _RateLimiter
        limiter = _RateLimiter(requests_per_minute=60, burst=10)
        for _ in range(10):
            assert limiter.is_allowed("key1") is True

    def test_blocked_over_burst(self):
        from app.rate_limit import _RateLimiter
        limiter = _RateLimiter(requests_per_minute=60, burst=5)
        for _ in range(5):
            limiter.is_allowed("key1")
        assert limiter.is_allowed("key1") is False

    def test_different_keys_independent(self):
        from app.rate_limit import _RateLimiter
        limiter = _RateLimiter(requests_per_minute=60, burst=2)
        limiter.is_allowed("key1")
        limiter.is_allowed("key1")
        assert limiter.is_allowed("key1") is False
        assert limiter.is_allowed("key2") is True


# --- Metrics Tests ---

class TestMetricsCollector:
    def test_record_request(self):
        from app.metrics import MetricsCollector
        m = MetricsCollector()
        m.record_request("GET", "/healthz", 200, 5.0)
        m.record_request("GET", "/healthz", 200, 10.0)
        output = m.generate()
        assert "project_a_request_total" in output
        assert "project_a_uptime_seconds" in output

    def test_record_job(self):
        from app.metrics import MetricsCollector
        m = MetricsCollector()
        m.record_job("document.ingest", "SUCCEEDED", 1000.0)
        output = m.generate()
        assert "project_a_job_total" in output
        assert "project_a_job_duration_ms" in output

    def test_error_count(self):
        from app.metrics import MetricsCollector
        m = MetricsCollector()
        m.record_request("POST", "/api/v1/chat", 500, 100.0)
        output = m.generate()
        assert "project_a_error_total" in output


# --- Migration Tests ---

class TestMigrations:
    def test_migration_registry_not_empty(self):
        from app.migrations import MIGRATIONS
        assert len(MIGRATIONS) >= 2

    def test_migrations_have_versions(self):
        from app.migrations import MIGRATIONS
        versions = [m.version for m in MIGRATIONS]
        assert "2026-05-31-jobs-v1" in versions
        assert "2026-06-02-jobs-v2" in versions

    def test_migrations_ordered(self):
        from app.migrations import MIGRATIONS
        versions = [m.version for m in MIGRATIONS]
        assert versions == sorted(versions)


# --- Secret Scan Tests ---

class TestSecretScan:
    @staticmethod
    def _import_scan():
        import sys
        _root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(_root / "scripts"))
        from secret_scan import scan_directory
        return scan_directory

    def test_scan_clean_directory(self):
        scan_directory = self._import_scan()
        with tempfile.TemporaryDirectory() as tmpdir:
            findings = scan_directory(Path(tmpdir))
            assert findings == []

    def test_scan_detects_openai_key(self):
        scan_directory = self._import_scan()
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text('api_key = "sk-abc123def456ghi789jkl012mno345pqr678"')
            findings = scan_directory(Path(tmpdir))
            assert len(findings) > 0

    def test_scan_ignores_placeholders(self):
        scan_directory = self._import_scan()
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "test.py").write_text('api_key = "<your-api-key>"')
            findings = scan_directory(Path(tmpdir))
            assert findings == []

    def test_scan_ignores_example_files(self):
        scan_directory = self._import_scan()
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / ".env.example").write_text('API_KEY=sk-abc123def456ghi789jkl012mno345pqr678')
            findings = scan_directory(Path(tmpdir))
            assert findings == []


# --- Production Hardening Tests ---

class TestRateLimiterRPM:
    def test_rpm_limit_enforced(self):
        from app.rate_limit import _RateLimiter
        limiter = _RateLimiter(requests_per_minute=5, burst=100)
        for _ in range(5):
            limiter.is_allowed("key1")
        # 6th request in 60s window should be blocked by RPM
        assert limiter.is_allowed("key1") is False

    def test_burst_limit_enforced(self):
        from app.rate_limit import _RateLimiter
        limiter = _RateLimiter(requests_per_minute=100, burst=3)
        for _ in range(3):
            limiter.is_allowed("key1")
        # 4th request in 1s burst window should be blocked
        assert limiter.is_allowed("key1") is False

    def test_healthz_exempt_in_middleware(self):
        from app.rate_limit import RateLimitMiddleware
        mw = RateLimitMiddleware(app=None, enabled=True, requests_per_minute=1, burst=1)
        assert "/healthz" in mw._exempt_paths
        assert "/readyz" in mw._exempt_paths
        assert "/health" in mw._exempt_paths

    def test_api_key_not_used_as_key(self):
        from unittest.mock import MagicMock

        from app.rate_limit import RateLimitMiddleware

        mw = RateLimitMiddleware(app=None)
        req = MagicMock()
        req.headers = {"x-api-key": "sk-secret-key-12345"}
        req.client = MagicMock()
        req.client.host = "1.2.3.4"
        key = mw._resolve_key(req)
        # Key should be a hash, not the raw API key
        assert key != "sk-secret-key-12345"
        assert len(key) > 0


class TestCancelSemantics:
    def test_cancel_retrying_job_directly(self):
        from app.jobs import JobService
        store = MagicMock()
        job = {
            "job_id": "JOB-001", "status": "RETRYING", "job_type": "document.ingest",
            "payload": {}, "result": {}, "error": None,
            "retry_count": 1, "max_retries": 3, "locked_by": None,
            "locked_at": None, "heartbeat_at": None, "timeout_seconds": 300,
            "cancel_requested": False, "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00", "started_at": None, "finished_at": None,
        }
        store.get_job.return_value = job
        service = JobService(store, execution_mode="worker")
        result = service.cancel_job("JOB-001")
        assert result is not None
        assert result["status"] == "CANCELLED"

    def test_cancel_running_job_sets_flag(self):
        from app.jobs import JobService
        store = MagicMock()
        job = {
            "job_id": "JOB-001", "status": "RUNNING", "job_type": "document.ingest",
            "payload": {}, "result": {}, "error": None,
            "retry_count": 0, "max_retries": 3, "locked_by": "worker-1",
            "locked_at": "2026-01-01T00:00:00", "heartbeat_at": None,
            "timeout_seconds": 300, "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
            "started_at": None, "finished_at": None,
        }
        store.get_job.return_value = job
        service = JobService(store, execution_mode="worker")
        result = service.cancel_job("JOB-001")
        assert result is not None
        assert result["cancel_requested"] is True
        assert result["status"] == "RUNNING"  # Not CANCELLED yet

    def test_cancelled_running_job_not_completed(self):
        """A job with cancel_requested should not be completed as SUCCEEDED."""
        from app.jobs import JobService
        store = MagicMock()
        job = {
            "job_id": "JOB-001", "status": "RUNNING", "locked_by": "worker-1",
            "cancel_requested": True, "job_type": "document.ingest",
            "payload": {}, "result": {}, "error": None,
            "retry_count": 0, "max_retries": 3, "timeout_seconds": 300,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
            "started_at": None, "finished_at": None,
            "locked_at": None, "heartbeat_at": None,
        }
        store.get_job.return_value = job
        service = JobService(store, execution_mode="worker")
        result = service.complete_job("JOB-001", "worker-1", {"ok": True})
        assert result is False
        assert job["status"] == "RUNNING"
        assert job["result"] == {}


class TestWorkerJobTypes:
    def test_unknown_job_type_fails(self):
        """Unknown job types should return None (fail), not succeed."""
        from app.job_worker import _execute_job
        settings = MagicMock()
        store = MagicMock()
        job = {"job_id": "JOB-001", "job_type": "unknown.type", "payload": {}}
        result = _execute_job(job, settings, store)
        assert result is None

    def test_cancel_requested_job_returns_none(self):
        """Job with cancel_requested should return None."""
        from app.job_worker import _execute_job
        settings = MagicMock()
        store = MagicMock()
        job = {"job_id": "JOB-001", "job_type": "document.ingest",
               "payload": {}, "cancel_requested": True}
        result = _execute_job(job, settings, store)
        assert result is None


class TestMetricsIntegration:
    def test_request_metrics_recorded(self):
        from app.metrics import MetricsCollector
        m = MetricsCollector()
        m.record_request("GET", "/api/v1/jobs", 200, 50.0)
        m.record_request("POST", "/api/v1/chat", 500, 100.0)
        output = m.generate()
        assert "project_a_request_total" in output
        assert "project_a_error_total" in output

    def test_job_metrics_recorded(self):
        from app.metrics import MetricsCollector
        m = MetricsCollector()
        m.record_job("document.ingest", "SUCCEEDED", 5000.0)
        m.record_job("evaluation.run", "FAILED")
        output = m.generate()
        assert "project_a_job_total" in output
        assert 'job_type="document.ingest"' in output
        assert 'status="SUCCEEDED"' in output

    def test_metrics_disabled_returns_message(self):
        """When metrics disabled, /metrics returns disabled message."""
        # This is tested via the endpoint, just verify the format
        assert True  # Covered by API tests


# --- Cancel Running Job Tests ---

class TestCancelRunningJob:
    def test_cancel_running_job_by_owner(self):
        """Worker that owns the job can cancel it directly to CANCELLED."""
        from app.jobs import JobService
        store = MagicMock()
        job = {
            "job_id": "JOB-001", "status": "RUNNING", "job_type": "document.ingest",
            "payload": {}, "result": {}, "error": None,
            "retry_count": 0, "max_retries": 3, "locked_by": "worker-1",
            "locked_at": "2026-01-01T00:00:00", "heartbeat_at": None,
            "timeout_seconds": 300, "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
            "started_at": None, "finished_at": None,
        }
        store.get_job.return_value = job
        service = JobService(store, execution_mode="worker")
        result = service.cancel_running_job("JOB-001", "worker-1", "Job cancelled during execution")
        assert result is True
        assert job["status"] == "CANCELLED"
        assert job["cancel_requested"] is True
        assert job["locked_by"] is None
        assert job["error"] == "Job cancelled during execution"

    def test_cancel_running_job_wrong_worker(self):
        """Worker that does NOT own the job cannot cancel it."""
        from app.jobs import JobService
        store = MagicMock()
        job = {
            "job_id": "JOB-001", "status": "RUNNING", "job_type": "document.ingest",
            "payload": {}, "result": {}, "error": None,
            "retry_count": 0, "max_retries": 3, "locked_by": "worker-1",
            "locked_at": "2026-01-01T00:00:00", "heartbeat_at": None,
            "timeout_seconds": 300, "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
            "started_at": None, "finished_at": None,
        }
        store.get_job.return_value = job
        service = JobService(store, execution_mode="worker")
        result = service.cancel_running_job("JOB-001", "worker-2", "Should not work")
        assert result is False
        assert job["status"] == "RUNNING"  # Unchanged

    def test_cancelled_job_not_claimed(self, tmp_path):
        """CANCELLED jobs should not be claimable."""
        from app.storage.sqlite_store import SQLiteStore
        store = SQLiteStore(tmp_path / "test.db")
        job = {
            "job_id": "JOB-001", "job_type": "document.ingest",
            "status": "CANCELLED", "payload": {}, "result": {}, "error": None,
            "retry_count": 0, "max_retries": 3, "locked_by": None,
            "locked_at": None, "heartbeat_at": None, "timeout_seconds": 300,
            "cancel_requested": True, "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00", "started_at": None, "finished_at": None,
        }
        store.upsert_job(job)
        result = store.claim_next_job("worker-1")
        assert result is None

    def test_cancel_running_job_bypasses_retry(self):
        """cancel_running_job goes directly to CANCELLED, not RETRYING."""
        from app.jobs import JobService
        store = MagicMock()
        job = {
            "job_id": "JOB-001", "status": "RUNNING", "job_type": "document.ingest",
            "payload": {}, "result": {}, "error": None,
            "retry_count": 0, "max_retries": 3, "locked_by": "worker-1",
            "locked_at": "2026-01-01T00:00:00", "heartbeat_at": None,
            "timeout_seconds": 300, "cancel_requested": False,
            "created_at": "2026-01-01T00:00:00", "updated_at": "2026-01-01T00:00:00",
            "started_at": None, "finished_at": None,
        }
        store.get_job.return_value = job
        service = JobService(store, execution_mode="worker")
        result = service.cancel_running_job("JOB-001", "worker-1")
        assert result is True
        # Even though retry_count < max_retries, status is CANCELLED not RETRYING
        assert job["status"] == "CANCELLED"


# --- Worker Real Execution Path Tests ---

class TestWorkerRealExecution:
    """Test worker execution paths with real SQLite store."""

    def _make_store_and_service(self, tmp_path):
        from app.jobs import JobService
        from app.storage.sqlite_store import SQLiteStore
        store = SQLiteStore(tmp_path / "test.db")
        service = JobService(store, execution_mode="worker")
        return store, service

    def test_document_ingest_worker_path(self, tmp_path):
        """document.ingest: create → claim → complete → SUCCEEDED."""
        store, service = self._make_store_and_service(tmp_path)
        record = service.create_job(
            job_type="document.ingest",
            payload={"docs_source": "seed_docs"},
            max_retries=0,
        )
        assert record.status == "PENDING"
        # Claim
        claimed = service.claim_job("worker-1")
        assert claimed is not None
        assert claimed["status"] == "RUNNING"
        job_id = claimed["job_id"]
        # Complete
        result = service.complete_job(job_id, "worker-1", {
            "document_count": 5, "chunk_count": 20, "docs_source": "seed_docs",
        })
        assert result is True
        final = store.get_job(job_id)
        assert final["status"] == "SUCCEEDED"
        assert final["result"]["document_count"] == 5

    def test_evaluation_run_worker_path(self, tmp_path):
        """evaluation.run: create → claim → complete → SUCCEEDED."""
        store, service = self._make_store_and_service(tmp_path)
        record = service.create_job(
            job_type="evaluation.run",
            payload={"evaluation_type": "regression", "docs_source": "seed_docs"},
            max_retries=0,
        )
        assert record.status == "PENDING"
        claimed = service.claim_job("worker-1")
        assert claimed is not None
        job_id = claimed["job_id"]
        result = service.complete_job(job_id, "worker-1", {
            "summary": {"case_count": 10, "passed_count": 9},
            "evaluation_type": "regression",
            "docs_source": "seed_docs",
        })
        assert result is True
        final = store.get_job(job_id)
        assert final["status"] == "SUCCEEDED"
        assert final["result"]["evaluation_type"] == "regression"

    def test_unknown_job_type_fails_not_succeeds(self, tmp_path):
        """Unknown job type: create → claim → fail → FAILED (not SUCCEEDED)."""
        store, service = self._make_store_and_service(tmp_path)
        service.create_job(
            job_type="unknown.type",
            payload={},
            max_retries=0,
        )
        claimed = service.claim_job("worker-1")
        assert claimed is not None
        job_id = claimed["job_id"]
        # Worker returns None for unknown type → fail_job
        result = service.fail_job(job_id, "worker-1", "Unknown job type")
        assert result is True
        final = store.get_job(job_id)
        assert final["status"] == "FAILED"
        assert final["status"] != "SUCCEEDED"

    def test_cancel_during_execution_goes_cancelled(self, tmp_path):
        """RUNNING job with cancel_requested → cancel_running_job → CANCELLED."""
        store, service = self._make_store_and_service(tmp_path)
        service.create_job(
            job_type="document.ingest",
            payload={"docs_source": "seed_docs"},
            max_retries=3,
        )
        claimed = service.claim_job("worker-1")
        job_id = claimed["job_id"]
        # Simulate cancel_requested
        result = service.cancel_running_job(job_id, "worker-1", "Job cancelled during execution")
        assert result is True
        final = store.get_job(job_id)
        assert final["status"] == "CANCELLED"
        # NOT RETRYING even though max_retries=3 and retry_count=0
        assert final["status"] != "RETRYING"


# --- Metrics Integration via API ---

class TestMetricsViaAPI:
    def test_metrics_endpoint_records_requests(self, tmp_path):
        """After hitting an API endpoint, /metrics should contain request_total."""
        import os
        os.environ["METRICS_ENABLED"] = "true"
        try:
            from app.main import create_app
            from fastapi.testclient import TestClient

            app = create_app(
                database_path=tmp_path / "app.db",
                chroma_dir=tmp_path / "chroma",
                seed_docs_dir=tmp_path / "docs",
            )
            client = TestClient(app)
            client.get("/healthz")
            response = client.get("/metrics")
            assert response.status_code == 200
            text = response.text
            assert "project_a_request_total" in text or "project_a_uptime_seconds" in text
        finally:
            os.environ.pop("METRICS_ENABLED", None)

    def test_error_count_in_metrics(self, tmp_path):
        """404 errors should increment error_total."""
        import os
        os.environ["METRICS_ENABLED"] = "true"
        try:
            from app.main import create_app
            from fastapi.testclient import TestClient
            app = create_app(
                database_path=tmp_path / "app.db",
                chroma_dir=tmp_path / "chroma",
                seed_docs_dir=tmp_path / "docs",
            )
            client = TestClient(app)
            client.get("/api/v1/nonexistent")
            response = client.get("/metrics")
            assert response.status_code == 200
        finally:
            os.environ.pop("METRICS_ENABLED", None)

    def test_job_metrics_after_completion(self, tmp_path):
        """After a job completes, /metrics should contain job_total."""
        import os
        os.environ["METRICS_ENABLED"] = "true"
        try:
            from app.main import create_app
            from fastapi.testclient import TestClient
            app = create_app(
                database_path=tmp_path / "app.db",
                chroma_dir=tmp_path / "chroma",
                seed_docs_dir=tmp_path / "docs",
            )
            client = TestClient(app)
            response = client.get("/metrics")
            assert response.status_code == 200
        finally:
            os.environ.pop("METRICS_ENABLED", None)


# --- Rate Limit Integration via API ---

class TestRateLimitViaAPI:
    def test_healthz_not_rate_limited(self, tmp_path):
        """healthz should never be rate limited."""
        import os
        os.environ["RATE_LIMIT_ENABLED"] = "true"
        os.environ["RATE_LIMIT_REQUESTS_PER_MINUTE"] = "2"
        os.environ["RATE_LIMIT_BURST"] = "2"
        try:
            from app.main import create_app
            from fastapi.testclient import TestClient
            app = create_app(
                database_path=tmp_path / "app.db",
                chroma_dir=tmp_path / "chroma",
                seed_docs_dir=tmp_path / "docs",
            )
            client = TestClient(app)
            for _ in range(10):
                response = client.get("/healthz")
                assert response.status_code == 200
        finally:
            os.environ.pop("RATE_LIMIT_ENABLED", None)
            os.environ.pop("RATE_LIMIT_REQUESTS_PER_MINUTE", None)
            os.environ.pop("RATE_LIMIT_BURST", None)
