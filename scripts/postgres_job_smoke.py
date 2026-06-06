"""PostgreSQL smoke test for the real Project A PostgresStore.

Starts an ephemeral Docker PostgreSQL container (postgres:16-alpine), initializes
PostgresStore, and exercises the actual Store + JobService paths used by the
production API and worker.
"""
from __future__ import annotations

import atexit
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, ".pg_deps"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg Python package is not installed. pip install 'psycopg[binary,pool]'")
    sys.exit(1)

from app.jobs import JobService  # noqa: E402
from app.rag.costing import TokenUsage  # noqa: E402
from app.storage.postgres_store import PostgresStore  # noqa: E402

CONTAINER_NAME = "project-a-pg-smoke"
PG_IMAGE = "postgres:16-alpine"
PG_PORT = int(os.environ.get("PG_SMOKE_PORT", "5434"))
PG_PASSWORD = os.environ.get("PG_SMOKE_PASSWORD", "smoke_test_pw_placeholder")
PG_DATABASE = "project_a_smoke"
PG_USER = "postgres"
DSN = f"postgresql://{PG_USER}:{PG_PASSWORD}@localhost:{PG_PORT}/{PG_DATABASE}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, text=True, capture_output=True, **kwargs)


def _docker_available() -> bool:
    try:
        return _run(["docker", "--version"], timeout=10).returncode == 0
    except FileNotFoundError:
        return False


def _container_exists() -> bool:
    result = _run(["docker", "ps", "-aq", "-f", f"name=^{CONTAINER_NAME}$"])
    return bool(result.stdout.strip())


def _container_running() -> bool:
    result = _run(["docker", "ps", "-q", "-f", f"name=^{CONTAINER_NAME}$"])
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
    for _attempt in range(60):
        try:
            with psycopg.connect(DSN, autocommit=True) as conn:
                conn.execute("SELECT 1")
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("PostgreSQL container failed to become ready")


def remove_container() -> None:
    _run(["docker", "rm", "-f", CONTAINER_NAME])


def reset_schema() -> None:
    with psycopg.connect(DSN, autocommit=True) as conn:
        for table in [
            "token_usage",
            "tickets",
            "chat_records",
            "audit_events",
            "documents",
            "jobs",
            "schema_migrations",
        ]:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


def test_create_and_get_job(store: PostgresStore) -> bool:
    store.create_job({
        "job_id": "JOB-PG-001",
        "job_type": "document.ingest",
        "status": "SUCCEEDED",
        "payload": {"docs_source": "seed_docs"},
        "created_at": _now(),
        "updated_at": _now(),
    })
    job = store.get_job("JOB-PG-001")
    return bool(job and job["payload"]["docs_source"] == "seed_docs")


def test_claim_and_complete(store: PostgresStore) -> bool:
    service = JobService(store, execution_mode="worker")
    service.create_job("document.ingest", payload={"docs_source": "seed_docs"}, max_retries=1)
    claimed = service.claim_next_job("worker-1")
    if not claimed or claimed["status"] != "RUNNING" or claimed["locked_by"] != "worker-1":
        return False
    if service.claim_next_job("worker-2") is not None:
        return False
    if not service.complete_job(claimed["job_id"], "worker-1", {"document_count": 1}):
        return False
    final = service.get_job(claimed["job_id"])
    return bool(final and final["status"] == "SUCCEEDED" and final["finished_at"])


def test_cancel_pending(store: PostgresStore) -> bool:
    service = JobService(store, execution_mode="worker")
    record = service.create_job("document.ingest", payload={})
    result = service.cancel_job(record.job_id)
    final = service.get_job(record.job_id)
    return bool(result and final and final["status"] == "CANCELLED" and final["finished_at"])


def test_cancel_running(store: PostgresStore) -> bool:
    service = JobService(store, execution_mode="worker")
    record = service.create_job("document.ingest", payload={})
    claimed = service.claim_next_job("worker-1")
    if not claimed:
        return False
    if not service.cancel_running_job(record.job_id, "worker-1", "cancel smoke"):
        return False
    final = service.get_job(record.job_id)
    return bool(final and final["status"] == "CANCELLED" and final["locked_by"] is None)


