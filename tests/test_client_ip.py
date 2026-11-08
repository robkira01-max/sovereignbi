"""Rate-limiter client IP resolution: X-Forwarded-For only from trusted proxies."""
from __future__ import annotations

import pytest

from starlette.datastructures import Headers

from app.api.middleware import RateLimitMiddleware, bucket_key


class _Req:
    def __init__(self, peer, xff=None):
        self.client = type("C", (), {"host": peer})() if peer is not None else None
        lines = [xff] if isinstance(xff, str) else list(xff or [])
        self.headers = Headers(raw=[(b"x-forwarded-for", v.encode()) for v in lines])


def ip(peer, xff=None):
    return RateLimitMiddleware._client_ip(_Req(peer, xff))


@pytest.fixture(autouse=True)
def _default_trust(monkeypatch):
    monkeypatch.delenv("SOVEREIGN_TRUSTED_PROXIES", raising=False)


def test_public_peer_cannot_spoof_xff():
    assert ip("198.51.100.7", "1.2.3.4") == "198.51.100.7"
    assert ip("198.51.100.7", "1.2.3.4, 5.6.7.8") == "198.51.100.7"


def test_no_xff_returns_peer():
    assert ip("10.0.0.1") == "10.0.0.1"
    assert ip("198.51.100.7") == "198.51.100.7"


def test_missing_client_returns_unknown():
    assert ip(None) == "unknown"


def test_private_peer_uses_xff():
    assert ip("172.18.0.3", "203.0.113.5") == "203.0.113.5"


def test_rightmost_untrusted_hop_wins_over_client_supplied_prefix():
    # client sent "9.9.9.9"; the edge proxy appended the real address
    assert ip("10.0.0.1", "9.9.9.9, 203.0.113.5") == "203.0.113.5"
    assert ip("10.0.0.1", "9.9.9.9, 203.0.113.5, 10.0.0.2") == "203.0.113.5"


def test_all_hops_trusted_falls_back_to_peer():
    assert ip("10.0.0.1", "10.0.0.2, 192.168.1.1") == "10.0.0.1"


def test_garbage_hop_falls_back_to_peer():
    assert ip("10.0.0.1", "not-an-ip") == "10.0.0.1"
    assert ip("10.0.0.1", "x" * 500) == "10.0.0.1"


def test_non_ip_peer_is_untrusted():
    assert ip("testclient", "1.2.3.4") == "testclient"


def test_ipv4_mapped_ipv6_peer_is_handled():
    assert ip("::ffff:10.0.0.1", "203.0.113.5") == "203.0.113.5"
    assert ip("::ffff:198.51.100.7", "1.2.3.4") == "::ffff:198.51.100.7"


def test_ipv6_client_is_normalised():
    assert ip("10.0.0.1", "2001:DB8::1") == "2001:db8::1"


def test_env_none_disables_xff_entirely(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TRUSTED_PROXIES", "none")
    assert ip("10.0.0.1", "203.0.113.5") == "10.0.0.1"


def test_env_explicit_cidr(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TRUSTED_PROXIES", "203.0.113.0/24")
    # a private peer is no longer trusted when an explicit list replaces the default
    assert ip("10.0.0.1", "1.2.3.4") == "10.0.0.1"
    assert ip("203.0.113.10", "1.2.3.4") == "1.2.3.4"


def test_env_invalid_entry_fails_closed(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TRUSTED_PROXIES", "garbage, 999.1.1.1/8")
    assert ip("10.0.0.1", "203.0.113.5") == "10.0.0.1"


def test_env_private_keyword_combines_with_cidr(monkeypatch):
    monkeypatch.setenv("SOVEREIGN_TRUSTED_PROXIES", "private, 203.0.113.0/24")
    assert ip("10.0.0.1", "198.51.100.9") == "198.51.100.9"
    assert ip("203.0.113.10", "198.51.100.9") == "198.51.100.9"


def test_spoofed_xff_cannot_evade_rate_limit_bucket():
    """Rotating XFF values from one public peer must map to a single bucket."""
    assert len({ip("198.51.100.7", f"1.1.1.{i}") for i in range(50)}) == 1


def test_multiple_xff_header_lines_are_joined():
    """A proxy that adds its own header line must not let a client-supplied first line win."""
    assert ip("10.0.0.1", ["9.9.9.9", "203.0.113.5"]) == "203.0.113.5"


def test_ipv6_zone_id_is_stripped():
    assert ip("10.0.0.1", "2001:db8::1%eth0") == "2001:db8::1"
    assert len({ip("10.0.0.1", f"2001:db8::1%z{i}") for i in range(20)}) == 1


def test_ipv6_clients_share_a_slash_64_bucket():
    assert bucket_key("2001:db8:1:2::1") == bucket_key("2001:db8:1:2:ffff:ffff:ffff:ffff")
    assert bucket_key("2001:db8:1:2::1") != bucket_key("2001:db8:1:3::1")


def test_ipv4_and_unknown_buckets_unchanged():
    assert bucket_key("203.0.113.5") == "203.0.113.5"
    assert bucket_key("unknown") == "unknown"
    assert bucket_key("testclient") == "testclient"


def test_rate_limiter_store_is_swept(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import middleware as mw

    monkeypatch.setattr(mw, "_MAX_BUCKETS", 5)
    created = {}

    class Spy(mw.RateLimitMiddleware):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            created["mw"] = self

    app = FastAPI()
    app.get("/ping")(lambda: {"ok": True})
    app.add_middleware(Spy, rpm=100)
    with TestClient(app) as c:
        c.get("/ping")
        limiter = created["mw"]
        for i in range(30):
            limiter._store[f"10.1.0.{i}"].append(0.0)  # long-expired entries
        limiter._last_sweep = 0.0
        c.get("/ping")
        assert set(limiter._store) == {"testclient"}
