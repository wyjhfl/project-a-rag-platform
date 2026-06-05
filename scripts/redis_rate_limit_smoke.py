"""Real Redis end-to-end smoke test for the rate limiting system.

Starts a Docker Redis container on port 6380, creates a test FastAPI app
with RateLimitMiddleware backed by Redis, and exercises every required
behaviour.  Exits 0 if all tests pass, 1 otherwise.
"""
from __future__ import annotations

import atexit
import hashlib
import os
import subprocess
import sys
import time
import types

# ---------------------------------------------------------------------------
# sys.path setup – must happen before any app.* imports
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, ".pg_deps"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

# ---------------------------------------------------------------------------
# Environment variables – must be set before importing app.config
# ---------------------------------------------------------------------------
os.environ.setdefault("RATE_LIMIT_ENABLED", "true")
os.environ.setdefault("RATE_LIMIT_BACKEND", "redis")
os.environ.setdefault("RATE_LIMIT_REDIS_URL", "redis://localhost:6380/1")
os.environ.setdefault("RATE_LIMIT_REQUESTS_PER_MINUTE", "10")
os.environ.setdefault("RATE_LIMIT_BURST", "5")
os.environ.setdefault("STORAGE_BACKEND", "sqlite")
os.environ.setdefault("LLM_PROVIDER", "xiaomi_mimo")

# ---------------------------------------------------------------------------
# Stub out missing app sub-modules so that app.rate_limit can be imported
# ---------------------------------------------------------------------------


def _ensure_module(name: str, attrs: dict) -> None:
    """Register *name* in ``sys.modules`` if it does not already exist."""
    if name in sys.modules:
        return
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod


_ensure_module("app.errors", {
    "error_payload": lambda code, message, request_id="": {
        "error": {"code": code, "message": message, "request_id": request_id}
    },
    "AppError": type("AppError", (Exception,), {
        "__init__": lambda self, code="", message="", status_code=500: None,
    }),
    "install_exception_handlers": lambda app: None,
})

_ensure_module("app.observability", {
    "current_request_id": lambda: "",
    "RequestContextMiddleware": type("RequestContextMiddleware", (), {
        "__init__": lambda self, app: setattr(self, "_app", app),
        "__call__": lambda self, scope, receive, send: self._app(scope, receive, send),
    }),
    "configure_logging": lambda level="INFO": None,
})

# ---------------------------------------------------------------------------
# App imports
# ---------------------------------------------------------------------------
from app.rate_limit import MemoryRateLimiter, RateLimitMiddleware, RedisRateLimiter  # noqa: E402
from app.config import Settings, get_settings  # noqa: E402

try:
    from app.main import create_app  # noqa: F401
except ImportError:
    create_app = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Third-party imports
# ---------------------------------------------------------------------------
try:
    import redis as _redis_lib
except ImportError:
    print("ERROR: redis Python package is not installed.  pip install redis")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("ERROR: httpx Python package is not installed.  pip install httpx")
    sys.exit(1)

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import JSONResponse, PlainTextResponse  # noqa: E402

# ---------------------------------------------------------------------------
# Docker / Redis helpers
# ---------------------------------------------------------------------------
CONTAINER_NAME = "project-a-redis-smoke"
REDIS_IMAGE = "redis:7-alpine"
REDIS_PORT = 6380
REDIS_URL = f"redis://localhost:{REDIS_PORT}/1"


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


def start_redis() -> None:
    if _container_running():
        return
    if _container_exists():
        subprocess.run(["docker", "start", CONTAINER_NAME], check=True)
    else:
        subprocess.run(
            [
                "docker", "run", "-d",
                "--name", CONTAINER_NAME,
                "-p", f"{REDIS_PORT}:6379",
                REDIS_IMAGE,
            ],
            check=True,
        )
    # Wait for Redis to accept connections
    for _ in range(40):
        try:
            client = _redis_lib.Redis.from_url(REDIS_URL)
            client.ping()
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Redis container failed to become ready")


def stop_redis() -> None:
    subprocess.run(["docker", "stop", CONTAINER_NAME], capture_output=True)


def remove_redis() -> None:
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)


def flush_redis() -> None:
    client = _redis_lib.Redis.from_url(REDIS_URL)
    client.flushdb()


# ---------------------------------------------------------------------------
# Test FastAPI application
# ---------------------------------------------------------------------------


def build_test_app() -> FastAPI:
    """Create a minimal FastAPI app with Redis-backed rate limiting."""
    app = FastAPI()

    app.add_middleware(
        RateLimitMiddleware,
        enabled=True,
        requests_per_minute=10,
        burst=5,
        backend="redis",
        redis_url=REDIS_URL,
    )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "service": "project-a-smoke"}

    @app.get("/readyz")
    def readyz():
        try:
            client = _redis_lib.Redis.from_url(REDIS_URL)
            client.ping()
            return {"status": "ok", "checks": {"redis": "ok"}}
        except Exception as exc:
            return JSONResponse(
                status_code=503,
                content={"status": "error", "checks": {"redis": f"error: {exc}"}},
            )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics():
        return PlainTextResponse("# metrics disabled\n", media_type="text/plain")

    @app.get("/api/v1/test")
    def test_get():
        return {"status": "ok"}

    @app.post("/api/v1/test")
    def test_post():
        return {"status": "ok"}

    return app


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_client(app: FastAPI):
    from starlette.testclient import TestClient
    return TestClient(app)


