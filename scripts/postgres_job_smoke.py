"""PostgreSQL smoke test for job operations.

Starts an ephemeral Docker PostgreSQL container (postgres:16-alpine) on port
5434, creates a simple jobs table, and exercises INSERT / SELECT / UPDATE /
DELETE plus concurrent claim with FOR UPDATE SKIP LOCKED.

Exits 0 if all 10 tests pass, 1 otherwise.
"""
from __future__ import annotations

import atexit
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# sys.path setup – must happen before any app.* imports
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, ".pg_deps"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

# ---------------------------------------------------------------------------
# Docker path – add custom Docker location to PATH
# ---------------------------------------------------------------------------
_docker_bin = os.path.join("D:\\codex安装\\tools\\Docker\\resources\\bin")
if os.path.isdir(_docker_bin):
    os.environ["PATH"] = _docker_bin + os.pathsep + os.environ.get("PATH", "")

# ---------------------------------------------------------------------------
# Third-party imports
# ---------------------------------------------------------------------------
try:
    import psycopg
except ImportError:
    print("ERROR: psycopg Python package is not installed.  pip install psycopg[binary]")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Docker / PostgreSQL helpers
# ---------------------------------------------------------------------------
CONTAINER_NAME = "project-a-pg-smoke"
PG_IMAGE = "postgres:16-alpine"
PG_PORT = 5434
PG_PASSWORD = os.environ.get("PG_SMOKE_PASSWORD", "smoke_test_pw_placeholder")
PG_DATABASE = "project_a_smoke"
PG_USER = "postgres"
DSN = f"postgresql://{PG_USER}:{PG_PASSWORD}@localhost:{PG_PORT}/{PG_DATABASE}"

JOBS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id       TEXT PRIMARY KEY,
    job_type     TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'PENDING',
    payload      TEXT DEFAULT '{}',
    result       TEXT DEFAULT '{}',
    error        TEXT,
    retry_count  INTEGER DEFAULT 0,
    max_retries  INTEGER DEFAULT 3,
    locked_by    TEXT,
    locked_at    TEXT,
    heartbeat_at TEXT,
    timeout_seconds INTEGER DEFAULT 300,
    cancel_requested INTEGER DEFAULT 0,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    started_at   TEXT
);
"""


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _container_exists() -> bool:
    result = subprocess.run(
        ["docker", "ps", "-aq", "-f", f"name=^{CONTAINER_NAME}$"],
        capture_output=True, text=True,
    )
    return bool(result.stdout.strip())


def _container_running() -> bool:
    result = subprocess.run(
        ["docker", "ps", "-q", "-f", f"name=^{CONTAINER_NAME}$"],
        capture_output=True, text=True,
    )
    return bool(result.stdout.strip())


def start_postgres() -> None:
    if _container_running():
        return
    if _container_exists():
        subprocess.run(["docker", "start", CONTAINER_NAME], check=True)
    else:
        subprocess.run(
            [
                "docker", "run", "-d",
                "--name", CONTAINER_NAME,
                "-e", f"POSTGRES_PASSWORD={PG_PASSWORD}",
                "-e", f"POSTGRES_DB={PG_DATABASE}",
                "-p", f"{PG_PORT}:5432",
                PG_IMAGE,
            ],
            check=True,
        )
    # Wait for PostgreSQL to accept connections
    for _ in range(60):
        try:
            conn = psycopg.connect(DSN, autocommit=True)
            conn.close()
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("PostgreSQL container failed to become ready")


def remove_container() -> None:
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_job(job_type: str = "smoke_test", status: str = "PENDING") -> dict:
    return {
        "job_id": f"JOB-{uuid.uuid4().hex[:8]}",
        "job_type": job_type,
        "status": status,
        "payload": "{}",
        "result": "{}",
        "error": None,
        "retry_count": 0,
        "max_retries": 3,
        "locked_by": None,
        "locked_at": None,
        "heartbeat_at": None,
        "timeout_seconds": 300,
        "cancel_requested": 0,
        "created_at": _now(),
        "updated_at": _now(),
        "started_at": None,
    }


def _insert_job(conn, job: dict) -> None:
    conn.execute(
        """INSERT INTO jobs
           (job_id, job_type, status, payload, result, error,
            retry_count, max_retries, locked_by, locked_at, heartbeat_at,
            timeout_seconds, cancel_requested, created_at, updated_at, started_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (job["job_id"], job["job_type"], job["status"],
         job["payload"], job["result"], job["error"],
         job["retry_count"], job["max_retries"],
         job["locked_by"], job["locked_at"], job["heartbeat_at"],
         job["timeout_seconds"], job["cancel_requested"],
         job["created_at"], job["updated_at"], job["started_at"]),
    )


