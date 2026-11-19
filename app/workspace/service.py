"""Sources et fichiers de l'espace de travail (P-086a). Tables `workspace_*` : réservées, jamais créables par un upload.

Lectures de lignes : `DataStore.execute` (sécurité par ligne). Écritures : connexion directe, uniquement ici (inventaire).
Aucune colonne d'identifiants : le seul connecteur (dossier monté) n'en a pas besoin."""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone

from app.audit_data.files import safe_display_name
from app.security.actor import audit_soft, audit_strict
from app.security.rbac import ROLES
from app.workspace import extract, paths

SOURCES, FILES = "workspace_sources", "workspace_files"
WORKSPACE_NAMESPACE = "workspace_"
TYPE_MOUNTED = "mounted_folder"
THIRD_PARTY_TYPES = frozenset({"google_drive", "sharepoint", "onedrive"})
_lock = threading.Lock()


class WorkspaceError(Exception):
    def __init__(self, status: int, message: str, code: str = "workspace_error") -> None:
        super().__init__(message)
        self.status, self.code = status, code


def third_party_allowed() -> bool:
    return os.environ.get("WORKSPACE_ALLOW_THIRD_PARTY", "false").strip().lower() in ("1", "true", "yes")


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def ensure_tables(store) -> None:
    store.con.execute(f"""CREATE TABLE IF NOT EXISTS {SOURCES} (
        source_id INTEGER, type VARCHAR, name VARCHAR, root VARCHAR, mode VARCHAR, min_role VARCHAR,
        enabled_by VARCHAR, state VARCHAR, created_at VARCHAR)""")
    store.con.execute(f"""CREATE TABLE IF NOT EXISTS {FILES} (
        file_id VARCHAR, source_id INTEGER, rel_path VARCHAR, size_bytes BIGINT, sha256 VARCHAR, version INTEGER,
        status VARCHAR, summary_json VARCHAR, imported_by VARCHAR, imported_at VARCHAR)""")


def _rows(store, sql: str) -> list[dict]:
    cols, rows = store.execute(sql)
    return [dict(zip(cols, r, strict=True)) for r in rows]


def _q(v: str) -> str:
    return "'" + str(v).replace("'", "''") + "'"


# ── sources ──────────────────────────────────────────────────────────────────────────────────────────────────────

def create_source(store, *, type_: str, name: str, root: str, min_role: str, actor: str) -> dict:
    if type_ in THIRD_PARTY_TYPES:
        audit_soft("workspace_third_party_refused", type=type_, actor=actor, enabled=third_party_allowed())
        if not third_party_allowed():
            raise WorkspaceError(400, "Les connecteurs de cloud tiers sont désactivés sur ce serveur (WORKSPACE_ALLOW_THIRD_PARTY).", "third_party_disabled")
        raise WorkspaceError(501, "Ce type de connecteur n'est pas encore implémenté.", "not_implemented")
    if type_ != TYPE_MOUNTED:
        raise WorkspaceError(400, "Type de connecteur inconnu.", "unknown_type")
    if min_role not in ROLES:
        raise WorkspaceError(422, "Rôle minimal invalide.", "invalid_role")
    try:
        real = paths.validate_root(root)
    except paths.PathRefused as e:
        audit_soft("workspace_path_refused", where="create_source", code=e.code, actor=actor, path=str(root)[:200])
        raise WorkspaceError(400, str(e), e.code) from None
    with _lock:
        sid = (_rows(store, f"SELECT coalesce(max(source_id),0)+1 AS n FROM {SOURCES}")[0]["n"])
        audit_strict("workspace_source_created", source_id=sid, type=type_, name=name[:80], min_role=min_role, actor=actor)
        store.con.execute(f"INSERT INTO {SOURCES} VALUES (?,?,?,?,?,?,?,?,?)",
                          [sid, type_, name, real, "read_only", min_role, actor, "active", _now()])
    return get_source(store, sid)


