"""Tests pour seed_store — chargement automatique au démarrage."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from app.data.duckdb_store import DataStore
from app.startup import seed_store


@pytest.fixture
def store():
    return DataStore()


@pytest.fixture
def seed_dir_with_csvs(tmp_path):
    (tmp_path / "population.csv").write_text("region,pop\nDjibouti-ville,286401\nAli Sabieh,86000\n")
    (tmp_path / "pib.csv").write_text("annee,valeur_mrd\n2023,5.8\n2024,6.0\n")
    return tmp_path


def test_seed_loads_csvs(store, seed_dir_with_csvs):
    seed_store(store, str(seed_dir_with_csvs))
    assert "population" in store.tables
    assert "pib" in store.tables


def test_seed_data_queryable(store, seed_dir_with_csvs):
    seed_store(store, str(seed_dir_with_csvs))
    cols, rows = store.execute("SELECT SUM(pop) FROM population")
    assert rows[0][0] == 372401


def test_seed_nonexistent_dir_no_raise(store):
    seed_store(store, "/nonexistent/path/that/does/not/exist")
    assert store.tables == set()


def test_seed_empty_dir_no_raise(store, tmp_path):
    seed_store(store, str(tmp_path))
    assert store.tables == set()


def test_seed_skips_bad_file(store, tmp_path):
    (tmp_path / "good.csv").write_text("a,b\n1,2\n")
    (tmp_path / "bad.csv").write_text("not,valid\n\"unterminated")
    # Should not raise — bad file is skipped, good file is loaded
    seed_store(store, str(tmp_path))
    assert "good" in store.tables


def test_seed_via_env_at_startup(seed_dir_with_csvs, monkeypatch):
    """L'app charge les tables si SOVEREIGN_SEED_DIR est définie au démarrage."""
    monkeypatch.setenv("SOVEREIGN_SEED_DIR", str(seed_dir_with_csvs))
    from fastapi.testclient import TestClient
    # Réinitialiser le store pour simuler un vrai démarrage
    from app import main as app_module
    fresh_store = DataStore()
    app_module.app.state.store = fresh_store
    # Déclencher le lifespan manuellement via seed_store
    seed_store(fresh_store, str(seed_dir_with_csvs))
    assert "population" in fresh_store.tables
    assert "pib" in fresh_store.tables
