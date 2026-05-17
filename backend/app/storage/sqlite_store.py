import json
import sqlite3
from pathlib import Path

from app.rag.costing import TokenUsage


class SQLiteStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    path TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                """
            )

    def add_document(self, document_id: str, source: str, path: str, chunk_count: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO documents (id, source, path, chunk_count)
                VALUES (?, ?, ?, ?)
                """,
                (document_id, source, path, chunk_count),
            )

    def add_chat_record(self, question: str, answer: str, citations: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_records (question, answer, citations)
                VALUES (?, ?, ?)
                """,
                (question, answer, citations),
            )

    def list_chat_records(self) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return list(
                connection.execute(
                    "SELECT question, answer, citations, created_at FROM chat_records ORDER BY id"
                )
            )

    def add_token_usage(self, usage: TokenUsage) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO token_usage (
                    request_id,
                    module,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost
                )
                VALUES (?, ?, ?, ?, ?, ?)
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

    def list_token_usage(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT request_id, module, prompt_tokens, completion_tokens,
                       total_tokens, estimated_cost, created_at
                FROM token_usage
                ORDER BY created_at, request_id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_ticket(self, ticket: dict) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tickets (
                    ticket_id,
                    idempotency_key,
                    question,
                    diagnosis,
                    citations,
                    device_model,
                    fault_code,
                    risk_level,
                    status,
                    required_parts,
                    human_required,
                    human_decision,
                    human_reviewer,
                    created_at,
                    updated_at,
                    closed_by,
                    closed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    closed_at = excluded.closed_at
                """,
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

    def get_ticket(self, ticket_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tickets WHERE ticket_id = ?",
                (ticket_id,),
            ).fetchone()
        return self._ticket_row_to_dict(row) if row else None

    def get_ticket_by_idempotency_key(self, idempotency_key: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tickets WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        return self._ticket_row_to_dict(row) if row else None

    def list_tickets(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
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
