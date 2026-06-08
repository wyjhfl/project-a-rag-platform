"""Unit tests for the Redis rate limiting system.

Uses mock Redis (unittest.mock) — the real Redis smoke test lives in
scripts/redis_rate_limit_smoke.py.
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure backend is on sys.path so ``app.*`` imports work.
_BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)  # noqa: E402

from app.rate_limit import MemoryRateLimiter, RateLimitMiddleware, RedisRateLimiter  # noqa: E402

# ---------------------------------------------------------------------------
# TestMemoryRateLimiter
# ---------------------------------------------------------------------------


class TestMemoryRateLimiter:
    """Tests for the in-memory rate limiter."""

    def test_allows_under_limit(self):
        """Requests under both RPM and burst limits are allowed."""
        limiter = MemoryRateLimiter(requests_per_minute=60, burst=30)
        for i in range(30):
            assert limiter.is_allowed("key1") is True, f"request {i} should be allowed"

    def test_blocks_over_burst(self):
        """Requests exceeding the burst limit within 1 second are blocked."""
        limiter = MemoryRateLimiter(requests_per_minute=100, burst=5)
        for _ in range(5):
            limiter.is_allowed("key1")
        assert limiter.is_allowed("key1") is False

    def test_blocks_over_rpm(self):
        """Requests exceeding the RPM limit within 60 seconds are blocked."""
        limiter = MemoryRateLimiter(requests_per_minute=5, burst=100)
        for _ in range(5):
            limiter.is_allowed("key1")
        assert limiter.is_allowed("key1") is False

    def test_cleanup_removes_old_entries(self):
        """cleanup() removes timestamps older than 120 seconds."""
        limiter = MemoryRateLimiter(requests_per_minute=60, burst=30)
        # Inject an old timestamp manually
        old_time = time.monotonic() - 200.0
        limiter._buckets["old_key"] = [old_time]
        assert "old_key" in limiter._buckets
        limiter.cleanup()
        assert "old_key" not in limiter._buckets

    def test_ping_returns_true(self):
        """ping() always returns True for the memory limiter."""
        limiter = MemoryRateLimiter(requests_per_minute=60, burst=30)
        assert limiter.ping() is True


# ---------------------------------------------------------------------------
# TestRedisRateLimiter
# ---------------------------------------------------------------------------


class TestRedisRateLimiter:
    """Tests for the Redis-backed rate limiter using mocks.

    We patch ``app.rate_limit._redis`` (the module-level variable set by
    ``import redis as _redis``) so that ``RedisRateLimiter.__init__`` sees
    our mock instead of the real (or missing) redis package.
    """

    def setup_method(self):
        self.mock_redis_patcher = patch("app.rate_limit._redis")
        self.mock_redis_mod = self.mock_redis_patcher.start()

        # Setup mock client
        self.mock_client = MagicMock()
        self.mock_redis_mod.Redis.from_url.return_value = self.mock_client
        self.mock_client.ping.return_value = True

        # Setup mock script
        self.mock_script = MagicMock()
        self.mock_client.register_script.return_value = self.mock_script

        # Create limiter
        self.limiter = RedisRateLimiter(
            redis_url="redis://localhost:6379/0",
            requests_per_minute=60,
            burst=30,
        )

    def teardown_method(self):
        self.mock_redis_patcher.stop()

    def test_is_allowed_under_limit(self):
        """When Redis INCR returns low values, the request is allowed."""
        self.mock_script.return_value = 1
        assert self.limiter.is_allowed("testkey") is True

    def test_is_allowed_over_burst(self):
        """When burst counter exceeds the burst limit, the request is denied."""
        self.mock_script.return_value = 0
        assert self.limiter.is_allowed("testkey") is False

    def test_is_allowed_over_rpm(self):
        """When RPM counter exceeds the RPM limit, the request is denied."""
        self.mock_script.return_value = 0
        assert self.limiter.is_allowed("testkey") is False

    def test_ping_success(self):
        """When redis.ping() returns True, ping() returns True."""
        self.mock_client.ping.return_value = True
        assert self.limiter.ping() is True

    def test_ping_failure(self):
        """When redis.ping() raises ConnectionError, ping() returns False."""
        self.mock_client.ping.side_effect = ConnectionError("Connection refused")
        assert self.limiter.ping() is False

    def test_connection_error_denies_request(self):
        """When Redis connection fails, is_allowed returns False."""
        self.mock_script.side_effect = ConnectionError("Connection refused")
        assert self.limiter.is_allowed("testkey") is False

    def test_key_format(self):
        """Verify keys use the correct format with project_a:ratelimit: prefix."""
        captured_keys = []
        self.mock_script.side_effect = lambda keys, args: (
            captured_keys.extend(keys) or 1
        )
        self.limiter.is_allowed("mykey")
        assert len(captured_keys) == 2
        # First key is burst, second is RPM
        assert captured_keys[0] == "project_a:ratelimit:burst:mykey"
        assert captured_keys[1] == "project_a:ratelimit:rpm:mykey"


# ---------------------------------------------------------------------------
# TestRateLimitMiddleware
# ---------------------------------------------------------------------------


class TestRateLimitMiddleware:
    """Tests for the rate-limiting middleware."""

    @pytest.fixture()
    def app_with_middleware(self):
        """Create a minimal Starlette app with RateLimitMiddleware."""
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route

        async def homepage(request):
            return PlainTextResponse("ok")

        async def healthz(request):
            return PlainTextResponse("healthy")

        async def readyz(request):
            return PlainTextResponse("ready")

        async def health(request):
            return PlainTextResponse("health")

        async def metrics(request):
            return PlainTextResponse("# metrics")

        routes = [
            Route("/", homepage),
            Route("/healthz", healthz),
            Route("/readyz", readyz),
            Route("/health", health),
            Route("/metrics", metrics),
        ]
        app = Starlette(routes=routes)
        app.add_middleware(
            RateLimitMiddleware,
            enabled=True,
            requests_per_minute=2,
            burst=2,
        )
        return app

    def test_exempt_paths(self, app_with_middleware):
        """Requests to /healthz, /readyz, /health, /metrics bypass rate limiting."""
        from starlette.testclient import TestClient

        client = TestClient(app_with_middleware)
        # Hit exempt paths many times — they should never be rate-limited
        for path in ["/healthz", "/readyz", "/health", "/metrics"]:
            for _ in range(10):
                response = client.get(path)
                assert response.status_code == 200, f"{path} should not be rate-limited"

    def test_key_sanitization(self):
        """API key is hashed (SHA256[:16]), not stored in plain text in the limiter key."""
        raw_key = "sk-secret-api-key-12345"
        req = MagicMock()
        req.headers = {"x-api-key": raw_key}
        req.client = MagicMock()
        req.client.host = "1.2.3.4"

        resolved = RateLimitMiddleware._resolve_key(req)
        # The resolved key should be the SHA256 hex digest truncated to 16 chars
        expected = hashlib.sha256(raw_key.encode()).hexdigest()[:16]
        assert resolved == expected
        # Must NOT be the raw key
        assert resolved != raw_key

    def test_429_response(self, app_with_middleware):
        """Over-limit requests return 429 with proper error body."""
        from starlette.testclient import TestClient

        client = TestClient(app_with_middleware)
        # Exhaust the limit (2 RPM, 2 burst)
        client.get("/")
        client.get("/")
        # Third request should be 429
        response = client.get("/")
        assert response.status_code == 429
        body = response.json()
        assert "error" in body or "code" in body or "message" in body

    def test_disabled_middleware(self):
        """When enabled=False, all requests pass through regardless of limits."""
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(
            RateLimitMiddleware,
            enabled=False,
            requests_per_minute=1,
            burst=1,
        )
        client = TestClient(app)
        # Even with RPM=1, burst=1, all requests should pass through
        for _ in range(20):
            response = client.get("/")
            assert response.status_code == 200
