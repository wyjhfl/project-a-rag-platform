"""Rate limiting middleware for Project A RAG Platform."""
from __future__ import annotations

import hashlib
import logging
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.errors import error_payload
from app.observability import current_request_id

logger = logging.getLogger("project_a")

_DEFAULT_EXEMPT_PATHS = frozenset({"/healthz", "/readyz", "/health", "/metrics"})


class _RateLimiter:
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


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        enabled: bool = True,
        requests_per_minute: int = 60,
        burst: int = 30,
        exempt_paths: set[str] | None = None,
    ) -> None:
        super().__init__(app)
        self._enabled = enabled
        self._limiter = _RateLimiter(requests_per_minute, burst)
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
