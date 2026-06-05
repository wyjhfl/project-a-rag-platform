"""Storage factory for Project A RAG Platform."""
from __future__ import annotations

from pathlib import Path

from app.storage.sqlite_store import SqliteStore


def build_store(settings, database_path=None):
    db_path = Path(database_path) if database_path else settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteStore(db_path)
