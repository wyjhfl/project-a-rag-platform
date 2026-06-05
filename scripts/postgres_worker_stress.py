"""PostgreSQL worker stress test for job operations.

Starts an ephemeral Docker PostgreSQL container (postgres:16-alpine) on port
5434, inserts N jobs, then spawns M worker threads that concurrently claim and
complete jobs using FOR UPDATE SKIP LOCKED.  Verifies no duplicate claims.

Usage:
    python scripts/postgres_worker_stress.py [--jobs N] [--workers M]

Defaults: --jobs 20 --workers 4
"""
from __future__ import annotations

import argparse
import atexit
import os
import subprocess
import sys
import threading
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
CONTAINER_NAME = "project-a-pg-stress"
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
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _insert_job(conn, job_id: str) -> None:
    now = _now()
    conn.execute(
        """INSERT INTO jobs
           (job_id, job_type, status, payload, result, error,
            retry_count, max_retries, locked_by, locked_at, heartbeat_at,
            timeout_seconds, cancel_requested, created_at, updated_at, started_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (job_id, "stress_test", "PENDING", "{}", "{}", None,
         0, 3, None, None, None, 300, 0, now, now, None),
    )


def _claim_job(conn, worker_id: str) -> str | None:
    """Claim the next PENDING job using FOR UPDATE SKIP LOCKED. Returns job_id or None."""
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
    return row[0] if row else None


def _complete_job(conn, job_id: str, worker_id: str, status: str = "SUCCEEDED", error: str | None = None) -> None:
    """Mark a claimed job as SUCCEEDED or FAILED."""
    now = _now()
    if status == "SUCCEEDED":
        conn.execute(
            """UPDATE jobs SET status = 'SUCCEEDED', result = %s, updated_at = %s
               WHERE job_id = %s AND locked_by = %s""",
            ('{"completed": true}', now, job_id, worker_id),
        )
    else:
        conn.execute(
            """UPDATE jobs SET status = 'FAILED', error = %s, updated_at = %s
               WHERE job_id = %s AND locked_by = %s""",
            (error or "unknown error", now, job_id, worker_id),
        )


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

def worker_thread(worker_id: str, results: dict, claimed_lock: threading.Lock) -> None:
    """Worker loop: claim jobs and complete them until no more PENDING jobs."""
    conn = psycopg.connect(DSN, autocommit=True)
    try:
        while True:
            job_id = _claim_job(conn, worker_id)
            if job_id is None:
                # No more PENDING jobs
                break
            with claimed_lock:
                if job_id in results["claimed_set"]:
                    results["duplicate_claims"] += 1
                else:
                    results["claimed_set"].add(job_id)
                    results["claimed_unique"] += 1

            # Simulate work
            time.sleep(0.01)

            # Complete the job (90% succeed, 10% fail)
            import random
            if random.random() < 0.9:
                _complete_job(conn, job_id, worker_id, "SUCCEEDED")
                results["succeeded"] += 1
            else:
                _complete_job(conn, job_id, worker_id, "FAILED", "simulated failure")
                results["failed"] += 1
    except Exception as exc:
        results["errors"].append(f"{worker_id}: {exc}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="PostgreSQL worker stress test")
    parser.add_argument("--jobs", type=int, default=20, help="Number of jobs to insert (default: 20)")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker threads (default: 4)")
    args = parser.parse_args()

    num_jobs = args.jobs
    num_workers = args.workers

    print(f"PostgreSQL Worker Stress Test  jobs={num_jobs} workers={num_workers}")

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

    # 4. Setup: create table and insert jobs
    conn = psycopg.connect(DSN, autocommit=True)
    try:
        conn.execute("DROP TABLE IF EXISTS jobs")
        conn.execute(JOBS_TABLE_DDL)

        job_ids = [f"JOB-STRESS-{uuid.uuid4().hex[:8]}" for _ in range(num_jobs)]
        for jid in job_ids:
            _insert_job(conn, jid)
        print(f"Inserted {num_jobs} jobs")
    finally:
        conn.close()

    # 5. Spawn worker threads
    results: dict = {
        "claimed_unique": 0,
        "duplicate_claims": 0,
        "succeeded": 0,
        "failed": 0,
        "cancelled": 0,
        "claimed_set": set(),
        "errors": [],
    }
    claimed_lock = threading.Lock()

    threads: list[threading.Thread] = []
    start_time = time.monotonic()

    for i in range(num_workers):
        wid = f"worker-{i}"
        t = threading.Thread(target=worker_thread, args=(wid, results, claimed_lock))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=120)

    elapsed = time.monotonic() - start_time

    # 6. Verify: check for duplicate claims in the database
    conn = psycopg.connect(DSN, autocommit=True)
    try:
        # Check that no job was claimed by more than one worker
        rows = conn.execute(
            "SELECT job_id, locked_by FROM jobs WHERE status IN ('SUCCEEDED', 'FAILED', 'CANCELLED')"
        ).fetchall()
        db_claimed = {}
        for row in rows:
            jid, locked_by = row
            if jid in db_claimed and db_claimed[jid] != locked_by:
                results["duplicate_claims"] += 1
            db_claimed[jid] = locked_by

        # Count remaining PENDING jobs (cancelled)
        pending = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'PENDING'").fetchone()[0]
        results["cancelled"] = pending
    finally:
        conn.close()

    # 7. Summary
    print()
    print("=" * 50)
    print("STRESS TEST SUMMARY")
    print("=" * 50)
    print(f"  claimed_unique  : {results['claimed_unique']}")
    print(f"  duplicate_claims: {results['duplicate_claims']}")
    print(f"  succeeded       : {results['succeeded']}")
    print(f"  failed          : {results['failed']}")
    print(f"  cancelled       : {results['cancelled']}")
    print(f"  errors          : {len(results['errors'])}")
    print(f"  elapsed         : {elapsed:.2f}s")
    if results["errors"]:
        for err in results["errors"]:
            print(f"  ERROR: {err}")
    print("=" * 50)

    if results["duplicate_claims"] > 0:
        print("FAILED: duplicate claims detected")
        sys.exit(1)
    if results["claimed_unique"] != num_jobs:
        print(f"FAILED: claimed {results['claimed_unique']} of {num_jobs} jobs")
        sys.exit(1)
    if results["errors"]:
        print("FAILED: worker errors occurred")
        sys.exit(1)

    print("PASSED: no duplicate claims, all jobs processed")
    sys.exit(0)


if __name__ == "__main__":
    main()
