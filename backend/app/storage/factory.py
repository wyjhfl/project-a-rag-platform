from pathlib import Path

from app.config import Settings
from app.storage.base import Store
from app.storage.sqlite_store import SQLiteStore


def build_store(settings: Settings, database_path: Path | None = None) -> Store:
    if database_path is not None:
        return SQLiteStore(database_path)

    backend = settings.storage_backend.strip().lower()
    if backend == "sqlite":
        return SQLiteStore(settings.database_path)
    if backend == "postgres":
        from app.storage.postgres_store import PostgresStore, PostgresStoreConfig

        return PostgresStore(PostgresStoreConfig(database_url=settings.database_url))
    raise ValueError("STORAGE_BACKEND must be either 'sqlite' or 'postgres'.")
