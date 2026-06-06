"""SQLite storage backend for Project A RAG Platform."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.rag.costing import TokenUsage
from app.storage.base import Store


class SqliteStore(Store):
    def __init__(self, database_path: Path):
        self._db_path = str(database_path)
        self._local = threading.local()
        self._init_schema()

    @property
    def _conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_schema(self):
        conn = self._conn
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                payload TEXT DEFAULT '{}',
                result TEXT DEFAULT '{}',
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
            );
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                path TEXT NOT NULL,
                chunk_count INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                actor_role TEXT,
                resource_type TEXT,
                resource_id TEXT,
                summary TEXT,
                metadata TEXT DEFAULT '{}',
                timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                question TEXT NOT NULL,
                diagnosis TEXT NOT NULL,
                citations TEXT NOT NULL,
                device_model TEXT,
                fault_code TEXT,
                risk_level TEXT NOT NULL,
                status TEXT NOT NULL,
                required_parts TEXT NOT NULL,
                human_required INTEGER NOT NULL,
                human_decision TEXT,
                human_reviewer TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                closed_by TEXT,
                closed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS token_usage (
                request_id TEXT PRIMARY KEY,
                module TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                estimated_cost REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self._ensure_column("jobs", "finished_at", "TEXT")
        conn.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        existing = {row["name"] for row in self._conn.execute(f"PRAGMA table_info({table})")}
        if column not in existing:
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def add_document(self, document_id: str, source: str, path: str, chunk_count: int) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO documents (id, source, path, chunk_count) VALUES (?, ?, ?, ?)",
            (document_id, source, path, chunk_count),
        )
        self._conn.commit()

    def create_job(self, job: dict) -> None:
        if "job_id" not in job:
            job["job_id"] = f"JOB-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        job.setdefault("created_at", now)
        job.setdefault("updated_at", now)
        self._conn.execute(
            """INSERT OR REPLACE INTO jobs (
                job_id, job_type, status, payload, result, error, retry_count,
                max_retries, locked_by, locked_at, heartbeat_at, timeout_seconds,
                cancel_requested, created_at, updated_at, started_at, finished_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (job.get("job_id"), job.get("job_type",""), job.get("status","PENDING"),
             json.dumps(job.get("payload",{})), json.dumps(job.get("result",{})),
             job.get("error"), job.get("retry_count",0), job.get("max_retries",3),
             job.get("locked_by"), job.get("locked_at"), job.get("heartbeat_at"),
             job.get("timeout_seconds",300), 1 if job.get("cancel_requested") else 0,
             job.get("created_at",now), job.get("updated_at",now), job.get("started_at"),
             job.get("finished_at"))
        )
        self._conn.commit()

    def get_job(self, job_id: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def update_job(self, job: dict) -> None:
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        if job.get("status") in {"SUCCEEDED", "FAILED", "CANCELLED"} and not job.get("finished_at"):
            job["finished_at"] = job["updated_at"]
        self.create_job(job)

    def upsert_job(self, job: dict) -> None:
        """Insert or update a job. If job_id exists, update; otherwise insert."""
        existing = self.get_job(job.get("job_id", ""))
        if existing is not None:
            self.update_job(job)
        else:
            self.create_job(job)

    def list_jobs(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._row_to_job(r) for r in rows]

    def claim_next_job(self, worker_id: str) -> dict | None:
        # Use BEGIN IMMEDIATE for atomic claim
        try:
            self._conn.execute("BEGIN IMMEDIATE")
        except Exception:
            # Already in a transaction
            pass
        row = self._conn.execute(
            """SELECT job_id FROM jobs
               WHERE status IN ('PENDING', 'RETRYING')
                 AND COALESCE(cancel_requested, 0) = 0
                 AND (locked_by IS NULL OR locked_by = '')
               ORDER BY created_at ASC LIMIT 1"""
        ).fetchone()
        if row is None:
            try:
                self._conn.rollback()
            except Exception:
                pass
            return None
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """UPDATE jobs SET status = 'RUNNING', locked_by = ?,
               locked_at = ?, heartbeat_at = ?, started_at = ?, updated_at = ?
               WHERE job_id = ?
                 AND status IN ('PENDING', 'RETRYING')
                 AND COALESCE(cancel_requested, 0) = 0""",
            (worker_id, now, now, now, now, row[0]),
        )
        if cursor.rowcount == 0:
            try:
                self._conn.rollback()
            except Exception:
                pass
            return None
        self._conn.commit()
        return self.get_job(row[0])

    def try_request_cancel_job(self, job_id: str, now: str) -> dict | None:
        """Atomically request cancellation without overwriting terminal jobs."""
        try:
            self._conn.execute("BEGIN IMMEDIATE")
        except Exception:
            pass
        row = self._conn.execute(
            "SELECT status FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            try:
                self._conn.rollback()
            except Exception:
                pass
            return None
        if row["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            try:
                self._conn.rollback()
            except Exception:
                pass
            return None

        if row["status"] == "RUNNING":
            cursor = self._conn.execute(
                """UPDATE jobs
                   SET cancel_requested = 1, updated_at = ?
                   WHERE job_id = ? AND status = 'RUNNING'""",
                (now, job_id),
            )
        else:
            cursor = self._conn.execute(
                """UPDATE jobs
                   SET status = 'CANCELLED', cancel_requested = 1,
                       locked_by = NULL, locked_at = NULL, heartbeat_at = NULL,
                       finished_at = ?, updated_at = ?
                   WHERE job_id = ?
                     AND status NOT IN ('RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')""",
                (now, now, job_id),
            )
        if cursor.rowcount != 1:
            try:
                self._conn.rollback()
            except Exception:
                pass
            return None
        self._conn.commit()
        return self.get_job(job_id)

    def try_complete_job(self, job_id: str, worker_id: str, result: dict, now: str) -> bool:
        cursor = self._conn.execute(
            """UPDATE jobs
               SET status = 'SUCCEEDED', result = ?, locked_by = NULL,
                   locked_at = NULL, heartbeat_at = NULL, finished_at = ?, updated_at = ?
               WHERE job_id = ?
                 AND status = 'RUNNING'
                 AND locked_by = ?
                 AND COALESCE(cancel_requested, 0) = 0""",
            (json.dumps(result), now, now, job_id, worker_id),
        )
        self._conn.commit()
        return cursor.rowcount == 1

    def try_fail_job(self, job_id: str, worker_id: str, error: str, now: str) -> bool:
        row = self._conn.execute(
            """SELECT retry_count, max_retries FROM jobs
               WHERE job_id = ? AND status = 'RUNNING' AND locked_by = ?
                 AND COALESCE(cancel_requested, 0) = 0""",
            (job_id, worker_id),
        ).fetchone()
        if row is None:
            return False
        retry_count = int(row["retry_count"] or 0) + 1
        max_retries = int(row["max_retries"] if row["max_retries"] is not None else 3)
        status = "FAILED" if retry_count >= max_retries else "RETRYING"
        finished_at = now if status == "FAILED" else None
        cursor = self._conn.execute(
            """UPDATE jobs
               SET status = ?, retry_count = ?, error = ?, locked_by = NULL,
                   locked_at = NULL, heartbeat_at = NULL, finished_at = ?, updated_at = ?
               WHERE job_id = ? AND status = 'RUNNING' AND locked_by = ?
                 AND COALESCE(cancel_requested, 0) = 0""",
            (status, retry_count, error, finished_at, now, job_id, worker_id),
        )
        self._conn.commit()
        return cursor.rowcount == 1

    def try_heartbeat_job(self, job_id: str, worker_id: str, now: str) -> bool:
        cursor = self._conn.execute(
            """UPDATE jobs SET heartbeat_at = ?, updated_at = ?
               WHERE job_id = ? AND status = 'RUNNING' AND locked_by = ?""",
            (now, now, job_id, worker_id),
        )
        self._conn.commit()
        return cursor.rowcount == 1

    def try_cancel_running_job(
        self,
        job_id: str,
        worker_id: str,
        reason: str | None,
        now: str,
    ) -> bool:
        cursor = self._conn.execute(
            """UPDATE jobs
               SET status = 'CANCELLED', cancel_requested = 1, error = COALESCE(?, error),
                   locked_by = NULL, locked_at = NULL, heartbeat_at = NULL,
                   finished_at = ?, updated_at = ?
               WHERE job_id = ? AND status = 'RUNNING' AND locked_by = ?""",
            (reason, now, now, job_id, worker_id),
        )
        self._conn.commit()
        return cursor.rowcount == 1


    def list_chat_records(self) -> list:
        rows = self._conn.execute("SELECT * FROM chat_records ORDER BY id DESC LIMIT 100").fetchall()
        return [dict(r) for r in rows]

    def add_chat_record(self, question: str, answer: str, citations: str) -> None:
        self._conn.execute(
            "INSERT INTO chat_records (question, answer, citations) VALUES (?, ?, ?)",
            (question, answer, citations),
        )
        self._conn.commit()

    def add_token_usage(self, usage: TokenUsage) -> None:
        self._conn.execute(
            """INSERT INTO token_usage (
                request_id, module, prompt_tokens, completion_tokens,
                total_tokens, estimated_cost
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                usage.request_id,
                usage.module,
                usage.prompt_tokens,
                usage.completion_tokens,
                usage.total_tokens,
                usage.estimated_cost,
            ),
        )
        self._conn.commit()

    def upsert_ticket(self, ticket: dict) -> None:
        self._conn.execute(
            """INSERT INTO tickets (
                ticket_id, idempotency_key, question, diagnosis, citations,
                device_model, fault_code, risk_level, status, required_parts,
                human_required, human_decision, human_reviewer,
                created_at, updated_at, closed_by, closed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
                question = excluded.question,
                diagnosis = excluded.diagnosis,
                citations = excluded.citations,
                device_model = excluded.device_model,
                fault_code = excluded.fault_code,
                risk_level = excluded.risk_level,
                status = excluded.status,
                required_parts = excluded.required_parts,
                human_required = excluded.human_required,
                human_decision = excluded.human_decision,
                human_reviewer = excluded.human_reviewer,
                updated_at = excluded.updated_at,
                closed_by = excluded.closed_by,
                closed_at = excluded.closed_at""",
            (
                ticket["ticket_id"],
                ticket["idempotency_key"],
                ticket["question"],
                ticket["diagnosis"],
                json.dumps(ticket["citations"], ensure_ascii=False),
                ticket.get("device_model"),
                ticket.get("fault_code"),
                ticket["risk_level"],
                ticket["status"],
                json.dumps(ticket["required_parts"], ensure_ascii=False),
                int(ticket["human_required"]),
                ticket.get("human_decision"),
                ticket.get("human_reviewer"),
                ticket["created_at"],
                ticket["updated_at"],
                ticket.get("closed_by"),
                ticket.get("closed_at"),
            ),
        )
        self._conn.commit()

    def get_ticket(self, ticket_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        return self._ticket_row_to_dict(row) if row else None

    def get_ticket_by_idempotency_key(self, idempotency_key: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM tickets WHERE idempotency_key = ?", (idempotency_key,)
        ).fetchone()
        return self._ticket_row_to_dict(row) if row else None

    def list_tickets(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM tickets ORDER BY created_at, ticket_id"
        ).fetchall()
        return [self._ticket_row_to_dict(row) for row in rows]

    @staticmethod
    def _ticket_row_to_dict(row: sqlite3.Row) -> dict:
        ticket = dict(row)
        ticket["citations"] = json.loads(ticket["citations"])
        ticket["required_parts"] = json.loads(ticket["required_parts"])
        ticket["human_required"] = bool(ticket["human_required"])
        return ticket

    def list_audit_events(self, limit: int = 100) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def record_audit_event(self, event: dict) -> None:
        self._conn.execute(
            "INSERT INTO audit_events (action, actor_role, resource_type, resource_id, summary, metadata, timestamp) VALUES (?,?,?,?,?,?,?)",
            (event.get("action"), event.get("actor_role"), event.get("resource_type"),
             event.get("resource_id"), event.get("summary"),
             json.dumps(event.get("metadata",{})), event.get("timestamp"))
        )
        self._conn.commit()

    def _row_to_job(self, row) -> dict:
        d = dict(row)
        d["payload"] = json.loads(d.get("payload", "{}"))
        d["result"] = json.loads(d.get("result", "{}"))
        d["cancel_requested"] = bool(d.get("cancel_requested", 0))
        return d

SQLiteStore = SqliteStore  # backward-compatible alias
