"""P-074 : validation des fichiers déposés (types réels, bombes ZIP, macros, noms hostiles, conservation)."""
from __future__ import annotations

import hashlib
import io
import os
import stat
import zipfile

import openpyxl
import pytest

from app.audit_data import files
from app.audit_data.files import FileRefused, safe_display_name, validate_upload

CSV = b"Date;Compte;Montant\n2026-01-05;601;100\n"


def xlsx_bytes(rows=(("Date", "Compte", "Montant"), ("2026-01-05", "601", 100))) -> bytes:
    wb = openpyxl.Workbook()
    for r in rows:
        wb.active.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def zip_with(members: dict[str, bytes], base: bytes | None = None) -> bytes:
    """Un xlsx valide auquel on ajoute des membres (ou une archive arbitraire si base=b'')."""
    buf = io.BytesIO()
    src = xlsx_bytes() if base is None else base
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if src:
            with zipfile.ZipFile(io.BytesIO(src)) as old:
                for i in old.infolist():
                    z.writestr(i.filename, old.read(i.filename))
        for name, content in members.items():
            z.writestr(name, content)
    return buf.getvalue()


def refused(name, data) -> str:
    with pytest.raises(FileRefused) as e:
        validate_upload(name, data)
    return e.value.code


# ── cas valides ─────────────────────────────────────────────────────────────

def test_valid_csv_and_xlsx_are_accepted_with_their_sha256():
    v = validate_upload("compta.csv", CSV)
    assert (v.kind, v.sha256, v.size) == ("csv", hashlib.sha256(CSV).hexdigest(), len(CSV))
    x = xlsx_bytes()
    assert validate_upload("Compta 2026.XLSX", x).kind == "xlsx"


# ── type réel ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", ["a.xls", "a.xlsm", "a.exe", "a.zip", "a.pdf", "a.csv.exe", "a", "a.", ".csv.bak", "a.xlsx.zip"])
def test_unsupported_extensions_are_refused(name):
    assert refused(name, CSV) == "unsupported_type"


@pytest.mark.parametrize("head,label", [
    (b"MZ\x90\x00", "exécutable"), (b"\x7fELF\x02", "exécutable"), (b"#!/bin/sh\nid", "script"), (b"%PDF-1.7", "PDF"),
    (b"PK\x03\x04", "archive"), (b"\xd0\xcf\x11\xe0", "OLE"), (b"\x1f\x8b\x08", "gzip"), (b"\x89PNG\r\n", "image"),
])
def test_files_that_are_not_csv_are_refused_even_under_a_csv_name(head, label):
    assert refused("innocent.csv", head + b"rest of file\n1;2\n") == "content_mismatch"


def test_html_xml_binary_and_empty_content_are_refused():
    assert refused("a.csv", b"<html><body>x</body></html>") == "content_mismatch"
    assert refused("a.csv", b"\xef\xbb\xbf  <?xml version='1.0'?>") == "content_mismatch"
    assert refused("a.csv", b"Date;Compte\n1;2\x00\x01\n") == "binary_content"
    assert refused("a.csv", b"") == "empty_file"
    assert refused("a.xlsx", b"") == "empty_file"


def test_csv_masquerading_as_xlsx_or_the_reverse_is_refused():
    assert refused("a.xlsx", CSV) == "content_mismatch"
    assert refused("a.csv", xlsx_bytes()) == "content_mismatch"


def test_size_limit(monkeypatch):
    monkeypatch.setattr(files, "MAX_BYTES", 100)
    assert refused("a.csv", b"x" * 101) == "too_large"
    assert validate_upload("a.csv", b"a;b\n1;2\n").kind == "csv"


# ── archives XLSX hostiles ─────────────────────────────────────────────────

def test_zip_bomb_by_compression_ratio_is_refused():
    assert refused("a.xlsx", zip_with({"xl/worksheets/big.xml": b"0" * (6 * 1024 * 1024)})) == "zip_bomb"


def test_zip_bomb_by_total_uncompressed_size_is_refused(monkeypatch):
    monkeypatch.setattr(files, "MAX_UNCOMPRESSED", 1000)
    assert refused("a.xlsx", xlsx_bytes()) == "zip_bomb"


def test_too_many_members_is_refused(monkeypatch):
    monkeypatch.setattr(files, "MAX_ZIP_MEMBERS", 3)
    assert refused("a.xlsx", xlsx_bytes()) == "zip_too_many_members"


