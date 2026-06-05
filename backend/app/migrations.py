"""Database migrations for Project A RAG Platform."""
from __future__ import annotations

from typing import Callable


class Migration:
    """A single database migration with a version identifier and upgrade function."""

    def __init__(self, version: str, func: Callable, description: str = "") -> None:
        self.version = version
        self.func = func
        self.description = description

    def __repr__(self) -> str:
        return f"Migration(version={self.version!r}, description={self.description!r})"


MIGRATIONS: list[Migration] = []


def register_migration(version: str, func: Callable, description: str = "") -> None:
    """Register a migration function for a given version."""
    MIGRATIONS.append(Migration(version, func, description))
    MIGRATIONS.sort(key=lambda m: m.version)


def get_migration_versions() -> list[str]:
    """Return sorted list of migration version strings."""
    return [m.version for m in MIGRATIONS]


# --- Built-in migrations ---


def _migrate_2026_05_31_jobs_v1(connection=None) -> None:
    """Add jobs table for background job processing."""
    if connection is not None:
        connection.executescript("""
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
        """)


def _migrate_2026_06_02_jobs_v2(connection=None) -> None:
    """Add finished_at column and audit events table."""
    if connection is not None:
        try:
            connection.execute(
                "ALTER TABLE jobs ADD COLUMN finished_at TEXT"
            )
        except Exception:
            pass  # Column may already exist
        connection.executescript("""
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
        """)


# Register built-in migrations
register_migration("2026-05-31-jobs-v1", _migrate_2026_05_31_jobs_v1, "Add jobs table")
register_migration("2026-06-02-jobs-v2", _migrate_2026_06_02_jobs_v2, "Add finished_at and audit_events")
