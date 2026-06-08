"""Enterprise landing guardrails for production configuration."""
from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_production_compose_defaults_are_fail_closed() -> None:
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "AUTH_ENABLED: ${AUTH_ENABLED:-true}" in compose
    assert "CACHE_ENABLED: ${CACHE_ENABLED:-true}" in compose
    assert "RATE_LIMIT_ENABLED: ${RATE_LIMIT_ENABLED:-true}" in compose
    assert "RATE_LIMIT_BACKEND: ${RATE_LIMIT_BACKEND:-redis}" in compose
    assert "RATE_LIMIT_REDIS_URL: ${RATE_LIMIT_REDIS_URL:-redis://redis:6379/0}" in compose
    assert "CORS_ALLOW_ORIGINS: ${CORS_ALLOW_ORIGINS:-" in compose


def test_env_production_example_documents_redis_rate_limit() -> None:
    env_text = (PROJECT_ROOT / ".env.production.example").read_text(encoding="utf-8")

    assert "AUTH_ENABLED=true" in env_text
    assert "CACHE_ENABLED=true" in env_text
    assert "RATE_LIMIT_ENABLED=true" in env_text
    assert "RATE_LIMIT_BACKEND=redis" in env_text
    assert "RATE_LIMIT_REDIS_URL=redis://redis:6379/0" in env_text
    assert "DATABASE_URL password must match POSTGRES_PASSWORD" in env_text


def test_dockerfile_installs_production_extras() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert 'pip install --no-cache-dir -e ".[cache,postgres,vector]"' in dockerfile


def test_storage_factory_uses_postgres_backend(monkeypatch) -> None:
    from app.storage import factory

    created: dict[str, str] = {}

    class FakePostgresStore:
        def __init__(self, database_url: str) -> None:
            created["database_url"] = database_url

    monkeypatch.setattr(factory, "PostgresStore", FakePostgresStore)

    settings = SimpleNamespace(
        storage_backend="postgres",
        database_url="postgresql://user:pass@postgres:5432/project_a",
        database_path=PROJECT_ROOT / "data" / "unused.db",
    )
    store = factory.build_store(settings)

    assert isinstance(store, FakePostgresStore)
    assert created["database_url"] == settings.database_url


def test_storage_factory_rejects_unknown_backend() -> None:
    from app.storage.factory import build_store

    settings = SimpleNamespace(
        storage_backend="unknown",
        database_url="",
        database_path=PROJECT_ROOT / "data" / "unused.db",
    )

    try:
        build_store(settings)
    except ValueError as exc:
        assert "STORAGE_BACKEND" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("unknown storage backend should fail")


def test_worker_processes_one_claimed_job_to_success() -> None:
    from app.job_worker import process_one_job
    from app.jobs import JobService

    class Store:
        def __init__(self) -> None:
            self.job = {
                "job_id": "JOB-001",
                "job_type": "document.ingest",
                "status": "PENDING",
                "payload": {"docs_source": "seed_docs"},
                "result": {},
                "error": None,
                "retry_count": 0,
                "max_retries": 1,
                "locked_by": None,
                "locked_at": None,
                "heartbeat_at": None,
                "timeout_seconds": 300,
                "cancel_requested": False,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "started_at": None,
            }

        def claim_next_job(self, worker_id: str):
            if self.job["status"] != "PENDING":
                return None
            self.job["status"] = "RUNNING"
            self.job["locked_by"] = worker_id
            return dict(self.job)

        def get_job(self, job_id: str):
            return dict(self.job) if job_id == self.job["job_id"] else None

        def update_job(self, job: dict) -> None:
            self.job.update(job)

    store = Store()
    service = JobService(store, execution_mode="worker")

    assert process_one_job(
        service=service,
        worker_id="worker-1",
        executor=lambda job: {"document_count": 1, "chunk_count": 2},
    )
    assert store.job["status"] == "SUCCEEDED"
    assert store.job["result"]["chunk_count"] == 2
    assert store.job["locked_by"] is None
    assert store.job["finished_at"]


