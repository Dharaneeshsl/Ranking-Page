"""
System middleware: request IDs, security headers and in-memory rate limiting.

NOTE: rate limiting is per-process in-memory. In multi-instance deployments put
a load balancer / API gateway in front (or swap for a Redis-backed limiter).
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

import config

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id and log request duration."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        if request.url.path.startswith("/api/auth"):
            response.headers["Cache-Control"] = "no-store"
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Hardening headers for every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        if config.COOKIE_SECURE:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limit per IP (login + global buckets)."""

    def __init__(self, app):
        super().__init__(app)
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._last_cleanup = time.monotonic()

    def _client_ip(self, request: Request) -> str:
        # Trusted proxy headers are set by uvicorn --proxy-headers (Docker/nginx).
        if request.headers.get("x-forwarded-for"):
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _allow(self, key: str, limit: int, window: float = 60.0) -> Tuple[bool, int]:
        now = time.monotonic()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit:
            retry = int(window - (now - bucket[0])) + 1
            return False, max(retry, 1)
        bucket.append(now)
        return True, 0

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Periodic cleanup so memory stays flat.
        now = time.monotonic()
        if now - self._last_cleanup > 300:
            for key in [k for k, v in self._hits.items() if not v]:
                self._hits.pop(key, None)
            self._last_cleanup = now

        ip = self._client_ip(request)
        path = request.url.path

        if path.endswith("/auth/login") and request.method == "POST":
            ok, retry = self._allow(f"login:{ip}", config.RATE_LIMIT_LOGIN_PER_MINUTE)
        else:
            ok, retry = self._allow(f"global:{ip}", config.RATE_LIMIT_PER_MINUTE)

        if not ok:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded. Please try again shortly.",
                    "retry_after": retry,
                },
                headers={"Retry-After": str(retry)},
            )
        return await call_next(request)
