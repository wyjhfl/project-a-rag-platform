from __future__ import annotations

import json
from dataclasses import dataclass

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.rag.costing import TokenUsage


@dataclass(frozen=True)
class PostgresStoreConfig:
    database_url: str
    min_size: int = 1
    max_size: int = 5


class PostgresStore:
    def __init__(self, config: PostgresStoreConfig) -> None:
        if not config.database_url:
            raise ValueError("STORAGE_BACKEND=postgres requires DATABASE_URL.")
        self.pool = ConnectionPool(
            config.database_url,
            min_size=config.min_size,
            max_size=config.max_size,
            kwargs={"row_factory": dict_row},
        )
        self._init_schema()

    def _init_schema(self) -> None:
        with self.pool.connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    path TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_records (
                    id BIGSERIAL PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    citations JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
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
                    human_required BOOLEAN NOT NULL,
                    human_decision TEXT,
                    human_reviewer TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    closed_by TEXT,
                    closed_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS token_usage (
                    request_id TEXT PRIMARY KEY,
                    module TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    estimated_cost DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add_document(self, document_id: str, source: str, path: str, chunk_count: int) -> None:
        with self.pool.connection() as connection:
            connection.execute(
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

    def add_chat_record(self, question: str, answer: str, citations: str) -> None:
        with self.pool.connection() as connection:
            connection.execute(
                """
                INSERT INTO chat_records (question, answer, citations)
                VALUES (%s, %s, %s)
                """,
                (question, answer, Jsonb(json.loads(citations))),
            )

    def list_chat_records(self) -> list[dict]:
        with self.pool.connection() as connection:
            rows = connection.execute(
                """
                SELECT question, answer, citations, created_at
                FROM chat_records
                ORDER BY id
                """
            ).fetchall()
        return rows

    def add_token_usage(self, usage: TokenUsage) -> None:
        with self.pool.connection() as connection:
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
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (request_id) DO NOTHING
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
        with self.pool.connection() as connection:
            rows = connection.execute(
                """
                SELECT request_id, module, prompt_tokens, completion_tokens,
                       total_tokens, estimated_cost, created_at
                FROM token_usage
                ORDER BY created_at, request_id
                """
            ).fetchall()
        return rows

    def upsert_ticket(self, ticket: dict) -> None:
        with self.pool.connection() as connection:
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
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (ticket_id) DO UPDATE SET
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
                    bool(ticket["human_required"]),
                    ticket.get("human_decision"),
                    ticket.get("human_reviewer"),
                    ticket["created_at"],
                    ticket["updated_at"],
                    ticket.get("closed_by"),
                    ticket.get("closed_at"),
                ),
            )

    def get_ticket(self, ticket_id: str) -> dict | None:
        with self.pool.connection() as connection:
            row = connection.execute(
                "SELECT * FROM tickets WHERE ticket_id = %s",
                (ticket_id,),
            ).fetchone()
        return self._ticket_row_to_dict(row) if row else None

    def get_ticket_by_idempotency_key(self, idempotency_key: str) -> dict | None:
        with self.pool.connection() as connection:
            row = connection.execute(
                "SELECT * FROM tickets WHERE idempotency_key = %s",
                (idempotency_key,),
            ).fetchone()
        return self._ticket_row_to_dict(row) if row else None

    def list_tickets(self) -> list[dict]:
        with self.pool.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM tickets ORDER BY created_at, ticket_id"
            ).fetchall()
        return [self._ticket_row_to_dict(row) for row in rows]

    @staticmethod
    def _ticket_row_to_dict(row: dict) -> dict:
        ticket = dict(row)
        ticket["human_required"] = bool(ticket["human_required"])
        return ticket