def test_worker_heartbeats_during_long_execution() -> None:
    from app.job_worker import process_one_job
    from app.jobs import JobService

    class Store:
        def __init__(self) -> None:
            self.heartbeat_count = 0
            self.job = {
                "job_id": "JOB-heartbeat",
                "job_type": "document.ingest",
                "status": "PENDING",
                "payload": {},
                "result": {},
                "error": None,
                "retry_count": 0,
                "max_retries": 1,
                "locked_by": None,
                "locked_at": None,
                "heartbeat_at": None,
                "timeout_seconds": 3,
                "cancel_requested": False,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "started_at": None,
            }

        def claim_next_job(self, worker_id: str):
            self.job["status"] = "RUNNING"
            self.job["locked_by"] = worker_id
            return dict(self.job)

        def get_job(self, job_id: str):
            return dict(self.job) if job_id == self.job["job_id"] else None

        def update_job(self, job: dict) -> None:
            if job.get("heartbeat_at"):
                self.heartbeat_count += 1
            self.job.update(job)

    store = Store()
    service = JobService(store, execution_mode="worker")

    assert process_one_job(
        service=service,
        worker_id="worker-1",
        executor=lambda job: (time.sleep(1.2) or {"document_count": 1}),
    )
    assert store.heartbeat_count >= 1
    assert store.job["status"] == "SUCCEEDED"


def test_worker_heartbeat_converts_cancel_requested_job_to_cancelled(monkeypatch) -> None:
    from app import job_worker
    from app.job_worker import process_one_job
    from app.jobs import JobService

    class Store:
        def __init__(self) -> None:
            self.job = {
                "job_id": "JOB-heartbeat-cancel",
                "job_type": "document.ingest",
                "status": "PENDING",
                "payload": {},
                "result": {},
                "error": None,
                "retry_count": 0,
                "max_retries": 3,
                "locked_by": None,
                "locked_at": None,
                "heartbeat_at": None,
                "timeout_seconds": 3,
                "cancel_requested": False,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "started_at": None,
                "finished_at": None,
            }

        def claim_next_job(self, worker_id: str):
            self.job["status"] = "RUNNING"
            self.job["locked_by"] = worker_id
            return dict(self.job)

        def get_job(self, job_id: str):
            return dict(self.job) if job_id == self.job["job_id"] else None

        def update_job(self, job: dict) -> None:
            self.job.update(job)

    store = Store()
    service = JobService(store, execution_mode="worker")
    recorded: list[tuple[str, str]] = []

    def executor(job):
        time.sleep(0.2)
        service.cancel_job(job["job_id"])
        time.sleep(1.2)
        return {"document_count": 1}

    monkeypatch.setattr(job_worker, "_record_worker_job_metric", lambda jt, st: recorded.append((jt, st)))
    assert process_one_job(service=service, worker_id="worker-1", executor=executor)
    assert store.job["status"] == "CANCELLED"
    assert store.job["cancel_requested"] is True
    assert store.job["result"] == {}
    assert store.job["locked_by"] is None
    assert recorded == [("document.ingest", "CANCELLED")]


def test_worker_heartbeat_interval_is_bounded() -> None:
    from app.job_worker import _heartbeat_interval_seconds

    assert _heartbeat_interval_seconds({"timeout_seconds": 3}) == 1.0
    assert _heartbeat_interval_seconds({"timeout_seconds": 300}) == 30.0
    assert _heartbeat_interval_seconds({"timeout_seconds": "bad"}) == 30.0


