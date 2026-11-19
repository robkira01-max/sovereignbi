"""P-071 : vérification d'intégrité du journal d'audit chaîné — ce qu'elle détecte, et ce qu'elle ne détecte pas."""
from __future__ import annotations

import json
import threading

import pytest
from fastapi.testclient import TestClient

from app import feedback
from app.feedback import record_audit, verify_audit_chain

ADMIN = {"X-Api-Key": "test-admin-key-sprint3"}
EDITOR = {"X-Api-Key": "test-editor-key-s6"}


@pytest.fixture()
def log(tmp_path):
    p = tmp_path / "audit.jsonl"
    for i in range(6):
        record_audit(f"action_{i}", {"n": i, "texte": "é"}, path=p)
    return p


def lines(p):
    return p.read_text(encoding="utf-8").splitlines()


def write(p, ls):
    p.write_text("\n".join(ls) + "\n", encoding="utf-8")


def mutate(raw, **changes):
    d = json.loads(raw)
    d.update(changes)
    return json.dumps(d, ensure_ascii=False)


def rehash(d):
    """Ce que ferait quelqu'un qui connaît l'algorithme (la chaîne n'est pas signée)."""
    import hashlib
    return hashlib.sha256((d["prev"] + json.dumps({"timestamp": d["timestamp"], "action": d["action"], "details": d["details"]},
                                                  ensure_ascii=False, sort_keys=True)).encode()).hexdigest()


# ── ce qui est détecté ──────────────────────────────────────────────────────

def test_intact_chain_is_valid_and_reports_entries_and_head(log):
    r = verify_audit_chain(log)
    assert r.valid and r.entries == 6 and r.first_break is None
    assert r.head == json.loads(lines(log)[-1])["hash"]


def test_missing_or_empty_file_is_valid_with_zero_entries(tmp_path):
    assert verify_audit_chain(tmp_path / "absent.jsonl").entries == 0
    (tmp_path / "e.jsonl").write_text("\n\n")
    r = verify_audit_chain(tmp_path / "e.jsonl")
    assert r.valid and r.entries == 0 and r.head == ""


def test_modified_content_is_detected_at_that_line(log):
    ls = lines(log)
    d = json.loads(ls[2]); d["details"]["n"] = 999
    ls[2] = json.dumps(d, ensure_ascii=False)
    write(log, ls)
    r = verify_audit_chain(log)
    assert not r.valid and r.first_break["line"] == 3 and r.entries == 2


def test_modified_content_and_hash_of_a_middle_line_is_caught_on_the_next_line(log):
    ls = lines(log)
    d = json.loads(ls[2]); d["details"]["n"] = 999
    d["hash"] = rehash({**d, "prev": json.loads(ls[1])["hash"]})
    ls[2] = json.dumps(d, ensure_ascii=False)
    write(log, ls)
    r = verify_audit_chain(log)
    assert not r.valid and r.first_break["line"] == 4


def test_deleted_middle_entry_is_detected(log):
    ls = lines(log); del ls[3]; write(log, ls)
    assert verify_audit_chain(log).first_break["line"] == 4


def test_deleted_first_entry_is_detected(log):
    ls = lines(log); del ls[0]; write(log, ls)
    r = verify_audit_chain(log)
    assert not r.valid and r.first_break["line"] == 1


def test_inserted_forged_entry_is_detected(log):
    ls = lines(log)
    ls.insert(3, json.dumps({"timestamp": "2026-01-01T00:00:00+00:00", "action": "forged", "details": {}, "hash": "a" * 64}))
    write(log, ls)
    assert verify_audit_chain(log).first_break["line"] == 4


def test_reordered_entries_are_detected(log):
    ls = lines(log); ls[1], ls[2] = ls[2], ls[1]; write(log, ls)
    assert not verify_audit_chain(log).valid


@pytest.mark.parametrize("bad,reason", [
    ("pas du json", "illisible"),
    (json.dumps({"timestamp": "t", "action": "a", "details": {}}), "champs"),
    (json.dumps({"timestamp": "t", "action": "a", "details": {}, "hash": "x" * 64, "extra": 1}), "champs"),
    (json.dumps({"timestamp": "t", "action": "a", "details": {}, "hash": "ZZ"}), "mal formée"),
    (json.dumps([1, 2]), "champs"),
])
def test_malformed_lines_are_reported_with_a_reason(log, bad, reason):
    ls = lines(log); ls[4] = bad; write(log, ls)
    r = verify_audit_chain(log)
    assert not r.valid and r.first_break["line"] == 5 and reason in r.first_break["reason"]


def test_blank_lines_are_ignored(log):
    ls = lines(log); ls.insert(2, ""); ls.append("   "); write(log, ls)
    assert verify_audit_chain(log).valid


def test_the_report_never_contains_entry_content(log):
    ls = lines(log)
    d = json.loads(ls[2]); d["details"]["secret"] = "VALEUR-CONFIDENTIELLE"; ls[2] = json.dumps(d)
    write(log, ls)
    assert "VALEUR-CONFIDENTIELLE" not in json.dumps(verify_audit_chain(log).__dict__)


# ── ce qui n'est PAS détecté (limites documentées, verrouillées par des tests) ──

def test_known_limit_truncating_the_last_entries_is_invisible_without_an_anchor(log):
    ls = lines(log)[:3]; write(log, ls)
    r = verify_audit_chain(log)
    assert r.valid and r.entries == 3                        # la chaîne restante est cohérente : rien à signaler


