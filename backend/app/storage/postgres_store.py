"""PostgreSQL storage backend for Project A RAG Platform."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.rag.costing import TokenUsage
from app.storage.base import Store

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - exercised through deployment preflight
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


class PostgresStore(Store):
    """PostgreSQL implementation of the Store interface.

    Connections are opened per operation.  This keeps the implementation
    predictable for API and worker processes and avoids sharing connection
    objects across threads.
    """

    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("DATABASE_URL is required for PostgresStore.")
        if psycopg is None or dict_row is None or Jsonb is None:
            raise RuntimeError(
                "PostgresStore requires psycopg with pool/binary extras. "
                "Install with: pip install 'psycopg[binary,pool]'"
            )
        self._database_url = database_url
        self._init_schema()

    def _connect(self):
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    payload JSONB DEFAULT '{}'::jsonb,
                    result JSONB DEFAULT '{}'::jsonb,
                    error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    locked_by TEXT,
                    locked_at TEXT,
                    heartbeat_at TEXT,
                    timeout_seconds INTEGER DEFAULT 300,
                    cancel_requested INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    path TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id BIGSERIAL PRIMARY KEY,
                    action TEXT NOT NULL,
                    actor_role TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    summary TEXT,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_records (
                    id BIGSERIAL PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    citations TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    question TEXT NOT NULL,
                    diagnosis TEXT NOT NULL,
                    citations JSONB NOT NULL,
                    device_model TEXT,
                    fault_code TEXT,
                    risk_level TEXT NOT NULL,
                    status TEXT NOT NULL,
                    required_parts JSONB NOT NULL,
                    human_required INTEGER NOT NULL,
                    human_decision TEXT,
                    human_reviewer TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    closed_by TEXT,
                    closed_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS token_usage (
                    request_id TEXT PRIMARY KEY,
                    module TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    estimated_cost DOUBLE PRECISION NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            self._ensure_jobs_columns(conn)
            conn.commit()

    @staticmethod
    def _ensure_jobs_columns(conn) -> None:
        columns = {
            "retry_count": "INTEGER DEFAULT 0",
            "max_retries": "INTEGER DEFAULT 3",
            "locked_by": "TEXT",
            "locked_at": "TEXT",
            "heartbeat_at": "TEXT",
            "timeout_seconds": "INTEGER DEFAULT 300",
            "cancel_requested": "INTEGER DEFAULT 0",
            "started_at": "TEXT",
            "finished_at": "TEXT",
        }
        for column, definition in columns.items():
            conn.execute(f"ALTER TABLE jobs ADD COLUMN IF NOT EXISTS {column} {definition}")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _json_value(value: Any, default: Any) -> Any:
        if value is None:
            return default
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        return value

    def add_document(self, document_id: str, source: str, path: str, chunk_count: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (id, source, path, chunk_count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    source = EXCLUDED.source,
                    path = EXCLUDED.path,
                    chunk_count = EXCLUDED.chunk_count
                """,
                (document_id, source, path, chunk_count),
            )
            conn.commit()

    def create_job(self, job: dict) -> None:
        if "job_id" not in job or not job["job_id"]:
            job["job_id"] = f"JOB-{uuid.uuid4().hex[:8]}"
        now = self._now()
        job.setdefault("created_at", now)
        job.setdefault("updated_at", now)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, job_type, status, payload, result, error,
                    retry_count, max_retries, locked_by, locked_at, heartbeat_at,
                    timeout_seconds, cancel_requested, created_at, updated_at,
                    started_at, finished_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (job_id) DO UPDATE SET
                    job_type = EXCLUDED.job_type,
                    status = EXCLUDED.status,
                    payload = EXCLUDED.payload,
                    result = EXCLUDED.result,
                    error = EXCLUDED.error,
                    retry_count = EXCLUDED.retry_count,
                    max_retries = EXCLUDED.max_retries,
                    locked_by = EXCLUDED.locked_by,
                    locked_at = EXCLUDED.locked_at,
                    heartbeat_at = EXCLUDED.heartbeat_at,
                    timeout_seconds = EXCLUDED.timeout_seconds,
                    cancel_requested = EXCLUDED.cancel_requested,
                    created_at = EXCLUDED.created_at,
                    updated_at = EXCLUDED.updated_at,
                    started_at = EXCLUDED.started_at,
                    finished_at = EXCLUDED.finished_at
                """,
                (
                    job.get("job_id"),
                    job.get("job_type", ""),
                    job.get("status", "PENDING"),
                    Jsonb(job.get("payload", {})),
                    Jsonb(job.get("result", {})),
                    job.get("error"),
                    job.get("retry_count", 0),
                    job.get("max_retries", 3),
                    job.get("locked_by"),
                    job.get("locked_at"),
                    job.get("heartbeat_at"),
                    job.get("timeout_seconds", 300),
                    1 if job.get("cancel_requested") else 0,
                    job.get("created_at", now),
                    job.get("updated_at", now),
                    job.get("started_at"),
                    job.get("finished_at"),
                ),
            )
            conn.commit()

    def get_job(self, job_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = %s", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def update_job(self, job: dict) -> None:
        job["updated_at"] = self._now()
        if job.get("status") in {"SUCCEEDED", "FAILED", "CANCELLED"} and not job.get("finished_at"):
            job["finished_at"] = job["updated_at"]
        self.create_job(job)

    def upsert_job(self, job: dict) -> None:
        self.create_job(job)

    def list_jobs(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def claim_next_job(self, worker_id: str) -> dict | None:
        now = self._now()
        with self._connect() as conn:
            row = conn.execute(
                """
                WITH candidate AS (
                    SELECT job_id
                    FROM jobs
                    WHERE status IN ('PENDING', 'RETRYING')
                      AND COALESCE(cancel_requested, 0) = 0
                      AND (locked_by IS NULL OR locked_by = '')
                    ORDER BY created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE jobs
                SET status = 'RUNNING',
                    locked_by = %s,
                    locked_at = %s,
                    heartbeat_at = %s,
                    started_at = COALESCE(started_at, %s),
                    updated_at = %s
                WHERE job_id = (SELECT job_id FROM candidate)
                RETURNING *
                """,
                (worker_id, now, now, now, now),
            ).fetchone()
            conn.commit()
        return self._row_to_job(row) if row else None

    def try_request_cancel_job(self, job_id: str, now: str) -> dict | None:
        """Atomically request cancellation without overwriting terminal jobs."""
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE jobs
                SET cancel_requested = 1,
                    status = CASE
                        WHEN status = 'RUNNING' THEN status
                        ELSE 'CANCELLED'
                    END,
                    locked_by = CASE WHEN status = 'RUNNING' THEN locked_by ELSE NULL END,
                    locked_at = CASE WHEN status = 'RUNNING' THEN locked_at ELSE NULL END,
                    heartbeat_at = CASE WHEN status = 'RUNNING' THEN heartbeat_at ELSE NULL END,
                    finished_at = CASE WHEN status = 'RUNNING' THEN finished_at ELSE %s END,
                    updated_at = %s
                WHERE job_id = %s
                  AND status NOT IN ('SUCCEEDED', 'FAILED', 'CANCELLED')
                RETURNING *
                """,
                (now, now, job_id),
            ).fetchone()
            conn.commit()
        return self._row_to_job(row) if row else None

    def try_complete_job(self, job_id: str, worker_id: str, result: dict, now: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE jobs
                SET status = 'SUCCEEDED', result = %s, locked_by = NULL,
                    locked_at = NULL, heartbeat_at = NULL, finished_at = %s, updated_at = %s
                WHERE job_id = %s
                  AND status = 'RUNNING'
                  AND locked_by = %s
                  AND COALESCE(cancel_requested, 0) = 0
                RETURNING job_id
                """,
                (Jsonb(result), now, now, job_id, worker_id),
            ).fetchone()
            conn.commit()
        return row is not None

    def try_fail_job(self, job_id: str, worker_id: str, error: str, now: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                WITH current_job AS (
                    SELECT retry_count, max_retries
                    FROM jobs
                    WHERE job_id = %s
                      AND status = 'RUNNING'
                      AND locked_by = %s
                      AND COALESCE(cancel_requested, 0) = 0
                    FOR UPDATE
                )
                UPDATE jobs
                SET retry_count = COALESCE(current_job.retry_count, 0) + 1,
                    status = CASE
                        WHEN COALESCE(current_job.retry_count, 0) + 1 >= COALESCE(current_job.max_retries, 3)
                        THEN 'FAILED'
                        ELSE 'RETRYING'
                    END,
                    error = %s,
                    locked_by = NULL,
                    locked_at = NULL,
                    heartbeat_at = NULL,
                    finished_at = CASE
                        WHEN COALESCE(current_job.retry_count, 0) + 1 >= COALESCE(current_job.max_retries, 3)
                        THEN %s
                        ELSE NULL
                    END,
                    updated_at = %s
                FROM current_job
                WHERE jobs.job_id = %s
                RETURNING jobs.job_id
                """,
                (job_id, worker_id, error, now, now, job_id),
            ).fetchone()
            conn.commit()
        return row is not None

    def try_heartbeat_job(self, job_id: str, worker_id: str, now: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE jobs
                SET heartbeat_at = %s, updated_at = %s
                WHERE job_id = %s AND status = 'RUNNING' AND locked_by = %s
                RETURNING job_id
                """,
                (now, now, job_id, worker_id),
            ).fetchone()
            conn.commit()
        return row is not None

    def try_cancel_running_job(
        self,
        job_id: str,
        worker_id: str,
        reason: str | None,
        now: str,
    ) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE jobs
                SET status = 'CANCELLED', cancel_requested = 1, error = COALESCE(%s, error),
                    locked_by = NULL, locked_at = NULL, heartbeat_at = NULL,
                    finished_at = %s, updated_at = %s
                WHERE job_id = %s AND status = 'RUNNING' AND locked_by = %s
                RETURNING job_id
                """,
                (reason, now, now, job_id, worker_id),
            ).fetchone()
            conn.commit()
        return row is not None


    def list_chat_records(self) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_records ORDER BY id DESC LIMIT 100"
            ).fetchall()
        return [dict(row) for row in rows]

    def add_chat_record(self, question: str, answer: str, citations: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO chat_records (question, answer, citations) VALUES (%s, %s, %s)",
                (question, answer, citations),
            )
            conn.commit()

    def add_token_usage(self, usage: TokenUsage) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO token_usage (
                    request_id, module, prompt_tokens, completion_tokens,
                    total_tokens, estimated_cost
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (request_id) DO UPDATE SET
                    module = EXCLUDED.module,
                    prompt_tokens = EXCLUDED.prompt_tokens,
                    completion_tokens = EXCLUDED.completion_tokens,
                    total_tokens = EXCLUDED.total_tokens,
                    estimated_cost = EXCLUDED.estimated_cost
                """,
                (
                    usage.request_id,
                    usage.module,
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.total_tokens,
                    usage.estimated_cost,
                ),
            )
            conn.commit()

    def upsert_ticket(self, ticket: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tickets (
                    ticket_id, idempotency_key, question, diagnosis, citations,
                    device_model, fault_code, risk_level, status, required_parts,
                    human_required, human_decision, human_reviewer,
                    created_at, updated_at, closed_by, closed_at
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (ticket_id) DO UPDATE SET
                    idempotency_key = EXCLUDED.idempotency_key,
                    question = EXCLUDED.question,
                    diagnosis = EXCLUDED.diagnosis,
                    citations = EXCLUDED.citations,
                    device_model = EXCLUDED.device_model,
                    fault_code = EXCLUDED.fault_code,
                    risk_level = EXCLUDED.risk_level,
                    status = EXCLUDED.status,
                    required_parts = EXCLUDED.required_parts,
                    human_required = EXCLUDED.human_required,
                    human_decision = EXCLUDED.human_decision,
                    human_reviewer = EXCLUDED.human_reviewer,
                    updated_at = EXCLUDED.updated_at,
                    closed_by = EXCLUDED.closed_by,
                    closed_at = EXCLUDED.closed_at
                """,
                (
                    ticket["ticket_id"],
                    ticket["idempotency_key"],
                    ticket["question"],
                    ticket["diagnosis"],
                    Jsonb(ticket["citations"]),
                    ticket.get("device_model"),
                    ticket.get("fault_code"),
                    ticket["risk_level"],
                    ticket["status"],
                    Jsonb(ticket["required_parts"]),
                    int(ticket["human_required"]),
                    ticket.get("human_decision"),
                    ticket.get("human_reviewer"),
                    ticket["created_at"],
                    ticket["updated_at"],
                    ticket.get("closed_by"),
                    ticket.get("closed_at"),
                ),
            )
            conn.commit()

    def get_ticket(self, ticket_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tickets WHERE ticket_id = %s",
                (ticket_id,),
            ).fetchone()
        return self._ticket_row_to_dict(row) if row else None

    def get_ticket_by_idempotency_key(self, idempotency_key: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tickets WHERE idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
        return self._ticket_row_to_dict(row) if row else None

    def list_tickets(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tickets ORDER BY created_at, ticket_id"
            ).fetchall()
        return [self._ticket_row_to_dict(row) for row in rows]

    def list_audit_events(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_events ORDER BY id DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return [self._audit_row_to_dict(row) for row in rows]

    def record_audit_event(self, event: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (
                    action, actor_role, resource_type, resource_id, summary, metadata, timestamp
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    event.get("action"),
                    event.get("actor_role"),
                    event.get("resource_type"),
                    event.get("resource_id"),
                    event.get("summary"),
                    Jsonb(event.get("metadata", {})),
                    event.get("timestamp"),
                ),
            )
            conn.commit()

    def _row_to_job(self, row: dict) -> dict:
        job = dict(row)
        job["payload"] = self._json_value(job.get("payload"), {})
        job["result"] = self._json_value(job.get("result"), {})
        job["cancel_requested"] = bool(job.get("cancel_requested", 0))
        return job

    def _ticket_row_to_dict(self, row: dict) -> dict:
        ticket = dict(row)
        ticket["citations"] = self._json_value(ticket.get("citations"), [])
        ticket["required_parts"] = self._json_value(ticket.get("required_parts"), [])
        ticket["human_required"] = bool(ticket.get("human_required"))
        return ticket

    def _audit_row_to_dict(self, row: dict) -> dict:
        event = dict(row)
        event["metadata"] = self._json_value(event.get("metadata"), {})
        return event


PostgreSQLStore = PostgresStore