def test_async_job_endpoints_pass_configured_timeout() -> None:
    source = (PROJECT_ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")

    assert source.count("timeout_seconds=settings.job_default_timeout_seconds") >= 2


def test_worker_cancels_running_job_when_cancel_requested() -> None:
    from app.job_worker import process_one_job
    from app.jobs import JobService

    class Store:
        def __init__(self) -> None:
            self.job = {
                "job_id": "JOB-002",
                "job_type": "document.ingest",
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
                "cancel_requested": True,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "started_at": None,
            }

        def claim_next_job(self, worker_id: str):
            self.job["status"] = "RUNNING"
            self.job["locked_by"] = worker_id
            return dict(self.job)

        def get_job(self, job_id: str):
            return dict(self.job) if job_id == self.job["job_id"] else None

        def update_job(self, job: dict) -> None:
            self.job.update(job)

    store = Store()
    service = JobService(store, execution_mode="worker")

    assert process_one_job(
        service=service,
        worker_id="worker-1",
        executor=lambda job: {"should_not_run": True},
    )
    assert store.job["status"] == "CANCELLED"
    assert store.job["retry_count"] == 0
    assert store.job["locked_by"] is None


def test_postgres_store_jobs_column_migration_is_idempotent() -> None:
    from app.storage.postgres_store import PostgresStore

    class FakeConn:
        def __init__(self) -> None:
            self.statements: list[str] = []

        def execute(self, sql: str) -> None:
            self.statements.append(sql)

    conn = FakeConn()
    PostgresStore._ensure_jobs_columns(conn)

    assert any("ADD COLUMN IF NOT EXISTS finished_at TEXT" in s for s in conn.statements)
    assert all("ADD COLUMN IF NOT EXISTS" in s for s in conn.statements)


def test_sqlite_store_migrates_existing_jobs_table_finished_at(tmp_path) -> None:
    import sqlite3

    from app.storage.sqlite_store import SqliteStore

    db_path = tmp_path / "legacy_jobs.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            payload TEXT DEFAULT '{}',
            result TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            started_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()

    store = SqliteStore(db_path)
    columns = {row["name"] for row in store._conn.execute("PRAGMA table_info(jobs)")}

    assert "finished_at" in columns


def test_worker_does_not_record_success_when_complete_is_rejected(monkeypatch) -> None:
    from app import job_worker

    class Service:
        def claim_next_job(self, worker_id: str):
            return {
                "job_id": "JOB-rejected",
                "job_type": "document.ingest",
                "status": "RUNNING",
                "cancel_requested": False,
            }

        def complete_job(self, job_id: str, worker_id: str, result: dict) -> bool:
            return False

        def get_job(self, job_id: str):
            return {
                "job_id": job_id,
                "job_type": "document.ingest",
                "status": "RUNNING",
                "cancel_requested": False,
            }

    recorded: list[tuple[str, str]] = []
    monkeypatch.setattr(job_worker, "_record_worker_job_metric", lambda jt, st: recorded.append((jt, st)))

    assert job_worker.process_one_job(
        service=Service(),
        worker_id="worker-1",
        executor=lambda job: {"document_count": 1},
    )
    assert recorded == [("document.ingest", "RUNNING")]


def test_worker_records_actual_status_when_fail_is_rejected(monkeypatch) -> None:
    from app import job_worker

    class Service:
        def claim_next_job(self, worker_id: str):
            return {
                "job_id": "JOB-fail-rejected",
                "job_type": "unknown.type",
                "status": "RUNNING",
                "cancel_requested": False,
            }

        def fail_job(self, job_id: str, worker_id: str, error: str) -> bool:
            return False

        def get_job(self, job_id: str):
            return {
                "job_id": job_id,
                "job_type": "unknown.type",
                "status": "RUNNING",
                "cancel_requested": False,
            }

    recorded: list[tuple[str, str]] = []
    monkeypatch.setattr(job_worker, "_record_worker_job_metric", lambda jt, st: recorded.append((jt, st)))

    assert job_worker.process_one_job(
        service=Service(),
        worker_id="worker-1",
        executor=lambda job: None,
    )
    assert recorded == [("unknown.type", "RUNNING")]


def test_postgres_store_declares_atomic_job_transitions() -> None:
    source = (PROJECT_ROOT / "backend" / "app" / "storage" / "postgres_store.py").read_text(
        encoding="utf-8"
    )

    assert "def try_request_cancel_job" in source
    assert "def timeout_stale_jobs" in source
    assert "def try_complete_job" in source
    assert "def try_fail_job" in source
    assert "def try_heartbeat_job" in source
    assert "def try_cancel_running_job" in source
    assert "status = 'RUNNING'" in source
    assert "locked_by = %s" in source
    assert "COALESCE(cancel_requested, 0) = 0" in source
    assert "status NOT IN ('SUCCEEDED', 'FAILED', 'CANCELLED')" in source
    assert "FOR UPDATE SKIP LOCKED" in source