def get_source(store, source_id: int) -> dict | None:
    r = _rows(store, f"SELECT * FROM {SOURCES} WHERE source_id = {int(source_id)}")
    return r[0] if r else None


def visible(src: dict | None, role: str) -> bool:
    """Droits hérités du dossier : rôle suffisant ET source active (l'administrateur voit aussi les sources désactivées)."""
    if src is None or ROLES.get(role, 0) < ROLES[src["min_role"]]:
        return False
    return src["state"] == "active" or role == "admin"


def public_source(src: dict, role: str) -> dict:
    out = {k: src[k] for k in ("source_id", "type", "name", "mode", "min_role", "state", "created_at")}
    if role == "admin":
        out["root"], out["enabled_by"] = src["root"], src["enabled_by"]      # chemin du serveur : administrateur seulement
    return out


def list_sources(store, role: str) -> list[dict]:
    return [public_source(s, role) for s in _rows(store, f"SELECT * FROM {SOURCES} ORDER BY source_id") if visible(s, role)]


def set_state(store, source_id: int, state: str, actor: str) -> dict:
    if state not in ("active", "disabled"):
        raise WorkspaceError(422, "État invalide.", "invalid_state")
    if get_source(store, source_id) is None:
        raise WorkspaceError(404, "Ressource introuvable.", "not_found")
    audit_strict("workspace_source_state", source_id=source_id, state=state, actor=actor)
    store.con.execute(f"UPDATE {SOURCES} SET state = ? WHERE source_id = ?", [state, int(source_id)])
    return get_source(store, source_id)


# ── fichiers ─────────────────────────────────────────────────────────────────────────────────────────────────────

def _file_public(r: dict, role: str) -> dict:
    meta = json.loads(r["summary_json"] or "{}")
    out = {"file_id": r["file_id"], "path": r["rel_path"], "version": r["version"], "size_bytes": r["size_bytes"],
           "sha256": r["sha256"], "status": r["status"], "imported_at": r["imported_at"],
           "kind": meta.get("kind"), "summary": meta.get("summary", {}), "anomalies": meta.get("anomalies", [])}
    if role == "admin":
        out["imported_by"] = r["imported_by"]
    return out


def list_files(store, source_id: int, role: str, *, all_versions: bool = False) -> list[dict]:
    rows = _rows(store, f"SELECT * FROM {FILES} WHERE source_id = {int(source_id)} ORDER BY rel_path, version DESC")
    if not all_versions:
        seen, latest = set(), []
        for r in rows:
            if r["rel_path"] not in seen:
                seen.add(r["rel_path"])
                latest.append(r)
        rows = latest
    return [_file_public(r, role) for r in rows]


def available_on_disk(store, src: dict) -> list[dict]:
    try:
        paths.validate_root(src["root"])
    except paths.PathRefused:
        return []
    imported = {(f["path"]): f["sha256"] for f in list_files(store, src["source_id"], "admin")}
    return [{"path": e["path"], "size_bytes": e["size"], "imported": e["path"] in imported} for e in paths.list_source(src["root"])]


def get_file(store, file_id: str) -> dict | None:
    try:
        uuid.UUID(file_id)
    except (ValueError, AttributeError, TypeError):
        return None
    r = _rows(store, f"SELECT * FROM {FILES} WHERE file_id = {_q(file_id)}")
    return r[0] if r else None


ALLOWED_EXT = (".csv", ".xlsx", ".pdf")


def _refuse(src: dict, rel, actor: str, code: str, where: str = "import") -> None:
    """Refus uniforme côté client (404, aucun oracle d'existence) ; le code précis reste dans le journal."""
    audit_soft("workspace_import_refused", source_id=src["source_id"], code=code, where=where, actor=actor,
               path=repr(str(rel)[:200]))
    raise WorkspaceError(404, "Fichier introuvable.", "not_found")


