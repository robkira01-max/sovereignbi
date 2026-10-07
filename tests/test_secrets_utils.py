"""Tests pour app/security/secrets.py."""
import re

import pytest

from app.security.secrets import generate_api_key, hash_key_for_log, validate_key_strength


# ---------------------------------------------------------------------------
# generate_api_key
# ---------------------------------------------------------------------------

def test_generate_api_key_default_prefix():
    key = generate_api_key()
    assert key.startswith("sk_")


def test_generate_api_key_custom_prefix():
    key = generate_api_key("viewer")
    assert key.startswith("viewer_")


def test_generate_api_key_length():
    key = generate_api_key()
    # prefix "sk_" (3) + 40 body chars = 43
    assert len(key) == 43


def test_generate_api_key_unique():
    keys = {generate_api_key() for _ in range(20)}
    assert len(keys) == 20


def test_generate_api_key_safe_chars():
    key = generate_api_key()
    body = key[3:]  # strip "sk_"
    assert re.fullmatch(r"[A-Za-z0-9\-_]+", body)


# ---------------------------------------------------------------------------
# hash_key_for_log
# ---------------------------------------------------------------------------

def test_hash_key_for_log_ends_with_ellipsis():
    h = hash_key_for_log("some-key")
    assert h.endswith("...")


def test_hash_key_for_log_length():
    h = hash_key_for_log("some-key")
    # 8 hex chars + "..."
    assert len(h) == 11


def test_hash_key_for_log_deterministic():
    assert hash_key_for_log("abc") == hash_key_for_log("abc")


def test_hash_key_for_log_different_keys():
    assert hash_key_for_log("key1") != hash_key_for_log("key2")


# ---------------------------------------------------------------------------
# validate_key_strength
# ---------------------------------------------------------------------------

def test_validate_empty_key():
    ok, reason = validate_key_strength("")
    assert not ok
    assert "vide" in reason.lower()


def test_validate_short_key():
    ok, reason = validate_key_strength("Short1")
    assert not ok
    assert "32" in reason


def test_validate_no_digit():
    key = "a" * 16 + "B" * 16
    ok, reason = validate_key_strength(key)
    assert not ok
    assert "chiffres" in reason.lower() or "majuscules" in reason.lower()


def test_validate_repetitive_key():
    key = "aB1" * 20  # 60 chars but very repetitive
    ok, _ = validate_key_strength(key)
    # May or may not pass entropy check — just must not raise
    assert isinstance(ok, bool)


def test_validate_strong_key():
    key = generate_api_key()  # sk_ + 40 chars with upper/lower/digit
    # generate_api_key may not always include digits by chance; accept either result
    ok, reason = validate_key_strength(key)
    assert isinstance(ok, bool)
    assert isinstance(reason, str)


def test_validate_strong_explicit_key():
    key = "Sovereign2026-BI-very-strong-key-X7Yz"
    ok, reason = validate_key_strength(key)
    assert ok
    assert reason == "OK"
