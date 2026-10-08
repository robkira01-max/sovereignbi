"""Session-wide fixtures and environment variables for the test suite.

Setting env vars here ensures all test modules use the same keys regardless
of import order. Individual test files may still use monkeypatch to override.
"""
import os

# These must be set before any app module is imported.
os.environ.setdefault("SOVEREIGN_EMBEDDER", "tfidf")

# RBAC keys — consistent across all test files
os.environ.setdefault("SOVEREIGN_VIEWER_KEY", "test-viewer-key-s6")
os.environ.setdefault("SOVEREIGN_EDITOR_KEY", "test-editor-key-s6")
os.environ.setdefault("SOVEREIGN_ADMIN_KEY", "test-admin-key-sprint3")

# Rate limiter — force high value so tests never hit the 60 rpm default
os.environ["SOVEREIGN_RATE_LIMIT_RPM"] = "100000"

# LLM timeout — fail fast so addin /ask tests don't hang waiting for Ollama
os.environ.setdefault("LLM_TIMEOUT", "5")
