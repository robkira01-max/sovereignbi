"""P-086a : espace de travail — sources montées côté serveur, copies figées, versions, chemins hostiles, droits."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import feedback
from app.data.duckdb_store import DataStore
from app.workspace import extract, paths

ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}
VIEWER = {"X-Api-Key": "test-viewer-key-s6"}
ROOT = Path(__file__).resolve().parents[1]
CSV = b"region,annee,valeur\nObock,2024,10\nTadjourah,2024,12\n"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    src = tmp_path / "allowed" / "dossier"
    src.mkdir(parents=True)
    (src / "chiffres.csv").write_bytes(CSV)
    monkeypatch.setenv("WORKSPACE_ALLOWED_ROOTS", str(tmp_path / "allowed"))
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp_path / "store"))
    monkeypatch.delenv("WORKSPACE_ALLOW_THIRD_PARTY", raising=False)
    monkeypatch.setattr(feedback, "AUDIT_PATH", tmp_path / "audit.jsonl")
    monkeypatch.setenv("SOVEREIGN_AUDIT_DOCS_DIR", str(tmp_path / "docs"))
    monkeypatch.setenv("SOVEREIGN_AUTH_DB", str(tmp_path / "auth.db"))
    from app.auth import security as sec
    sec.init_auth_db()
    from app.main import app
    monkeypatch.setattr(app.state, "store", DataStore(), raising=False)
    with TestClient(app) as c:
        yield c, src, tmp_path


def admin_session(c):
    """Créer et activer une source exige une SESSION administrateur (pas une clé), comme les autres actions de gouvernance."""
    from app.auth import security as sec
    email = f"adm-{os.urandom(3).hex()}@example.org"
    sec.create_user(email, "Un-mot-de-passe-long-1", "admin")
    t = c.post("/auth/login", json={"email": email, "password": "Un-mot-de-passe-long-1"}).json()["token"]
    return {"Authorization": f"Bearer {t}"}


def connect(c, src, min_role="viewer", name="Cabinet"):
    r = c.post("/workspace/sources", json={"type": "mounted_folder", "name": name, "root": str(src), "min_role": min_role}, headers=admin_session(c))
    assert r.status_code == 201, r.text
    return r.json()["source_id"]


def importing(c, sid, path="chiffres.csv", headers=EDITOR):
    return c.post(f"/workspace/sources/{sid}/import", json={"path": path}, headers=headers)


def actions(tmp_path):
    p = tmp_path / "audit.jsonl"
    return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []


# ── rôles ────────────────────────────────────────────────────────────────────────────────────────────────────────

def test_admin_connects_viewer_sees_files_but_cannot_import_editor_imports(env):
    c, src, _ = env
    assert c.post("/workspace/sources", json={"type": "mounted_folder", "name": "x", "root": str(src)}, headers=EDITOR).status_code == 403
    sid = connect(c, src)
    assert importing(c, sid, headers=VIEWER).status_code == 403
    r = importing(c, sid)
    assert r.status_code == 201 and r.json()["file"]["status"] == "Indexé" and r.json()["file"]["summary"]["rows"] == 2
    files = c.get(f"/workspace/sources/{sid}/files", headers=VIEWER).json()
    assert [f["path"] for f in files["files"]] == ["chiffres.csv"] and "available" not in files      # le disque n'est listé que pour les éditeurs
    assert c.get(f"/workspace/sources/{sid}/files", headers=EDITOR).json()["available"][0]["imported"] is True


def test_viewer_never_sees_the_server_path_and_responses_carry_no_credential(env):
    c, src, tmp = env
    sid = connect(c, src)
    importing(c, sid)
    blob = json.dumps([c.get("/workspace/sources", headers=VIEWER).json(), c.get(f"/workspace/sources/{sid}/files", headers=VIEWER).json(),
                       c.get("/workspace/status", headers=VIEWER).json()])
    assert str(src) not in blob and str(tmp) not in blob
    assert not re.search(r"credential|password|secret|token", blob, re.I)
    assert c.get("/workspace/sources", headers=ADMIN).json()[0]["root"] == os.path.realpath(src)
    log = (tmp / "audit.jsonl").read_text()
    assert "Obock" not in log and not re.search(r"credential|password", log, re.I)       # jamais de contenu dans le journal


def test_user_without_right_on_a_folder_sees_neither_files_nor_names(env):
    c, src, _ = env
    sid = connect(c, src, min_role="editor", name="Dossier confidentiel")
    importing(c, sid)
    fid = c.get(f"/workspace/sources/{sid}/files", headers=EDITOR).json()["files"][0]["file_id"]
    assert c.get("/workspace/sources", headers=VIEWER).json() == []
    for r in (c.get(f"/workspace/sources/{sid}/files", headers=VIEWER), c.get(f"/workspace/files/{fid}/content", headers=VIEWER),
              c.get("/workspace/sources/999/files", headers=VIEWER)):
        assert r.status_code == 404 and r.json() == c.get("/workspace/sources/999/files", headers=VIEWER).json()      # 404 uniforme
    assert "Dossier confidentiel" not in c.get("/workspace/sources", headers=VIEWER).text


def test_disabled_source_is_hidden_from_non_admins(env):
    c, src, _ = env
    sid = connect(c, src)
    assert c.patch(f"/workspace/sources/{sid}", json={"state": "disabled"}, headers=EDITOR).status_code == 403
    assert c.patch(f"/workspace/sources/{sid}", json={"state": "disabled"}, headers=admin_session(c)).status_code == 200
    assert c.get("/workspace/sources", headers=VIEWER).json() == [] and importing(c, sid).status_code == 404
    assert len(c.get("/workspace/sources", headers=ADMIN).json()) == 1


# ── chemins hostiles ─────────────────────────────────────────────────────────────────────────────────────────────

def test_hostile_paths_are_refused_and_journalised(env):
    c, src, tmp = env
    sid = connect(c, src)
    outside = tmp / "secret.csv"
    outside.write_bytes(b"a,b\n1,2\n")
    (src / "lien.csv").symlink_to(outside)
    (src / "sousdossier").symlink_to(tmp)                   # répertoire intermédiaire qui sort de la racine
    for bad in ("../secret.csv", "a/../../secret.csv", "/etc/passwd", str(outside), "x\x00.csv", "a\\b.csv", "lien.csv", "sousdossier/secret.csv", "./chiffres.csv", ""):
        r = importing(c, sid, path=bad)
        assert r.status_code in (404, 422), (bad, r.status_code)
    refused = [a for a in actions(tmp) if a["action"] == "workspace_import_refused"]
    assert len(refused) >= 8
    assert not (tmp / "store").exists() or not any(p.name == hashlib.sha256(b"a,b\n1,2\n").hexdigest() for p in (tmp / "store").rglob("*"))


def test_symlink_swapped_between_validation_and_read_is_refused(env, monkeypatch):
    c, src, tmp = env
    sid = connect(c, src)
    outside = tmp / "secret.csv"
    outside.write_bytes(b"a,b\n1,2\n")
    real_open = os.open

    def swapping_open(path, flags, *a, **k):
        if str(path).endswith("chiffres.csv"):                 # l'attaquant échange le fichier contre un lien APRÈS la validation
            os.unlink(path)
            os.symlink(outside, path)
        return real_open(path, flags, *a, **k)
    monkeypatch.setattr(paths.os, "open", swapping_open)
    r = importing(c, sid)
    assert r.status_code == 404
    assert any(a["details"].get("code") == "symlink_refused" for a in actions(tmp))


def test_directory_swapped_for_a_symlink_after_validation_is_refused(env, monkeypatch):
    c, src, tmp = env
    (src / "sous").mkdir()
    (src / "sous" / "f.csv").write_bytes(CSV)
    other = tmp / "ailleurs"
    other.mkdir()
    (other / "f.csv").write_bytes(b"x,y\n9,9\n")
    sid = connect(c, src)
    real_open = os.open

    def swapping_open(path, flags, *a, **k):
        if str(path).endswith(os.path.join("sous", "f.csv")):
            (src / "sous" / "f.csv").unlink()
            (src / "sous").rmdir()
            os.symlink(other, src / "sous")
        return real_open(path, flags, *a, **k)
    monkeypatch.setattr(paths.os, "open", swapping_open)
    r = importing(c, sid, path="sous/f.csv")
    assert r.status_code == 404
    assert any(a["details"].get("code") == "outside_root" for a in actions(tmp))


def test_roots_come_from_the_operator_only(env, monkeypatch):
    c, src, tmp = env
    bad = c.post("/workspace/sources", json={"type": "mounted_folder", "name": "x", "root": "/etc"}, headers=admin_session(c))
    assert bad.status_code == 400 and bad.json()["detail"].startswith("Cette racine")
    esc = tmp / "allowed" / "evasion"
    esc.symlink_to(tmp)                                          # un lien dans la racine autorisée qui sort
    assert c.post("/workspace/sources", json={"type": "mounted_folder", "name": "x", "root": str(esc)}, headers=admin_session(c)).status_code == 400
    monkeypatch.setenv("WORKSPACE_ALLOWED_ROOTS", "")            # liste vide = aucune source
    r = c.post("/workspace/sources", json={"type": "mounted_folder", "name": "x", "root": str(src)}, headers=admin_session(c))
    assert r.status_code == 400 and "WORKSPACE_ALLOWED_ROOTS" in r.json()["detail"]


# ── empreinte, versions, intégrité ───────────────────────────────────────────────────────────────────────────────

def test_import_records_sha256_and_a_change_creates_a_new_version(env):
    c, src, tmp = env
    sid = connect(c, src)
    v1 = importing(c, sid).json()["file"]
    assert v1["sha256"] == hashlib.sha256(CSV).hexdigest() and v1["version"] == 1
    again = importing(c, sid)
    assert again.status_code == 200 and again.json()["unchanged"] is True
    new = CSV + b"Dikhil,2024,7\n"
    (src / "chiffres.csv").write_bytes(new)
    v2 = importing(c, sid).json()["file"]
    assert v2["version"] == 2 and v2["sha256"] == hashlib.sha256(new).hexdigest() and v2["summary"]["rows"] == 3
    versions = {f["version"]: f for f in c.get(f"/workspace/sources/{sid}/files?all_versions=true", headers=VIEWER).json()["files"]}
    assert versions[1]["status"] == "Périmé" and versions[2]["status"] == "Indexé"
    assert c.get(f"/workspace/files/{v1['file_id']}/content", headers=VIEWER).content == CSV         # l'ancienne version reste lisible
    assert (tmp / "store" / str(sid) / v1["sha256"]).exists()


def test_copies_are_scoped_per_source(env):
    c, src, tmp = env
    s1 = connect(c, src)
    s2 = connect(c, src, name="Autre")
    importing(c, s1)
    importing(c, s2)
    assert (tmp / "store" / str(s1) / hashlib.sha256(CSV).hexdigest()).exists() and (tmp / "store" / str(s2) / hashlib.sha256(CSV).hexdigest()).exists()


def test_tampered_copy_is_refused_on_read_and_journalised(env):
    c, src, tmp = env
    sid = connect(c, src)
    f = importing(c, sid).json()["file"]
    p = tmp / "store" / str(sid) / f["sha256"]
    p.write_bytes(CSV + b"ALTERE")
    r = c.get(f"/workspace/files/{f['file_id']}/content", headers=VIEWER)
    assert r.status_code == 409 and b"ALTERE" not in r.content
    assert any(a["action"] == "workspace_integrity_failure" for a in actions(tmp))
    p.unlink()
    assert c.get(f"/workspace/files/{f['file_id']}/content", headers=VIEWER).status_code == 409


def test_download_headers_are_safe(env):
    c, src, _ = env
    sid = connect(c, src)
    f = importing(c, sid).json()["file"]
    r = c.get(f"/workspace/files/{f['file_id']}/content", headers=VIEWER)
    assert r.status_code == 200 and r.headers["x-content-type-options"] == "nosniff" and r.headers["cache-control"] == "no-store"
    assert r.headers["content-disposition"].startswith("attachment")


# ── cloud tiers désactivés ───────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("t", ["google_drive", "sharepoint", "onedrive"])
def test_third_party_connectors_do_not_exist_server_side_by_default(env, t, monkeypatch):
    c, src, tmp = env
    r = c.post("/workspace/sources", json={"type": t, "name": "x", "root": str(src)}, headers=admin_session(c))
    assert r.status_code == 400 and "désactivés" in r.json()["detail"]
    assert c.get("/workspace/status", headers=VIEWER).json()["third_party_enabled"] is False
    assert any(a["action"] == "workspace_third_party_refused" for a in actions(tmp))
    monkeypatch.setenv("WORKSPACE_ALLOW_THIRD_PARTY", "true")      # même activé : pas d'implémentation dans P-086a
    assert c.post("/workspace/sources", json={"type": t, "name": "x", "root": str(src)}, headers=admin_session(c)).status_code == 501


def test_unknown_connector_type_is_refused(env):
    c, src, _ = env
    assert c.post("/workspace/sources", json={"type": "ftp", "name": "x", "root": str(src)}, headers=admin_session(c)).status_code == 400


# ── fichiers hostiles : plafonds et statut Anomalies ─────────────────────────────────────────────────────────────

def test_hostile_files_become_anomalies_never_a_crash(env, monkeypatch):
    c, src, tmp = env
    sid = connect(c, src)
    from pypdf import PdfWriter
    w = PdfWriter()
    for _ in range(5):
        w.add_blank_page(100, 100)
    buf = io.BytesIO()
    w.write(buf)
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "x")
        z.writestr("xl/workbook.xml", b"0" * 5000)
    (src / "trop_de_pages.pdf").write_bytes(buf.getvalue())
    (src / "faux.pdf").write_bytes(b"%PDF-1.7 \x00\x01 pas un pdf")
    (src / "bombe.xlsx").write_bytes(zbuf.getvalue())
    (src / "faux.xlsx").write_bytes(b"pas un zip")
    (src / "inconnu.bin").write_bytes(b"\x00\x01")
    (src / "long.csv").write_bytes(b"a,b\n" + b"1,2\n" * 5000)
    (src / "ragged.csv").write_bytes(b"a,b\n1\n2,3,4\n")
    (src / "vide.csv").write_bytes(b"")
    monkeypatch.setattr(extract, "MAX_PAGES", 2)
    monkeypatch.setattr("app.audit_data.files.MAX_UNCOMPRESSED", 1000)
    for name in ("trop_de_pages.pdf", "faux.pdf", "bombe.xlsx", "faux.xlsx", "ragged.csv", "vide.csv"):
        r = importing(c, sid, path=name)
        assert r.status_code == 201, (name, r.text)
        f = r.json()["file"]
        assert f["status"] == "Anomalies" and f["anomalies"], name
    monkeypatch.setattr(extract, "MAX_ROWS", 100)
    assert importing(c, sid, path="long.csv").json()["file"]["status"] == "Anomalies"
    monkeypatch.setattr(extract, "MAX_ROWS", 1_000_000)
    monkeypatch.setattr(extract, "_timeout", lambda: -1000.0)                 # délai d'extraction dépassé
    (src / "long2.csv").write_bytes(b"a,b\n" + b"3,4\n" * 5000)
    r = importing(c, sid, path="long2.csv").json()["file"]
    assert r["status"] == "Anomalies" and "Délai" in r["anomalies"][0]
    assert any(a["action"] == "workspace_import" and a["details"]["status"] == "Anomalies" for a in actions(tmp))


def test_oversized_file_is_refused_before_it_is_stored(env, monkeypatch):
    c, src, tmp = env
    sid = connect(c, src)
    monkeypatch.setenv("WORKSPACE_MAX_FILE_MB", "1")
    (src / "gros.csv").write_bytes(b"a,b\n" + b"1,2\n" * 400_000)
    r = importing(c, sid, path="gros.csv")
    assert r.status_code == 413
    assert not list((tmp / "store").rglob(".tmp-*"))                           # aucun résidu
    assert not [p for p in (tmp / "store").rglob("*") if p.is_file()]


def test_xlsx_sdmx_and_pdf_text_are_indexed(env):
    import openpyxl
    from pypdf import PdfWriter
    c, src, _ = env
    sid = connect(c, src)
    wb = openpyxl.Workbook()
    wb.active.append(["region", "valeur"])
    wb.active.append(["Obock", 3])
    wb.save(src / "classeur.xlsx")
    (src / "sdmx.csv").write_text("STRUCTURE,STRUCTURE_ID,ACTION,REGION,OBS_VALUE\ndataflow,MIZANBI:X(1.0),I,Obock,5\n")
    assert importing(c, sid, path="classeur.xlsx").json()["file"]["summary"]["sheets"][0]["rows"] == 2
    f = importing(c, sid, path="sdmx.csv").json()["file"]
    assert f["kind"] == "sdmx" and f["status"] == "Indexé"
    w = PdfWriter()
    w.add_blank_page(100, 100)
    buf = io.BytesIO()
    w.write(buf)
    (src / "blanc.pdf").write_bytes(buf.getvalue())
    p = importing(c, sid, path="blanc.pdf").json()["file"]
    assert p["status"] == "Anomalies" and "OCR" in p["anomalies"][0]               # pas de texte : on le dit, on ne devine pas


# ── noms réservés, inventaire, aucun envoi à un modèle ──────────────────────────────────────────────────────────

def test_workspace_tables_are_reserved_like_audit_tables(env):
    import pandas as pd

    from app.data.duckdb_store import ReservedTableError
    store = DataStore()
    for name in ("workspace_sources", "workspace_files", "workspace_autre", "audit_x"):
        with pytest.raises(ReservedTableError):
            store.load_dataframe(name, pd.DataFrame({"a": [1]}))


def test_every_disk_access_goes_through_paths_py():
    pattern = re.compile(r"\bopen\(|os\.(open|scandir|listdir|walk|unlink|remove|rename|replace|mkdir|makedirs|stat|lstat|chmod)\b|"
                         r"\.(read_bytes|read_text|write_bytes|write_text|iterdir|glob|rglob|unlink|mkdir|exists|is_file|is_dir)\(|shutil|tempfile")
    offenders = {}
    for f in (ROOT / "app" / "workspace").glob("*.py"):
        if f.name == "paths.py":
            continue
        hits = pattern.findall(f.read_text(encoding="utf-8"))
        if hits:
            offenders[f.name] = hits
    assert not offenders, f"Accès disque hors paths.py : {offenders}"


def test_the_workspace_never_imports_a_model_client_or_the_network():
    for f in (ROOT / "app" / "workspace").glob("*.py"):
        src = f.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(from|import)\s+(app\.llm|app\.rag|httpx|requests|urllib|aiohttp|socket|openai|anthropic)", src, re.M), f.name


def test_a_model_client_that_receives_file_content_fails_the_test(env, monkeypatch):
    """Faux fournisseur : tout appel à un client de modèle pendant connexion, import, lecture ou liste fait échouer le test."""
    from app.llm import ollama_client
    called = []

    def boom(*a, **k):
        called.append(1)
        raise AssertionError("Un contenu de fichier a été envoyé à un modèle")
    for name in dir(ollama_client):
        obj = getattr(ollama_client, name)
        if isinstance(obj, type) and name.endswith("Client"):
            for meth in ("generate", "chat", "complete", "ask", "_post"):
                if hasattr(obj, meth):
                    monkeypatch.setattr(obj, meth, boom)
    c, src, _ = env
    sid = connect(c, src)
    f = importing(c, sid).json()["file"]
    c.get(f"/workspace/sources/{sid}/files", headers=EDITOR)
    c.get(f"/workspace/files/{f['file_id']}/content", headers=VIEWER)
    assert not called


# ── revue sécurité P-086a ────────────────────────────────────────────────────────────────────────────────────────

def test_only_csv_xlsx_pdf_are_copied_hidden_files_and_other_types_are_refused_before_any_copy(env):
    c, src, tmp = env
    sid = connect(c, src)
    for n in (".env", "id_rsa", "secrets.csv.bak", "notes.txt", ".cache.csv"):
        (src / n).write_bytes(b"SECRET")
        assert importing(c, sid, path=n).status_code == 404, n
    assert not [p for p in (tmp / "store").rglob("*") if p.is_file()]


def test_hard_links_and_fifos_are_refused(env):
    c, src, tmp = env
    sid = connect(c, src)
    outside = tmp / "dehors.csv"
    outside.write_bytes(b"a,b\n1,2\n")
    os.link(outside, src / "dur.csv")
    assert importing(c, sid, path="dur.csv").status_code == 404
    os.mkfifo(src / "tube.csv")
    assert importing(c, sid, path="tube.csv").status_code == 404
    codes = {a["details"].get("code") for a in actions(tmp) if a["action"] == "workspace_import_refused"}
    assert {"hardlink_refused", "not_regular"} <= codes


def test_a_root_removed_by_the_operator_stops_working(env, monkeypatch):
    c, src, tmp = env
    sid = connect(c, src)
    assert importing(c, sid).status_code == 201
    monkeypatch.setenv("WORKSPACE_ALLOWED_ROOTS", str(tmp / "autre"))
    assert importing(c, sid).status_code == 404
    assert c.get(f"/workspace/sources/{sid}/files", headers=EDITOR).json()["available"] == []


def test_system_roots_and_storage_overlap_are_refused(env, monkeypatch):
    c, src, tmp = env
    monkeypatch.setenv("WORKSPACE_ALLOWED_ROOTS", "/")
    assert paths.allowed_roots() == []
    monkeypatch.setenv("WORKSPACE_ALLOWED_ROOTS", str(tmp))
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp / "allowed" / "dossier" / "copies"))
    r = c.post("/workspace/sources", json={"type": "mounted_folder", "name": "x", "root": str(src)}, headers=admin_session(c))
    assert r.status_code == 400 and "stockage" in r.json()["detail"]


def test_non_ascii_file_names_download_without_error(env):
    c, src, _ = env
    sid = connect(c, src)
    (src / "تقرير_جيبوتي.csv").write_bytes(CSV)
    f = importing(c, sid, path="تقرير_جيبوتي.csv")
    assert f.status_code == 201
    r = c.get(f"/workspace/files/{f.json()['file']['file_id']}/content", headers=VIEWER)
    assert r.status_code == 200 and "filename*=UTF-8''" in r.headers["content-disposition"]


def test_storage_quota_is_enforced_and_leaves_no_residue(env, monkeypatch):
    c, src, tmp = env
    sid = connect(c, src)
    monkeypatch.setenv("WORKSPACE_MAX_TOTAL_MB", "1")
    (src / "un.csv").write_bytes(b"a,b\n" + b"1,2\n" * 200_000)
    assert importing(c, sid, path="un.csv").status_code == 201
    (src / "deux.csv").write_bytes(b"a,b\n" + b"3,4\n" * 200_000)
    assert importing(c, sid, path="deux.csv").status_code == 507
    assert not list((tmp / "store").rglob(".tmp-*"))


def test_creating_a_source_requires_a_named_session_not_a_key(env):
    c, src, _ = env
    r = c.post("/workspace/sources", json={"type": "mounted_folder", "name": "x", "root": str(src)}, headers=ADMIN)
    assert r.status_code == 403


def test_an_unreadable_name_is_ignored_in_the_disk_listing(env):
    c, src, _ = env
    sid = connect(c, src)
    try:
        open(os.path.join(os.fsencode(src), b"bad\xff.csv"), "wb").close()
    except OSError:
        pytest.skip("système de fichiers sans noms non UTF-8")
    assert c.get(f"/workspace/sources/{sid}/files", headers=EDITOR).status_code == 200
