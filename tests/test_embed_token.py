"""Tests des tokens d'embed HMAC-SHA256."""
import time
import pytest
from app.embed.token import generate_token, verify_token, EMBED_SECRET_ENV

_SECRET = "test-embed-secret-sprint8"


def test_generate_token_returns_embed_token(monkeypatch):
    monkeypatch.setenv(EMBED_SECRET_ENV, _SECRET)
    et = generate_token()
    assert et.token
    assert "." in et.token
    assert et.expires_at > int(time.time())


def test_verify_token_valid(monkeypatch):
    monkeypatch.setenv(EMBED_SECRET_ENV, _SECRET)
    et = generate_token(dashboard_id="dash1", scopes=["read"])
    result = verify_token(et.token)
    assert result is not None
    assert result.dashboard_id == "dash1"
    assert "read" in result.scopes


def test_verify_token_expired(monkeypatch):
    monkeypatch.setenv(EMBED_SECRET_ENV, _SECRET)
    et = generate_token(ttl_seconds=-1)
    result = verify_token(et.token)
    assert result is None


def test_verify_token_tampered_returns_none(monkeypatch):
    monkeypatch.setenv(EMBED_SECRET_ENV, _SECRET)
    et = generate_token()
    tampered = et.token[:-5] + "XXXXX"
    assert verify_token(tampered) is None


def test_verify_token_wrong_secret_returns_none(monkeypatch):
    monkeypatch.setenv(EMBED_SECRET_ENV, _SECRET)
    et = generate_token()
    result = verify_token(et.token, secret="wrong-secret")
    assert result is None


def test_generate_token_requires_secret(monkeypatch):
    monkeypatch.delenv(EMBED_SECRET_ENV, raising=False)
    with pytest.raises(ValueError, match="Secret"):
        generate_token(secret=None)


def test_token_dashboard_id_preserved(monkeypatch):
    monkeypatch.setenv(EMBED_SECRET_ENV, _SECRET)
    et = generate_token(dashboard_id="my-dash-42")
    result = verify_token(et.token)
    assert result.dashboard_id == "my-dash-42"


def test_token_scopes_preserved(monkeypatch):
    monkeypatch.setenv(EMBED_SECRET_ENV, _SECRET)
    et = generate_token(scopes=["read", "export"])
    result = verify_token(et.token)
    assert "read" in result.scopes
    assert "export" in result.scopes


def test_token_wildcard_dashboard(monkeypatch):
    monkeypatch.setenv(EMBED_SECRET_ENV, _SECRET)
    et = generate_token(dashboard_id="*")
    result = verify_token(et.token)
    assert result.dashboard_id == "*"


def test_verify_token_malformed_string(monkeypatch):
    monkeypatch.setenv(EMBED_SECRET_ENV, _SECRET)
    assert verify_token("not-a-valid-token") is None
    assert verify_token("") is None


def test_explicit_secret_overrides_env(monkeypatch):
    monkeypatch.setenv(EMBED_SECRET_ENV, "env-secret")
    et = generate_token(secret="explicit-secret")
    assert verify_token(et.token, secret="explicit-secret") is not None
    assert verify_token(et.token, secret="env-secret") is None