def import_file(store, src: dict, rel: str, actor: str, role: str) -> dict:
    """Copie figée + empreinte + version. Même contenu = rien de nouveau ; contenu changé = nouvelle version, l'ancienne reste (Périmé).

    L'indexation (potentiellement longue) se fait HORS du verrou : le verrou ne couvre que le calcul de version et l'écriture."""
    try:
        paths.validate_root(src["root"])             # la racine doit rester autorisée par l'opérateur à CHAQUE usage
        rel = paths.validate_rel(rel)
        if not rel.lower().endswith(ALLOWED_EXT) or any(part.startswith(".") for part in rel.split("/")):
            raise paths.PathRefused("type_refused", "Type de fichier non autorisé.")
        sha, size = paths.copy_from_source(src["root"], rel, src["source_id"])
    except paths.PathRefused as e:
        _refuse(src, rel, actor, e.code)
    except paths.TooLarge:
        audit_soft("workspace_import_refused", source_id=src["source_id"], code="too_large", path=repr(str(rel)[:200]), actor=actor)
        raise WorkspaceError(413, "Fichier trop volumineux.", "too_large") from None
    except paths.QuotaExceeded:
        audit_soft("workspace_import_refused", source_id=src["source_id"], code="quota", path=repr(str(rel)[:200]), actor=actor)
        raise WorkspaceError(507, "Quota de stockage atteint : contactez l'administrateur.", "quota") from None
    with _lock:
        prev = _rows(store, f"SELECT * FROM {FILES} WHERE source_id = {int(src['source_id'])} AND rel_path = {_q(rel)} ORDER BY version DESC LIMIT 1")
        if prev and prev[0]["sha256"] == sha:
            return {"unchanged": True, "file": _file_public(prev[0], role)}
    try:
        res = extract.index_bytes(rel, paths.read_copy(src["source_id"], sha))      # relit la copie : empreinte recalculée
    except paths.IntegrityError:
        audit_soft("workspace_integrity_failure", source_id=src["source_id"], sha256=sha, actor=actor, where="import")
        raise WorkspaceError(409, "Copie altérée pendant l'import : refusé.", "integrity") from None
    with _lock:
        prev = _rows(store, f"SELECT * FROM {FILES} WHERE source_id = {int(src['source_id'])} AND rel_path = {_q(rel)} ORDER BY version DESC LIMIT 1")
        if prev and prev[0]["sha256"] == sha:
            return {"unchanged": True, "file": _file_public(prev[0], role)}
        version = (prev[0]["version"] + 1) if prev else 1
        fid = str(uuid.uuid4())
        audit_strict("workspace_import", source_id=src["source_id"], file_id=fid, path=rel[:200], sha256=sha, version=version,
                     status=res.status, anomalies=len(res.anomalies), actor=actor)
        if prev:
            store.con.execute(f"UPDATE {FILES} SET status = 'Périmé' WHERE source_id = ? AND rel_path = ?", [int(src["source_id"]), rel])
        meta = json.dumps({"kind": res.kind, "summary": res.summary, "anomalies": res.anomalies}, ensure_ascii=False)
        store.con.execute(f"INSERT INTO {FILES} VALUES (?,?,?,?,?,?,?,?,?,?)",
                          [fid, int(src["source_id"]), rel, size, sha, version, res.status, meta, actor, _now()])
    return {"unchanged": False, "file": _file_public(get_file(store, fid), role)}


def read_file_content(store, f: dict, actor: str) -> tuple[bytes, str]:
    try:
        data = paths.read_copy(f["source_id"], f["sha256"])
    except paths.IntegrityError:
        audit_soft("workspace_integrity_failure", source_id=f["source_id"], file_id=f["file_id"], sha256=f["sha256"], actor=actor, where="read")
        raise WorkspaceError(409, "La copie ne correspond plus à son empreinte : accès refusé.", "integrity") from None
    audit_soft("workspace_file_read", source_id=f["source_id"], file_id=f["file_id"], actor=actor)
    return data, safe_display_name(f["rel_path"])
