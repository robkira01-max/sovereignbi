"""Tests for app/learning/versioning.py."""
import time

import pytest
import yaml

from app.learning.versioning import list_versions, rollback, snapshot


def _model_yaml(rules: list[str] | None = None) -> str:
    data = {"schema_version": "2", "rules": rules or ["Règle initiale."]}
    return yaml.dump(data, allow_unicode=True)


# ── snapshot ──────────────────────────────────────────────────────────────────


def test_snapshot_creates_file(tmp_path):
    model = tmp_path / "model.yaml"
    model.write_text(_model_yaml(), encoding="utf-8")
    vdir = tmp_path / "versions"

    dest = snapshot(model_path=model, versions_dir=vdir)
    assert dest.exists()
    assert dest.suffix == ".yaml"


def test_snapshot_copies_content(tmp_path):
    model = tmp_path / "model.yaml"
    content = _model_yaml(["Règle spéciale pour le test."])
    model.write_text(content, encoding="utf-8")
    vdir = tmp_path / "versions"

    dest = snapshot(model_path=model, versions_dir=vdir)
    restored = yaml.safe_load(dest.read_text(encoding="utf-8"))
    assert "Règle spéciale pour le test." in restored["rules"]


def test_snapshot_with_label(tmp_path):
    model = tmp_path / "model.yaml"
    model.write_text(_model_yaml(), encoding="utf-8")
    vdir = tmp_path / "versions"

    dest = snapshot(label="my_label", model_path=model, versions_dir=vdir)
    assert "my_label" in dest.name


def test_snapshot_creates_versions_dir(tmp_path):
    model = tmp_path / "model.yaml"
    model.write_text(_model_yaml(), encoding="utf-8")
    vdir = tmp_path / "nonexistent" / "versions"
    assert not vdir.exists()

    snapshot(model_path=model, versions_dir=vdir)
    assert vdir.exists()


# ── list_versions ─────────────────────────────────────────────────────────────


def test_list_versions_empty_dir(tmp_path):
    vdir = tmp_path / "versions"
    vdir.mkdir()
    assert list_versions(versions_dir=vdir) == []


def test_list_versions_nonexistent_dir(tmp_path):
    assert list_versions(versions_dir=tmp_path / "nope") == []


def test_list_versions_returns_metadata(tmp_path):
    model = tmp_path / "model.yaml"
    model.write_text(_model_yaml(), encoding="utf-8")
    vdir = tmp_path / "versions"

    snapshot(model_path=model, versions_dir=vdir)
    versions = list_versions(versions_dir=vdir)
    assert len(versions) == 1
    v = versions[0]
    assert "filename" in v
    assert "path" in v
    assert "size" in v
    assert "label" in v
    assert v["size"] > 0


def test_list_versions_sorted(tmp_path):
    model = tmp_path / "model.yaml"
    model.write_text(_model_yaml(), encoding="utf-8")
    vdir = tmp_path / "versions"

    snapshot(label="first", model_path=model, versions_dir=vdir)
    time.sleep(1.1)  # ensure different timestamp
    snapshot(label="second", model_path=model, versions_dir=vdir)

    versions = list_versions(versions_dir=vdir)
    assert len(versions) == 2
    assert versions[0]["filename"] < versions[1]["filename"]  # sorted lexicographically


# ── rollback ──────────────────────────────────────────────────────────────────


def test_rollback_replaces_model(tmp_path):
    model = tmp_path / "model.yaml"
    model.write_text(_model_yaml(["Règle v1."]), encoding="utf-8")
    vdir = tmp_path / "versions"

    snap = snapshot(model_path=model, versions_dir=vdir)
    model.write_text(_model_yaml(["Règle v2."]), encoding="utf-8")

    rollback(snap.name, model_path=model, versions_dir=vdir)
    restored = yaml.safe_load(model.read_text(encoding="utf-8"))
    assert "Règle v1." in restored["rules"]


def test_rollback_creates_pre_rollback_snapshot(tmp_path):
    model = tmp_path / "model.yaml"
    model.write_text(_model_yaml(["Règle v1."]), encoding="utf-8")
    vdir = tmp_path / "versions"

    snap = snapshot(model_path=model, versions_dir=vdir)
    model.write_text(_model_yaml(["Règle v2."]), encoding="utf-8")

    rollback(snap.name, model_path=model, versions_dir=vdir)
    versions = list_versions(versions_dir=vdir)
    labels = [v["label"] for v in versions]
    assert "pre_rollback" in labels


def test_rollback_unknown_version_raises(tmp_path):
    model = tmp_path / "model.yaml"
    model.write_text(_model_yaml(), encoding="utf-8")
    vdir = tmp_path / "versions"
    vdir.mkdir()

    with pytest.raises(FileNotFoundError):
        rollback("model_19990101_000000_ghost.yaml", model_path=model, versions_dir=vdir)
