"""Storage factory for Project A RAG Platform."""
from __future__ import annotations

from pathlib import Path

from app.storage.postgres_store import PostgresStore
from app.storage.sqlite_store import SqliteStore


def build_store(settings, database_path=None):
    backend = settings.storage_backend.strip().lower()
    if backend == "postgres":
        return PostgresStore(settings.database_url)
    if backend != "sqlite":
        raise ValueError("STORAGE_BACKEND must be either 'sqlite' or 'postgres'.")
    db_path = Path(database_path) if database_path else settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteStore(db_path)
