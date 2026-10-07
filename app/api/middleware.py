"""API middleware stack : version header, response time, security headers, rate limiting."""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

CURRENT_API_VERSION = "v1"

# Paths exempt from rate limiting (K8s probes, Prometheus scrape)
_RATE_EXEMPT = frozenset({"/health", "/live", "/ready", "/metrics"})


class ApiVersionMiddleware(BaseHTTPMiddleware):
    """Inject X-API-Version and X-Response-Time on every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-API-Version"] = CURRENT_API_VERSION
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject standard defensive headers on every response."""

    _HEADERS: dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none'"
        ),
    }

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in self._HEADERS.items():
            response.headers.setdefault(header, value)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter per client IP.

    Default: 60 requests / minute.  Override with SOVEREIGN_RATE_LIMIT_RPM env var.
    Returns 429 with Retry-After header when the window is exceeded.
    Endpoints in _RATE_EXEMPT are bypassed entirely.
    """

    def __init__(self, app, rpm: int | None = None) -> None:
        super().__init__(app)
        self._rpm: int = rpm if rpm is not None else int(
            os.environ.get("SOVEREIGN_RATE_LIMIT_RPM", "60")
        )
        self._window = 60.0
        self._lock = threading.Lock()
        self._store: dict[str, deque[float]] = defaultdict(deque)

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _RATE_EXEMPT:
            return await call_next(request)

        ip = self._client_ip(request)
        now = time.time()
        cutoff = now - self._window

        with self._lock:
            dq = self._store[ip]
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= self._rpm:
                retry_after = max(1, int(self._window - (now - dq[0])) + 1)
                reset_ts = int(dq[0] + self._window) if dq else int(now + self._window)
                return JSONResponse(
                    {"detail": "Trop de requêtes. Veuillez réessayer dans un instant."},
                    status_code=429,
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self._rpm),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_ts),
                    },
                )
            dq.append(now)
            remaining = self._rpm - len(dq)
            reset_ts = int(dq[0] + self._window)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._rpm)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_ts)
        return response
