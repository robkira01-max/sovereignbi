"""API middleware : version header + response time."""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CURRENT_API_VERSION = "v1"


class ApiVersionMiddleware(BaseHTTPMiddleware):
    """Inject X-API-Version and X-Response-Time headers on every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-API-Version"] = CURRENT_API_VERSION
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        return response