@pytest.mark.parametrize("name", ["../evil.xml", "/etc/passwd", "xl/../../evil", "a\\b.xml"])
def test_unsafe_internal_paths_are_refused(name):
    assert refused("a.xlsx", zip_with({name: b"x"})) == "zip_unsafe_path"


@pytest.mark.parametrize("member,code", [
    ("xl/vbaProject.bin", "macros_refused"), ("xl/externalLinks/externalLink1.xml", "external_links_refused"),
    ("xl/embeddings/oleObject1.bin", "embedded_objects_refused"), ("xl/activeX/activeX1.xml", "embedded_objects_refused"),
])
def test_macros_external_links_and_embedded_objects_are_refused(member, code):
    assert refused("a.xlsx", zip_with({member: b"x"})) == code


def test_arbitrary_or_corrupt_zip_is_not_an_xlsx():
    assert refused("a.xlsx", zip_with({"readme.txt": b"hi"}, base=b"")) == "not_an_xlsx"
    assert refused("a.xlsx", b"PK\x03\x04" + b"\x00" * 40) == "not_a_zip"
    assert refused("a.xlsx", xlsx_bytes()[:-30]) in ("not_a_zip",)


# ── noms ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("../../etc/passwd.csv", "passwd.csv"), ("C:\\Users\\x\\budget.csv", "budget.csv"), ("a\x00b\nc.csv", "abc.csv"),
    ("gnp\u202ecsv.exe", "gnpcsv.exe"), ("...hidden.csv", "hidden.csv"), (None, "document"), ("", "document"),
    ("budget   2026.csv", "budget 2026.csv"),
])
def test_display_names_are_sanitised(raw, expected):
    assert safe_display_name(raw) == expected


def test_display_name_is_length_bounded():
    assert len(safe_display_name("x" * 500 + ".csv")) == 120


def test_bidi_trick_extension_cannot_hide_an_unsupported_type():
    # « budget‮vsc.exe » (RLO) s'affiche « budgetexe.csv » : l'extension réelle est vérifiée APRÈS assainissement
    assert refused("budget\u202evsc.exe", CSV) == "unsupported_type"


# ── conservation ────────────────────────────────────────────────────────────

@pytest.fixture()
def docs(tmp_path, monkeypatch):
    monkeypatch.setenv("SOVEREIGN_AUDIT_DOCS_DIR", str(tmp_path / "docs"))
    return tmp_path / "docs"


def test_original_is_stored_by_hash_read_only_and_never_overwritten(docs):
    v = validate_upload("../../x.csv", CSV)
    p = files.store_original(v, CSV)
    assert p.parent == docs.resolve() and p.name == f"{v.sha256}.csv"
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o400
    assert files.store_original(v, CSV) == p                       # idempotent
    assert files.read_original(v.sha256, "csv") == CSV
    os.chmod(p, 0o600)
    p.write_bytes(b"corrompu")
    with pytest.raises(FileRefused) as e:                          # on ne réécrit pas par-dessus un original altéré
        files.store_original(v, CSV)
    assert e.value.code == "stored_original_corrupt" and p.read_bytes() == b"corrompu"


@pytest.mark.parametrize("sha,kind", [("../../etc/passwd", "csv"), ("a" * 63, "csv"), ("A" * 64, "csv"), ("a" * 64, "exe"), ("a" * 64 + "/x", "csv")])
def test_original_path_rejects_anything_but_a_hash(docs, sha, kind):
    with pytest.raises(ValueError):
        files.original_path(sha, kind)
    assert files.read_original(sha, kind) is None


def test_stale_tmp_file_does_not_block_a_deposit(docs):
    v = validate_upload("a.csv", CSV)
    d = files.original_path(v.sha256, v.kind).parent
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{v.sha256}.csv.tmp").write_bytes(b"reste d'un crash")
    assert files.store_original(v, CSV).read_bytes() == CSV
    assert [p.name for p in d.iterdir() if p.name.endswith(".tmp")] == [f"{v.sha256}.csv.tmp"]


def test_small_member_with_extreme_ratio_is_refused():
    assert refused("a.xlsx", zip_with({"xl/worksheets/x.xml": b"0" * (3 * 1024 * 1024)})) == "zip_bomb"