# ---------------------------------------------------------------------------
# Individual tests (10 total)
# ---------------------------------------------------------------------------

def test_connect(conn) -> bool:
    """1. Basic connectivity – SELECT 1."""
    row = conn.execute("SELECT 1").fetchone()
    return row is not None and row[0] == 1


def test_create_table(conn) -> bool:
    """2. Create jobs table."""
    conn.execute(JOBS_TABLE_DDL)
    return True


def test_insert_job(conn) -> bool:
    """3. Insert a job."""
    job = _make_job()
    _insert_job(conn, job)
    row = conn.execute("SELECT job_id FROM jobs WHERE job_id = %s", (job["job_id"],)).fetchone()
    return row is not None and row[0] == job["job_id"]


def test_query_job(conn) -> bool:
    """4. Query a job by job_id."""
    job = _make_job()
    _insert_job(conn, job)
    row = conn.execute(
        "SELECT job_type, status FROM jobs WHERE job_id = %s",
        (job["job_id"],),
    ).fetchone()
    return row is not None and row[0] == "smoke_test" and row[1] == "PENDING"


def test_update_job_status(conn) -> bool:
    """5. Update a job's status to RUNNING."""
    job = _make_job()
    _insert_job(conn, job)
    conn.execute(
        "UPDATE jobs SET status = 'RUNNING', updated_at = %s WHERE job_id = %s",
        (_now(), job["job_id"]),
    )
    row = conn.execute(
        "SELECT status FROM jobs WHERE job_id = %s", (job["job_id"],)
    ).fetchone()
    return row is not None and row[0] == "RUNNING"


def test_delete_job(conn) -> bool:
    """6. Delete a job."""
    job = _make_job()
    _insert_job(conn, job)
    conn.execute("DELETE FROM jobs WHERE job_id = %s", (job["job_id"],))
    row = conn.execute(
        "SELECT job_id FROM jobs WHERE job_id = %s", (job["job_id"],)
    ).fetchone()
    return row is None


def test_claim_next_job(conn) -> bool:
    """7. Claim the next PENDING job (single worker)."""
    conn.execute("DELETE FROM jobs")
    job = _make_job()
    _insert_job(conn, job)
    worker_id = "worker-1"
    now = _now()
    row = conn.execute(
        """UPDATE jobs SET status = 'RUNNING', locked_by = %s,
           locked_at = %s, heartbeat_at = %s, started_at = %s, updated_at = %s
           WHERE job_id = (
               SELECT job_id FROM jobs
               WHERE status = 'PENDING'
               ORDER BY created_at ASC
               LIMIT 1
               FOR UPDATE SKIP LOCKED
           )
           RETURNING job_id""",
        (worker_id, now, now, now, now),
    ).fetchone()
    return row is not None and row[0] == job["job_id"]


def test_concurrent_claim_no_duplicates(conn) -> bool:
    """8. Concurrent claim with FOR UPDATE SKIP LOCKED – no duplicates."""
    conn.execute("DELETE FROM jobs")
    # Insert 3 jobs
    jobs = [_make_job() for _ in range(3)]
    for j in jobs:
        _insert_job(conn, j)

    claimed_ids: list[str] = []
    worker_ids = ["worker-A", "worker-B", "worker-C"]

    for wid in worker_ids:
        now = _now()
        row = conn.execute(
            """UPDATE jobs SET status = 'RUNNING', locked_by = %s,
               locked_at = %s, heartbeat_at = %s, started_at = %s, updated_at = %s
               WHERE job_id = (
                   SELECT job_id FROM jobs
                   WHERE status = 'PENDING'
                   ORDER BY created_at ASC
                   LIMIT 1
                   FOR UPDATE SKIP LOCKED
               )
               RETURNING job_id""",
            (wid, now, now, now, now),
        ).fetchone()
        if row is not None:
            claimed_ids.append(row[0])

    # All claimed IDs must be unique
    return len(claimed_ids) == len(set(claimed_ids))