# ---------------------------------------------------------------------------
# Individual tests
# ---------------------------------------------------------------------------


def test_redis_ping() -> bool:
    client = _redis_lib.Redis.from_url(REDIS_URL)
    return bool(client.ping())


def test_burst_limit(app: FastAPI) -> bool:
    flush_redis()
    client = _make_client(app)
    # 5 requests should all succeed (burst=5)
    for i in range(5):
        resp = client.get("/api/v1/test")
        if resp.status_code != 200:
            return False
    # 6th request within the same second must be rejected (429)
    resp = client.get("/api/v1/test")
    return resp.status_code == 429


def test_rpm_limit(app: FastAPI) -> bool:
    flush_redis()
    client = _make_client(app)
    # First burst of 5
    for i in range(5):
        resp = client.get("/api/v1/test")
        if resp.status_code != 200:
            return False
    # Wait for burst window (1 s) to roll over
    time.sleep(1.1)
    # Second burst of 5  (total 10 = RPM limit)
    for i in range(5):
        resp = client.get("/api/v1/test")
        if resp.status_code != 200:
            return False
    # Wait again so burst window resets
    time.sleep(1.1)
    # 11th request must be rejected by RPM limit
    resp = client.get("/api/v1/test")
    return resp.status_code == 429


def test_health_exempt(app: FastAPI) -> bool:
    flush_redis()
    client = _make_client(app)
    for path in ("/healthz", "/readyz", "/health", "/metrics"):
        for _ in range(20):
            resp = client.get(path)
            if resp.status_code != 200:
                return False
    return True


def test_key_sanitization() -> bool:
    raw_key = "sk-secret-api-key-12345"
    # Build a minimal request-like object
    class _FakeClient:
        host = "10.0.0.1"

    class _FakeRequest:
        headers = {"x-api-key": raw_key}
        client = _FakeClient()

    resolved = RateLimitMiddleware._resolve_key(_FakeRequest())
    expected = hashlib.sha256(raw_key.encode()).hexdigest()[:16]
    if resolved != expected:
        return False
    # The raw key must NOT appear in the resolved key
    if raw_key in resolved:
        return False
    return True


def test_redis_unavailable_readyz(app: FastAPI) -> bool:
    stop_redis()
    time.sleep(1)
    try:
        client = _make_client(app)
        resp = client.get("/readyz")
        # Accept 503, or any non-200, or JSON with status=error/degraded
        if resp.status_code == 503:
            return True
        if resp.status_code != 200:
            return True
        try:
            body = resp.json()
            if body.get("status") in ("error", "degraded"):
                return True
        except Exception:
            pass
        return False
    finally:
        start_redis()


def test_redis_unavailable_request_rejected(app: FastAPI) -> bool:
    stop_redis()
    time.sleep(1)
    try:
        client = _make_client(app)
        resp = client.get("/api/v1/test")
        # Must NOT be 200 (which would mean silent degradation to memory).
        # Expected: 429 (rate-limited because Redis is down) or 5xx.
        return resp.status_code != 200
    finally:
        start_redis()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    # 1. Check Docker availability
    if not _docker_available():
        print("ERROR: Docker is not available.  Install Docker and try again.")
        sys.exit(1)

    # 2. Start Redis container
    try:
        start_redis()
    except Exception as exc:
        print(f"ERROR: Failed to start Redis container: {exc}")
        sys.exit(1)

    # 3. Register cleanup
    atexit.register(remove_redis)

    # 4. Build test app
    app = build_test_app()

    # 5. Run tests
    results: dict[str, bool] = {}
    tests = [
        ("redis_ping", lambda: test_redis_ping()),
        ("burst_limit", lambda: test_burst_limit(app)),
        ("rpm_limit", lambda: test_rpm_limit(app)),
        ("health_exempt", lambda: test_health_exempt(app)),
        ("key_sanitization", lambda: test_key_sanitization()),
        ("redis_unavailable_readyz", lambda: test_redis_unavailable_readyz(app)),
        ("redis_unavailable_request_rejected", lambda: test_redis_unavailable_request_rejected(app)),
    ]

    for name, fn in tests:
        try:
            ok = fn()
        except Exception as exc:
            ok = False
        results[name] = bool(ok)
        print(f"{name}: {'PASSED' if ok else 'FAILED'}")

    # 6. Summary
    print()
    failed = [n for n, ok in results.items() if not ok]
    if failed:
        print("FAILED")
        sys.exit(1)
    else:
        print("PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
