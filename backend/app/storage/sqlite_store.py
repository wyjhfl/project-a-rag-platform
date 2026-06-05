"""SQLite storage backend for Project A RAG Platform."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

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
                started_at TEXT
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
                question TEXT,
                answer TEXT,
                created_at TEXT
            );
        """)
        conn.commit()

    def create_job(self, job: dict) -> None:
        if "job_id" not in job:
            job["job_id"] = f"JOB-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        job.setdefault("created_at", now)
        job.setdefault("updated_at", now)
        self._conn.execute(
            "INSERT OR REPLACE INTO jobs (job_id, job_type, status, payload, result, error, retry_count, max_retries, locked_by, locked_at, heartbeat_at, timeout_seconds, cancel_requested, created_at, updated_at, started_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (job.get("job_id"), job.get("job_type",""), job.get("status","PENDING"),
             json.dumps(job.get("payload",{})), json.dumps(job.get("result",{})),
             job.get("error"), job.get("retry_count",0), job.get("max_retries",3),
             job.get("locked_by"), job.get("locked_at"), job.get("heartbeat_at"),
             job.get("timeout_seconds",300), 1 if job.get("cancel_requested") else 0,
             job.get("created_at",now), job.get("updated_at",now), job.get("started_at"))
        )
        self._conn.commit()

    def get_job(self, job_id: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def update_job(self, job: dict) -> None:
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
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
            "SELECT job_id FROM jobs WHERE status = 'PENDING' ORDER BY created_at ASC LIMIT 1"
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
               WHERE job_id = ? AND status = 'PENDING'""",
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

    def list_chat_records(self) -> list:
        rows = self._conn.execute("SELECT * FROM chat_records ORDER BY id DESC LIMIT 100").fetchall()
        return [dict(r) for r in rows]

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