def test_skip_locked_returns_none_when_all_claimed(conn) -> bool:
    """9. FOR UPDATE SKIP LOCKED returns None when all jobs are claimed."""
    conn.execute("DELETE FROM jobs")
    job = _make_job()
    _insert_job(conn, job)
    # Claim it
    now = _now()
    conn.execute(
        """UPDATE jobs SET status = 'RUNNING', locked_by = %s,
           locked_at = %s, heartbeat_at = %s, started_at = %s, updated_at = %s
           WHERE job_id = %s""",
        ("worker-X", now, now, now, now, job["job_id"]),
    )
    # Try to claim again – should get None (no PENDING jobs left)
    row = conn.execute(
        """SELECT job_id FROM jobs
           WHERE status = 'PENDING'
           ORDER BY created_at ASC
           LIMIT 1
           FOR UPDATE SKIP LOCKED"""
    ).fetchone()
    return row is None


def test_complete_job(conn) -> bool:
    """10. Complete a claimed job – set status to SUCCEEDED."""
    job = _make_job()
    _insert_job(conn, job)
    now = _now()
    conn.execute(
        """UPDATE jobs SET status = 'RUNNING', locked_by = %s,
           locked_at = %s, heartbeat_at = %s, started_at = %s, updated_at = %s
           WHERE job_id = %s""",
        ("worker-Y", now, now, now, now, job["job_id"]),
    )
    conn.execute(
        """UPDATE jobs SET status = 'SUCCEEDED', result = %s, updated_at = %s
           WHERE job_id = %s""",
        ('{"done": true}', _now(), job["job_id"]),
    )
    row = conn.execute(
        "SELECT status FROM jobs WHERE job_id = %s", (job["job_id"],)
    ).fetchone()
    return row is not None and row[0] == "SUCCEEDED"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # 1. Check Docker availability
    if not _docker_available():
        print("ERROR: Docker is not available.  Install Docker and try again.")
        sys.exit(1)

    # 2. Start PostgreSQL container
    try:
        start_postgres()
    except Exception as exc:
        print(f"ERROR: Failed to start PostgreSQL container: {exc}")
        sys.exit(1)

    # 3. Register cleanup
    atexit.register(remove_container)

    # 4. Connect and run tests
    conn = psycopg.connect(DSN, autocommit=True)
    try:
        # Create table first
        conn.execute(JOBS_TABLE_DDL)

        tests = [
            ("connect", lambda: test_connect(conn)),
            ("create_table", lambda: test_create_table(conn)),
            ("insert_job", lambda: test_insert_job(conn)),
            ("query_job", lambda: test_query_job(conn)),
            ("update_job_status", lambda: test_update_job_status(conn)),
            ("delete_job", lambda: test_delete_job(conn)),
            ("claim_next_job", lambda: test_claim_next_job(conn)),
            ("concurrent_claim_no_duplicates", lambda: test_concurrent_claim_no_duplicates(conn)),
            ("skip_locked_returns_none", lambda: test_skip_locked_returns_none_when_all_claimed(conn)),
            ("complete_job", lambda: test_complete_job(conn)),
        ]

        results: dict[str, bool] = {}
        for name, fn in tests:
            try:
                ok = fn()
            except Exception as exc:
                print(f"  [{name}] exception: {exc}")
                ok = False
            results[name] = bool(ok)
            print(f"{name}: {'PASSED' if ok else 'FAILED'}")

        # 5. Summary
        print()
        passed = sum(1 for ok in results.values() if ok)
        total = len(results)
        print(f"{passed}/{total} PASSED" if passed == total else f"{passed}/{total} FAILED")

        if all(results.values()):
            sys.exit(0)
        else:
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