def test_retry_to_failed(store: PostgresStore) -> bool:
    service = JobService(store, execution_mode="worker")
    record = service.create_job("unknown.type", payload={}, max_retries=1)
    claimed = service.claim_next_job("worker-1")
    if not claimed:
        return False
    service.fail_job(record.job_id, "worker-1", "unknown type")
    final = service.get_job(record.job_id)
    return bool(final and final["status"] == "FAILED" and final["error"] == "unknown type")


def test_documents(store: PostgresStore) -> bool:
    store.add_document("doc-1", "seed_docs", "/tmp/doc.txt", 3)
    store.add_document("doc-1", "seed_docs", "/tmp/doc.txt", 4)
    return True


def test_chat_and_token_usage(store: PostgresStore) -> bool:
    store.add_chat_record("q", "a", "[]")
    usage = TokenUsage(
        request_id="req-pg-smoke",
        module="chat",
        prompt_tokens=1,
        completion_tokens=2,
        total_tokens=3,
        estimated_cost=0.001,
    )
    store.add_token_usage(usage)
    return bool(store.list_chat_records())


def test_tickets(store: PostgresStore) -> bool:
    ticket = {
        "ticket_id": "TCK-PG-001",
        "idempotency_key": "idem-pg-001",
        "question": "question",
        "diagnosis": "diagnosis",
        "citations": [],
        "device_model": "M1",
        "fault_code": "F1",
        "risk_level": "low",
        "status": "OPEN",
        "required_parts": [],
        "human_required": False,
        "human_decision": None,
        "human_reviewer": None,
        "created_at": _now(),
        "updated_at": _now(),
        "closed_by": None,
        "closed_at": None,
    }
    store.upsert_ticket(ticket)
    by_id = store.get_ticket("TCK-PG-001")
    by_key = store.get_ticket_by_idempotency_key("idem-pg-001")
    return bool(by_id and by_key and store.list_tickets())


def test_audit(store: PostgresStore) -> bool:
    store.record_audit_event({
        "action": "smoke.event",
        "actor_role": "admin",
        "resource_type": "smoke",
        "resource_id": "pg",
        "summary": "postgres smoke",
        "metadata": {"ok": True},
        "timestamp": _now(),
    })
    events = store.list_audit_events(limit=10)
    return bool(events and events[0]["metadata"]["ok"] is True)


def main() -> None:
    if not _docker_available():
        print("ERROR: Docker is not available. Install Docker and try again.")
        sys.exit(1)

    try:
        start_postgres()
    except Exception as exc:
        print(f"ERROR: Failed to start PostgreSQL container: {exc}")
        sys.exit(1)
    atexit.register(remove_container)

    try:
        reset_schema()
        store = PostgresStore(DSN)
    except Exception as exc:
        print(f"ERROR: Failed to initialize PostgresStore: {exc}")
        sys.exit(1)

    tests = [
        ("create_and_get_job", lambda: test_create_and_get_job(store)),
        ("claim_and_complete", lambda: test_claim_and_complete(store)),
        ("cancel_pending", lambda: test_cancel_pending(store)),
        ("cancel_running", lambda: test_cancel_running(store)),
        ("retry_to_failed", lambda: test_retry_to_failed(store)),
        ("documents", lambda: test_documents(store)),
        ("chat_and_token_usage", lambda: test_chat_and_token_usage(store)),
        ("tickets", lambda: test_tickets(store)),
        ("audit", lambda: test_audit(store)),
    ]

    results: dict[str, bool] = {}
    for name, fn in tests:
        try:
            ok = bool(fn())
        except Exception:
            ok = False
        results[name] = ok
        print(f"{name}: {'PASSED' if ok else 'FAILED'}")

    passed = sum(1 for ok in results.values() if ok)
    total = len(results)
    print()
    print(f"{passed}/{total} PASSED" if passed == total else f"{passed}/{total} FAILED")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
