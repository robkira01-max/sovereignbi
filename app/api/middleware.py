"""API version header middleware."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CURRENT_API_VERSION = "v1"


class ApiVersionMiddleware(BaseHTTPMiddleware):
    """Inject X-API-Version header on every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-API-Version"] = CURRENT_API_VERSION
        return response