def test_an_anchor_noted_earlier_exposes_the_truncation(log):
    before = verify_audit_chain(log)
    write(log, lines(log)[:3])
    r = verify_audit_chain(log, anchor_entries=before.entries, anchor_hash=before.head)
    assert not r.valid and r.anchor_checked and r.anchor_ok is False


def test_an_anchor_stays_valid_when_new_entries_are_appended(log):
    before = verify_audit_chain(log)
    record_audit("later", {"x": 1}, path=log)
    r = verify_audit_chain(log, anchor_entries=before.entries, anchor_hash=before.head)
    assert r.valid and r.anchor_ok is True and r.entries == before.entries + 1


def test_an_anchor_detects_a_rewritten_history(log):
    before = verify_audit_chain(log)
    ls = lines(log)
    prev = ""
    out = []
    for raw in ls:                                            # réécriture complète et cohérente d'un attaquant qui connaît l'algorithme
        d = json.loads(raw); d["details"]["n"] = 0
        d["hash"] = rehash({**d, "prev": prev}); prev = d["hash"]
        out.append(json.dumps(d, ensure_ascii=False))
    write(log, out)
    assert verify_audit_chain(log).valid                      # limite : la chaîne seule ne le voit pas
    r = verify_audit_chain(log, anchor_entries=before.entries, anchor_hash=before.head)
    assert not r.valid and r.anchor_ok is False               # … l'ancrage externe, si


def test_anchor_beyond_the_log_or_with_a_wrong_hash_fails(log):
    assert verify_audit_chain(log, anchor_entries=99, anchor_hash="a" * 64).anchor_ok is False
    assert verify_audit_chain(log, anchor_entries=3, anchor_hash="a" * 64).anchor_ok is False
    assert verify_audit_chain(log, anchor_entries=0).anchor_ok is True


# ── concurrence ─────────────────────────────────────────────────────────────

def test_verifying_while_others_write_never_raises_a_false_alarm(tmp_path):
    p = tmp_path / "c.jsonl"
    stop = threading.Event()
    bad = []

    def writer(k):
        for i in range(60):
            record_audit("w", {"k": k, "i": i}, path=p)

    def verifier():
        while not stop.is_set():
            r = verify_audit_chain(p)
            if not r.valid:
                bad.append(r.first_break)

    ws = [threading.Thread(target=writer, args=(k,)) for k in range(4)]
    v = threading.Thread(target=verifier)
    v.start(); [w.start() for w in ws]; [w.join() for w in ws]; stop.set(); v.join()
    assert not bad, bad[:2]
    r = verify_audit_chain(p)
    assert r.valid and r.entries == 240


# ── route ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app.main import app
    p = tmp_path / "audit.jsonl"
    monkeypatch.setattr(feedback, "AUDIT_PATH", p)
    for i in range(3):
        record_audit(f"a{i}", {"i": i}, path=p)
    with TestClient(app) as c:
        yield c, p
    app.state.active_sector_id = None
    app.state.active_semantic_text = None


def test_route_is_admin_only(client):
    c, _ = client
    assert c.get("/audit/verify").status_code == 401
    assert c.get("/audit/verify", headers=EDITOR).status_code == 403


def test_route_reports_validity_and_the_limits(client):
    c, p = client
    r = c.get("/audit/verify", headers=ADMIN).json()
    assert r["valid"] is True and r["entries"] == 3 and r["first_break"] is None and len(r["head"]) == 64
    assert "ne détecte pas" in r["limits"] and "ancrage" in r["limits"]
    ls = lines(p); ls[1] = mutate(ls[1], action="falsifie"); write(p, ls)
    r = c.get("/audit/verify", headers=ADMIN).json()
    assert r["valid"] is False and r["first_break"]["line"] == 2


def test_route_audits_the_verification_itself_without_content(client):
    c, p = client
    c.get("/audit/verify", headers=ADMIN)
    last = json.loads(lines(p)[-1])
    assert last["action"] == "audit_verified" and {k: v for k, v in last["details"].items() if k not in ("auth_method", "key_ref")} == {"valid": True, "entries": 3}
    assert verify_audit_chain(p).valid


def test_route_anchor_flow_end_to_end(client):
    c, p = client
    first = c.get("/audit/verify", headers=ADMIN).json()
    anchor = {"anchor_entries": first["entries"], "anchor_hash": first["head"]}
    assert c.get("/audit/verify", params=anchor, headers=ADMIN).json()["anchor_ok"] is True
    write(p, lines(p)[:2])
    r = c.get("/audit/verify", params=anchor, headers=ADMIN).json()
    assert r["valid"] is False and r["anchor_ok"] is False


@pytest.mark.parametrize("params", [{"anchor_entries": 3}, {"anchor_hash": "a" * 64}, {"anchor_entries": 3, "anchor_hash": "XYZ"},
                                    {"anchor_entries": -1, "anchor_hash": "a" * 64}, {"anchor_entries": "x"}, {"anchor_hash": "a" * 65}])
def test_route_rejects_incomplete_or_malformed_anchors(client, params):
    c, _ = client
    assert c.get("/audit/verify", params=params, headers=ADMIN).status_code == 422


def test_real_writer_and_verifier_agree_on_a_long_log(tmp_path):
    p = tmp_path / "long.jsonl"
    for i in range(300):
        record_audit("x", {"i": i, "é": "ü" * (i % 5)}, path=p)
    assert verify_audit_chain(p).entries == 300 and verify_audit_chain(p).valid
