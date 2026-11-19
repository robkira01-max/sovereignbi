"""Stockage DuckDB du pack Audit, volet import (P-074).

Tables : `audit_documents` (métadonnées + empreinte de l'original), `audit_quality_issues` (anomalies),
`audit_financial_records` (données normalisées, montants en DECIMAL(38,6), interrogeables et protégeables par ligne).
- Écriture : requêtes paramétrées sur la connexion du store. Lecture : `DataStore.execute` (sécurité par ligne, D-3),
  avec des valeurs validées (UUID, SHA-256, listes blanches), jamais du texte libre.
- Pas de PRIMARY KEY / UNIQUE sur les tables mises à jour (limites de DuckDB sur UPDATE indexé) : l'unicité est
  garantie par `LOCK` + vérification avant insertion (processus unique).
- Les originaux ne sont jamais modifiés ; les enregistrements d'un document ne sont jamais supprimés par ce module.
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone

import pandas as pd

from app.audit_data.normalize import Issue, Record

DOCS, ISSUES, RECORDS = "audit_documents", "audit_quality_issues", "audit_financial_records"
LOCK = threading.Lock()
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_SHA = re.compile(r"[0-9a-f]{64}")
_DOC_COLS = ("document_id", "sha256", "display_name", "kind", "size_bytes", "uploaded_by", "uploaded_at", "rows_total",
             "status", "imported_at", "imported_by", "rows_imported", "options_json", "summary_json")
_ISSUE_COLS = ("issue_id", "document_id", "severity", "code", "source_row", "field", "message", "raw_value", "status",
               "resolved_by", "resolved_at", "justification")


def valid_id(x: str) -> bool:
    return bool(_UUID.fullmatch(x or ""))


def now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def ensure_tables(store) -> None:
    store.con.execute(f"""CREATE TABLE IF NOT EXISTS {DOCS} (
        document_id VARCHAR, sha256 VARCHAR, display_name VARCHAR, kind VARCHAR, size_bytes BIGINT, uploaded_by VARCHAR,
        uploaded_at VARCHAR, rows_total INTEGER, status VARCHAR, imported_at VARCHAR, imported_by VARCHAR,
        rows_imported INTEGER, options_json VARCHAR, summary_json VARCHAR)""")
    store.con.execute(f"""CREATE TABLE IF NOT EXISTS {ISSUES} (
        issue_id VARCHAR, document_id VARCHAR, severity VARCHAR, code VARCHAR, source_row INTEGER, field VARCHAR,
        message VARCHAR, raw_value VARCHAR, status VARCHAR, resolved_by VARCHAR, resolved_at VARCHAR, justification VARCHAR)""")
    store.con.execute(f"""CREATE TABLE IF NOT EXISTS {RECORDS} (
        record_id VARCHAR, document_id VARCHAR, source_row INTEGER, entry_date DATE, account VARCHAR, label VARCHAR,
        reference VARCHAR, debit DECIMAL(38,6), credit DECIMAL(38,6), amount DECIMAL(38,6), currency VARCHAR,
        currency_source VARCHAR, fiscal_year INTEGER, has_error BOOLEAN)""")
    store.tables.add(RECORDS)          # interrogeable (et protégeable par une règle de sécurité par ligne)


def _rows(store, sql: str) -> list[dict]:
    cols, rows = store.execute(sql)
    return [dict(zip(cols, r, strict=True)) for r in rows]


# ── documents ────────────────────────────────────────────────────────────────

def find_by_hash(store, sha256: str) -> dict | None:
    if not _SHA.fullmatch(sha256 or ""):
        return None
    ensure_tables(store)
    r = _rows(store, f"SELECT {', '.join(_DOC_COLS)} FROM {DOCS} WHERE sha256 = '{sha256}'")
    return _doc(r[0]) if r else None


def get_document(store, document_id: str) -> dict | None:
    if not valid_id(document_id):
        return None
    ensure_tables(store)
    r = _rows(store, f"SELECT {', '.join(_DOC_COLS)} FROM {DOCS} WHERE document_id = '{document_id}'")
    return _doc(r[0]) if r else None


def _doc(row: dict) -> dict:
    row["options"] = json.loads(row.pop("options_json") or "null")
    row["summary"] = json.loads(row.pop("summary_json") or "null")
    return row


def list_documents(store, limit: int = 50, offset: int = 0) -> list[dict]:
    ensure_tables(store)
    limit, offset = max(1, min(int(limit), 200)), max(0, int(offset))
    cols = [c for c in _DOC_COLS if c not in ("options_json",)]
    rows = _rows(store, f"SELECT {', '.join(cols)} FROM {DOCS} ORDER BY uploaded_at DESC LIMIT {limit} OFFSET {offset}")
    for r in rows:
        r["summary"] = json.loads(r.pop("summary_json") or "null")
    return rows


def insert_document(store, *, sha256: str, display_name: str, kind: str, size: int, uploaded_by: str, rows_total: int) -> str:
    ensure_tables(store)
    doc_id = str(uuid.uuid4())
    store.con.execute(f"INSERT INTO {DOCS} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
        doc_id, sha256, display_name, kind, size, uploaded_by, now(), rows_total, "uploaded", None, None, None, None, None])
    return doc_id


def mark_imported(store, document_id: str, *, by: str, rows: int, options: dict, summary: dict, con=None) -> None:
    cur = (con or store.con).execute(
        f"UPDATE {DOCS} SET status = 'imported', imported_at = ?, imported_by = ?, rows_imported = ?, options_json = ?, summary_json = ? "
        f"WHERE document_id = ? AND status = 'uploaded'",
        [now(), by, rows, json.dumps(options, sort_keys=True), json.dumps(summary, sort_keys=True), document_id])
    if (cur.fetchone() or [0])[0] != 1:       # mise à jour sans effet = incohérence : la transaction s'annule
        raise RuntimeError("document non marqué comme importé")


# ── enregistrements et anomalies ─────────────────────────────────────────────

def insert_records(store, document_id: str, records: list[Record], con=None) -> None:
    ensure_tables(store)
    con = con or store.con
    if not records:
        return
    df = pd.DataFrame({
        "record_id": [f"{document_id}:{r.source_row}" for r in records],
        "document_id": document_id,
        "source_row": [r.source_row for r in records],
        "entry_date": [r.entry_date.isoformat() if r.entry_date else None for r in records],
        "account": [r.account for r in records], "label": [r.label for r in records],
        "reference": [r.reference for r in records],
        "debit": [None if r.debit is None else format(r.debit, "f") for r in records],
        "credit": [None if r.credit is None else format(r.credit, "f") for r in records],
        "amount": [None if r.amount is None else format(r.amount, "f") for r in records],
        "currency": [r.currency for r in records], "currency_source": [r.currency_source for r in records],
        "fiscal_year": pd.array([r.fiscal_year for r in records], dtype="Int64"),
        "has_error": [r.has_error for r in records],
    })
    con.register("_p074_df", df)
    try:
        con.execute(f"""INSERT INTO {RECORDS}
            SELECT record_id, document_id, source_row, CAST(entry_date AS DATE), account, label, reference,
                   CAST(debit AS DECIMAL(38,6)), CAST(credit AS DECIMAL(38,6)), CAST(amount AS DECIMAL(38,6)),
                   currency, currency_source, fiscal_year, has_error FROM _p074_df""")
    finally:
        con.unregister("_p074_df")


def insert_issues(store, document_id: str, issues: list[Issue], con=None) -> None:
    ensure_tables(store)
    con = con or store.con
    if not issues:
        return
    df = pd.DataFrame({
        "issue_id": [str(uuid.uuid4()) for _ in issues], "document_id": document_id,
        "severity": [i.severity for i in issues], "code": [i.code for i in issues],
        "source_row": pd.array([i.source_row for i in issues], dtype="Int64"), "field": [i.field for i in issues],
        "message": [i.message for i in issues], "raw_value": [i.raw_value for i in issues],
        "status": "open", "resolved_by": None, "resolved_at": None, "justification": None})
    con.register("_p074_iss", df)
    try:
        con.execute(f"INSERT INTO {ISSUES} SELECT {', '.join(_ISSUE_COLS)} FROM _p074_iss")
    finally:
        con.unregister("_p074_iss")


def list_issues(store, document_id: str, *, status: str | None = None, severity: str | None = None,
                limit: int = 100, offset: int = 0) -> list[dict]:
    if not valid_id(document_id):
        return []
    ensure_tables(store)
    where = [f"document_id = '{document_id}'"]
    if status in ("open", "resolved"):
        where.append(f"status = '{status}'")
    if severity in ("error", "warning"):
        where.append(f"severity = '{severity}'")
    limit, offset = max(1, min(int(limit), 500)), max(0, int(offset))
    return _rows(store, f"SELECT {', '.join(_ISSUE_COLS)} FROM {ISSUES} WHERE {' AND '.join(where)} "
                        f"ORDER BY source_row NULLS LAST, issue_id LIMIT {limit} OFFSET {offset}")


def issue_counts(store, document_id: str) -> dict:
    if not valid_id(document_id):
        return {}
    ensure_tables(store)
    rows = _rows(store, f"SELECT severity, status, count(*) AS n FROM {ISSUES} WHERE document_id = '{document_id}' GROUP BY 1, 2")
    out = {"open_errors": 0, "open_warnings": 0, "resolved_errors": 0, "resolved_warnings": 0}
    for r in rows:
        out[f"{r['status']}_{r['severity']}s"] = int(r["n"])
    return out


def get_issue(store, issue_id: str) -> dict | None:
    if not valid_id(issue_id):
        return None
    ensure_tables(store)
    r = _rows(store, f"SELECT {', '.join(_ISSUE_COLS)} FROM {ISSUES} WHERE issue_id = '{issue_id}'")
    return r[0] if r else None


def resolve_issue(store, issue_id: str, *, by: str, justification: str) -> bool:
    """True si l'anomalie était ouverte et vient d'être résolue (une anomalie résolue ne se « re-résout » pas)."""
    with LOCK:
        cur = store.con.execute(
            f"UPDATE {ISSUES} SET status = 'resolved', resolved_by = ?, resolved_at = ?, justification = ? "
            f"WHERE issue_id = ? AND status = 'open'", [by, now(), justification, issue_id])
        return (cur.fetchone() or [0])[0] == 1
