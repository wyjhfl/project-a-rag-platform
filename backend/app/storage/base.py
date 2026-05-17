from typing import Protocol

from app.rag.costing import TokenUsage


class Store(Protocol):
    def add_document(self, document_id: str, source: str, path: str, chunk_count: int) -> None:
        pass

    def add_chat_record(self, question: str, answer: str, citations: str) -> None:
        pass

    def list_chat_records(self) -> list:
        pass

    def add_token_usage(self, usage: TokenUsage) -> None:
        pass

    def list_token_usage(self) -> list[dict]:
        pass

    def upsert_ticket(self, ticket: dict) -> None:
        pass

    def get_ticket(self, ticket_id: str) -> dict | None:
        pass

    def get_ticket_by_idempotency_key(self, idempotency_key: str) -> dict | None:
        pass

    def list_tickets(self) -> list[dict]:
        pass
