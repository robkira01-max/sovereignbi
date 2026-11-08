"""API middleware stack : version header, response time, security headers, rate limiting."""
from __future__ import annotations

import ipaddress
import os
import threading
import time
from collections import defaultdict, deque
from functools import lru_cache

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

CURRENT_API_VERSION = "v1"

# Paths exempt from rate limiting (K8s probes, Prometheus scrape)
_RATE_EXEMPT = frozenset({"/health", "/live", "/ready", "/metrics"})

_MAX_BUCKETS = 10_000

_PRIVATE_NETS = (
    "127.0.0.0/8", "::1/128", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
    "169.254.0.0/16", "fc00::/7", "fe80::/10",
)


@lru_cache(maxsize=8)
def _trusted_networks(raw: str) -> tuple:
    nets: list = []
    for part in raw.split(","):
        part = part.strip().lower()
        if not part or part == "none":
            continue
        if part == "private":
            nets += [ipaddress.ip_network(n) for n in _PRIVATE_NETS]
            continue
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            continue  # invalid entry → fail closed (not trusted)
    return tuple(nets)


def _parse_ip(value: str):
    try:
        # Drop an IPv6 zone id ("fe80::1%eth0"): each suffix would be a fresh bucket.
        ip = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return None
    return ip.ipv4_mapped if getattr(ip, "ipv4_mapped", None) else ip


def bucket_key(ip: str) -> str:
    """Rate-limit bucket for a client address. IPv6 clients usually own a whole /64,
    so bucketing per address would let them rotate addresses to dodge limits."""
    parsed = _parse_ip(ip)
    if parsed is not None and parsed.version == 6:
        return str(ipaddress.ip_network(f"{parsed}/64", strict=False))
    return ip


def _is_trusted(value: str, nets: tuple) -> bool:
    ip = _parse_ip(value)
    return ip is not None and any(ip in n for n in nets)


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
        self._last_sweep = 0.0

    @staticmethod
    def _client_ip(request: Request) -> str:
        """Real client IP. X-Forwarded-For is honoured only when the TCP peer is a
        trusted proxy (SOVEREIGN_TRUSTED_PROXIES: CIDR list, 'private' [default], 'none'),
        and is read right-to-left so client-supplied leftmost entries are never trusted."""
        peer = request.client.host if request.client else "unknown"
        # A proxy may add its own header line instead of appending to an existing one.
        forwarded = ",".join(request.headers.getlist("x-forwarded-for"))
        if not forwarded:
            return peer
        nets = _trusted_networks(os.environ.get("SOVEREIGN_TRUSTED_PROXIES", "private"))
        if not _is_trusted(peer, nets):
            return peer
        for hop in reversed([h.strip() for h in forwarded.split(",") if h.strip()]):
            if _is_trusted(hop, nets):
                continue
            ip = _parse_ip(hop)
            return str(ip) if ip is not None else peer
        return peer

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _RATE_EXEMPT:
            return await call_next(request)

        ip = bucket_key(self._client_ip(request))
        now = time.time()
        cutoff = now - self._window

        with self._lock:
            if len(self._store) > _MAX_BUCKETS and now - self._last_sweep > self._window / 10:
                self._last_sweep = now
                for k in [k for k, d in self._store.items() if not d or d[-1] < cutoff]:
                    del self._store[k]
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
