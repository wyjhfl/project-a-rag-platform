"""Rate limiting middleware for Project A RAG Platform."""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.errors import error_payload
from app.observability import current_request_id

logger = logging.getLogger("project_a")

_DEFAULT_EXEMPT_PATHS = frozenset({"/healthz", "/readyz", "/health", "/metrics"})

# ---------------------------------------------------------------------------
# Optional redis dependency
# ---------------------------------------------------------------------------
try:
    import redis as _redis
except ImportError:
    _redis = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Lua script for atomic Redis-backed sliding-window rate limiting.
# ---------------------------------------------------------------------------
_LUA_SLIDING_WINDOW_SCRIPT = """\
local burst_key = KEYS[1]
local rpm_key = KEYS[2]
local now_ms = tonumber(ARGV[1])
local burst_window_ms = tonumber(ARGV[2])
local rpm_window_ms = tonumber(ARGV[3])
local burst_limit = tonumber(ARGV[4])
local rpm_limit = tonumber(ARGV[5])
local member = ARGV[6]
local burst_ttl = tonumber(ARGV[7])
local rpm_ttl = tonumber(ARGV[8])

redis.call('ZREMRANGEBYSCORE', burst_key, 0, now_ms - burst_window_ms)
redis.call('ZREMRANGEBYSCORE', rpm_key, 0, now_ms - rpm_window_ms)

local burst_count = redis.call('ZCARD', burst_key)
local rpm_count = redis.call('ZCARD', rpm_key)

if burst_count >= burst_limit or rpm_count >= rpm_limit then
    redis.call('EXPIRE', burst_key, burst_ttl)
    redis.call('EXPIRE', rpm_key, rpm_ttl)
    return 0
end

redis.call('ZADD', burst_key, now_ms, member)
redis.call('ZADD', rpm_key, now_ms, member)
redis.call('EXPIRE', burst_key, burst_ttl)
redis.call('EXPIRE', rpm_key, rpm_ttl)
return 1
"""


# ---------------------------------------------------------------------------
# MemoryRateLimiter
# ---------------------------------------------------------------------------


class MemoryRateLimiter:
    """In-memory rate limiter using sliding window counters."""

    def __init__(self, requests_per_minute: int, burst: int) -> None:
        self._rpm = requests_per_minute
        self._burst = burst
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window = self._buckets[key]
        # Remove timestamps older than 60 seconds
        cutoff = now - 60.0
        self._buckets[key] = [t for t in window if t > cutoff]
        # Check RPM limit (total requests in the 60-second window)
        if len(self._buckets[key]) >= self._rpm:
            return False
        # Check burst limit (concurrent requests in short window)
        recent_cutoff = now - 1.0  # 1-second burst window
        recent_count = sum(1 for t in self._buckets[key] if t > recent_cutoff)
        if recent_count >= self._burst:
            return False
        self._buckets[key].append(now)
        return True

    def cleanup(self) -> None:
        now = time.monotonic()
        cutoff = now - 120.0
        empty_keys = []
        for key, timestamps in self._buckets.items():
            self._buckets[key] = [t for t in timestamps if t > cutoff]
            if not self._buckets[key]:
                empty_keys.append(key)
        for key in empty_keys:
            del self._buckets[key]

    def ping(self) -> bool:
        """Health check -- always returns True for in-memory limiter."""
        return True


# Backward-compatible alias
_RateLimiter = MemoryRateLimiter


# ---------------------------------------------------------------------------
# RedisRateLimiter
# ---------------------------------------------------------------------------


class RedisRateLimiter:
    """Redis-backed rate limiter using atomic sorted-set sliding windows.

    When Redis is unavailable, ``is_allowed`` returns ``False`` -- no silent
    degradation to in-memory fallback.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        requests_per_minute: int = 60,
        burst: int = 30,
    ) -> None:
        if _redis is None:
            raise RuntimeError(
                "redis package is required for RedisRateLimiter. "
                "Install it with: pip install redis"
            )
        self._rpm = requests_per_minute
        self._burst = burst
        self._redis_url = redis_url
        self._client = _redis.Redis.from_url(redis_url, decode_responses=True)
        self._script = self._client.register_script(_LUA_SLIDING_WINDOW_SCRIPT)

    def is_allowed(self, key: str) -> bool:
        now_ms = time.time_ns() // 1_000_000
        burst_key = f"project_a:ratelimit:burst:{key}"
        rpm_key = f"project_a:ratelimit:rpm:{key}"
        member = f"{now_ms}:{uuid.uuid4().hex}"
        try:
            return bool(
                int(
                    self._script(
                        keys=[burst_key, rpm_key],
                        args=[
                            now_ms,
                            1_000,
                            60_000,
                            self._burst,
                            self._rpm,
                            member,
                            2,
                            61,
                        ],
                    )
                )
            )
        except Exception:
            logger.exception("Redis rate limit check failed -- denying request")
            return False

    def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            return self._client.ping()
        except Exception:
            return False


# ---------------------------------------------------------------------------
# RateLimitMiddleware
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        enabled: bool = True,
        requests_per_minute: int = 60,
        burst: int = 30,
        exempt_paths: set[str] | None = None,
        backend: str = "memory",
        redis_url: str = "",
    ) -> None:
        super().__init__(app)
        self._enabled = enabled
        if backend == "redis" and redis_url:
            self._limiter = RedisRateLimiter(
                redis_url=redis_url,
                requests_per_minute=requests_per_minute,
                burst=burst,
            )
        else:
            self._limiter = MemoryRateLimiter(
                requests_per_minute=requests_per_minute,
                burst=burst,
            )
        self._exempt_paths = exempt_paths or _DEFAULT_EXEMPT_PATHS

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._enabled:
            return await call_next(request)

        if request.url.path in self._exempt_paths:
            return await call_next(request)

        key = self._resolve_key(request)
        if not self._limiter.is_allowed(key):
            rid = current_request_id() or getattr(request.state, "request_id", "")
            resp = JSONResponse(
                status_code=429,
                content=error_payload("rate_limited", "Too many requests. Please try again later.", rid),
            )
            resp.headers["X-Request-ID"] = rid
            resp.headers["Retry-After"] = "60"
            return resp

        return await call_next(request)

    @staticmethod
    def _resolve_key(request: Request) -> str:
        api_key = request.headers.get("x-api-key", "")
        if api_key:
            return hashlib.sha256(api_key.encode()).hexdigest()[:16]
        forwarded = request.headers.get("x-forwarded-for", "")
        client_host = request.client.host if request.client else "unknown"
        ip = forwarded.split(",")[0].strip() if forwarded else client_host
        return f"ip:{ip}"
