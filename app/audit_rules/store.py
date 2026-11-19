"""Stockage des exécutions de règles et des signalements (P-075). Tables réservées (invisibles de l'IA et de l'upload)."""
from __future__ import annotations

import json
import re
import uuid

from app.audit_data.repo import _rows, now, valid_id

RUNS, FINDINGS = "audit_rule_runs", "audit_findings"
_RUN_COLS = ("run_id", "document_id", "document_sha256", "created_by", "created_at", "ruleset_hash", "summary_json")
_FIND_COLS = ("finding_id", "run_id", "rule_code", "rule_version", "document_id", "severity", "indicative", "status",
              "summary", "source_rows", "amount", "details_json", "created_at", "seq")


def ensure_tables(store) -> None:
    store.con.execute(f"""CREATE TABLE IF NOT EXISTS {RUNS} (run_id VARCHAR, document_id VARCHAR, document_sha256 VARCHAR,
        created_by VARCHAR, created_at VARCHAR, ruleset_hash VARCHAR, summary_json VARCHAR)""")
    store.con.execute(f"""CREATE TABLE IF NOT EXISTS {FINDINGS} (finding_id VARCHAR, run_id VARCHAR, rule_code VARCHAR,
        rule_version INTEGER, document_id VARCHAR, severity VARCHAR, indicative BOOLEAN, status VARCHAR, summary VARCHAR,
        source_rows VARCHAR, amount VARCHAR, details_json VARCHAR, created_at VARCHAR, seq INTEGER)""")


def new_run_id() -> str:
    return str(uuid.uuid4())


def save_run(store, *, run_id: str, doc: dict, created_by: str, ruleset_hash: str, summary: dict, findings: list[tuple[object, dict]]) -> None:
    """Un run et tous ses signalements dans une transaction (tout ou rien). `findings` = (Rule, dict)."""
    ensure_tables(store)
    ts = now()
    cur = store.con.cursor()
    cur.execute("BEGIN TRANSACTION")
    try:
        cur.execute(f"INSERT INTO {RUNS} VALUES (?,?,?,?,?,?,?)",
                    [run_id, doc["document_id"], doc["sha256"], created_by, ts, ruleset_hash, json.dumps(summary, sort_keys=True)])
        for seq, (rule, f) in enumerate(findings):
            cur.execute(f"INSERT INTO {FINDINGS} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
                str(uuid.uuid4()), run_id, rule.code, rule.version, doc["document_id"], rule.severity, rule.indicative,
                "to_review", f["summary"], ",".join(map(str, f["source_rows"])), f["amount"], f["details"], ts, seq])
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise
    finally:
        cur.close()


def get_run(store, run_id: str, *, actor: str, is_admin: bool) -> dict | None:
    if not valid_id(run_id):
        return None
    ensure_tables(store)
    r = _rows(store, f"SELECT {', '.join(_RUN_COLS)} FROM {RUNS} WHERE run_id = '{run_id}'")
    if not r or (not is_admin and r[0]["created_by"] != actor):
        return None                                            # 404 identique : on ne révèle pas l'existence
    r[0]["summary"] = json.loads(r[0].pop("summary_json"))
    return r[0]


def list_findings(store, run_id: str, *, rule_code: str | None, severity: str | None, limit: int, offset: int) -> list[dict]:
    ensure_tables(store)
    where = [f"run_id = '{run_id}'"] if valid_id(run_id) else ["FALSE"]
    if rule_code:
        if not re.fullmatch(r"AUD[0-9]{3}", rule_code):
            return []
        where.append(f"rule_code = '{rule_code}'")
    if severity in ("info", "warning"):
        where.append(f"severity = '{severity}'")
    limit, offset = max(1, min(int(limit), 500)), max(0, int(offset))
    rows = _rows(store, f"SELECT {', '.join(_FIND_COLS)} FROM {FINDINGS} WHERE {' AND '.join(where)} "
                        f"ORDER BY rule_code, seq LIMIT {limit} OFFSET {offset}")
    for r in rows:
        r["source_rows"] = [int(x) for x in r["source_rows"].split(",") if x]
        r["details"] = json.loads(r.pop("details_json"))
        r.pop("seq", None)
    return rows
