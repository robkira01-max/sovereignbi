"""Import tabulaire et contrôle qualité des données d'audit (P-074).

Rôles : consultation des métadonnées = viewer ; tout ce qui touche au contenu (aperçu, anomalies, import) = editor ;
résolution d'une anomalie « error » = admin (celui qui importe ne clôt pas seul ses propres erreurs).
Les écritures sont précédées d'une entrée au journal d'audit chaîné (échec fermé si le journal est indisponible).
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from pydantic import BaseModel, Field

from app.audit_data import files, normalize, parse, repo
from app.security import row_policy
from app.security.actor import actor_label, audit_soft, audit_strict
from app.security.rbac import RequireRole

router = APIRouter(prefix="/audit-data", tags=["audit-data"])
_VIEWER, _EDITOR = RequireRole("viewer"), RequireRole("editor")
# Résolution d'anomalie : action de personne connectée (P-083) — ni clé API, même personnelle, ni clé partagée.
_EDITOR_SESSION = RequireRole("editor", session_only=True)
PREVIEW_ROWS = 20


class ImportBody(BaseModel):
    mapping: dict[str, str] = Field(max_length=12, description="champ normalisé → en-tête du fichier")
    decimal_separator: Literal[".", ","]
    date_format: str = Field(max_length=12)
    default_currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")
    default_fiscal_year: int | None = Field(None, ge=1990, le=2100)
    sheet: str | None = Field(None, max_length=64)
    dry_run: bool = False


class ResolveBody(BaseModel):
    justification: str = Field(min_length=10, max_length=500)


def _cell(v) -> str | None:
    if v is None:
        return None
    return v.isoformat() if isinstance(v, (date, datetime)) else str(v)[:200]


def _preview(table: parse.Table) -> dict:
    return {"headers": table.headers, "rows": [[_cell(c) for c in cells] for _, cells in table.rows[:PREVIEW_ROWS]],
            "rows_total": len(table.rows), "meta": table.meta}


def _redact(doc: dict, role: str) -> dict:
    """Quand des règles de sécurité par ligne existent, un non-admin ne voit que des métadonnées neutres :
    ni totaux, ni options, ni nom d'origine, ni auteur (ils révéleraient le contenu d'un périmètre non autorisé)."""
    if role == "admin" or not row_policy.active():
        return doc
    keep = ("document_id", "kind", "status", "uploaded_at", "imported_at", "rows_total", "rows_imported")
    return {k: doc[k] for k in keep if k in doc}


def _content_guard(role: str) -> None:
    if role != "admin" and row_policy.active():
        raise HTTPException(403, "Des règles de sécurité par ligne sont actives : le contenu brut des fichiers est réservé à un administrateur.")


def _store(request: Request):
    return request.app.state.store


def _read_table(doc: dict, sheet: str | None = None) -> parse.Table:
    data = files.read_original(doc["sha256"], doc["kind"])
    if data is None:
        raise HTTPException(410, "Original introuvable sur le disque.")
    if hashlib.sha256(data).hexdigest() != doc["sha256"]:
        audit_soft("audit_original_tampered", document_id=doc["document_id"])
        raise HTTPException(409, "L'original a été modifié depuis son dépôt (empreinte différente) : lecture refusée.")
    try:
        return parse.read_table(data, doc["kind"], sheet)
    except parse.TableRefused as e:
        raise HTTPException(422, {"code": e.code, "message": str(e)}) from None


def _doc_or_404(store, document_id: str) -> dict:
    try:
        doc = repo.get_document(store, document_id)
    except row_policy.AccessDenied as e:
        raise HTTPException(403, str(e)) from None
    if doc is None:
        raise HTTPException(404, "Document introuvable.")
    return doc


@router.post("/documents", status_code=201)
def upload_document(request: Request, response: Response, file: UploadFile = File(...),
                    sheet: str | None = Form(None, max_length=64), role: str = Depends(_EDITOR)):
    store, actor = _store(request), actor_label(request, role)
    try:
        declared = int(request.headers.get("content-length", "0"))
    except ValueError:
        declared = 0
    if declared > files.MAX_BYTES + 1024 * 1024:
        audit_soft("audit_file_refused", reason="too_large", size=declared, actor=actor)
        raise HTTPException(413, {"code": "too_large", "message": "Requête trop volumineuse."})
    data = file.file.read(files.MAX_BYTES + 1)          # lecture bornée : jamais plus que la limite + 1 octet
    try:
        vf = files.validate_upload(file.filename, data)
    except files.FileRefused as e:
        audit_soft("audit_file_refused", reason=e.code, size=len(data), actor=actor)
        raise HTTPException(413 if e.code == "too_large" else 400, {"code": e.code, "message": str(e)}) from None
    try:
        existing = repo.find_by_hash(store, vf.sha256)
        if existing is not None:         # même contenu déjà déposé : détecté, aucun doublon créé
            audit_soft("audit_file_duplicate", document_id=existing["document_id"], sha256=vf.sha256, actor=actor)
            response.status_code = 200
            return {"duplicate": True, "document": {k: existing[k] for k in ("document_id", "status")}}
        try:
            table = parse.read_table(data, vf.kind, sheet)
        except parse.TableRefused as e:
            audit_soft("audit_file_refused", reason=e.code, size=len(data), sha256=vf.sha256[:12], actor=actor)
            raise HTTPException(422, {"code": e.code, "message": str(e)}) from None
        with repo.LOCK:
            existing = repo.find_by_hash(store, vf.sha256)       # re-vérifié sous verrou (dépôts simultanés)
            if existing is not None:
                response.status_code = 200
                return {"duplicate": True, "document": {k: existing[k] for k in ("document_id", "status")}}
            audit_strict("audit_document_uploaded", sha256=vf.sha256, kind=vf.kind, size=vf.size, actor=actor)
            try:
                files.store_original(vf, data)
                doc_id = repo.insert_document(store, sha256=vf.sha256, display_name=vf.display_name, kind=vf.kind,
                                              size=vf.size, uploaded_by=actor, rows_total=len(table.rows))
            except files.FileRefused as e:
                audit_soft("audit_document_upload_failed", sha256=vf.sha256, reason=e.code, actor=actor)
                raise HTTPException(409, {"code": e.code, "message": str(e)}) from None
            except Exception:
                audit_soft("audit_document_upload_failed", sha256=vf.sha256, reason="internal", actor=actor)
                raise
    except row_policy.AccessDenied as e:
        raise HTTPException(403, str(e)) from None
    return {"duplicate": False, "document": _redact(repo.get_document(store, doc_id), role), "preview": _preview(table),
            "suggestions": normalize.suggest(table)}


@router.get("/documents")
def list_documents(request: Request, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                   role: str = Depends(_VIEWER)):
    try:
        return {"documents": [_redact(d, role) for d in repo.list_documents(_store(request), limit, offset)]}
    except row_policy.AccessDenied as e:
        raise HTTPException(403, str(e)) from None


@router.get("/documents/{document_id}")
def get_document(document_id: str, request: Request, role: str = Depends(_VIEWER)):
    store = _store(request)
    doc = _doc_or_404(store, document_id)
    return {**_redact(doc, role), "issue_counts": repo.issue_counts(store, document_id)}


@router.get("/documents/{document_id}/integrity")
def check_integrity(document_id: str, request: Request, _: str = Depends(_VIEWER)):
    """Recalcule le SHA-256 de l'original conservé et le compare à l'empreinte enregistrée au dépôt."""
    doc = _doc_or_404(_store(request), document_id)
    data = files.read_original(doc["sha256"], doc["kind"])
    status = "missing" if data is None else "ok" if hashlib.sha256(data).hexdigest() == doc["sha256"] else "mismatch"
    return {"document_id": document_id, "sha256": doc["sha256"], "status": status}


@router.get("/documents/{document_id}/preview")
def preview_document(document_id: str, request: Request, sheet: str | None = Query(None, max_length=64),
                     role: str = Depends(_EDITOR)):
    _content_guard(role)
    table = _read_table(_doc_or_404(_store(request), document_id), sheet)
    return {"preview": _preview(table), "suggestions": normalize.suggest(table)}


@router.post("/documents/{document_id}/import")
def import_document(document_id: str, body: ImportBody, request: Request, role: str = Depends(_EDITOR)):
    store, actor = _store(request), actor_label(request, role)
    doc = _doc_or_404(store, document_id)
    if doc["status"] != "uploaded" and not body.dry_run:
        raise HTTPException(409, "Ce document a déjà été importé (les enregistrements ne sont pas remplacés).")
    table = _read_table(doc, body.sheet)
    opts = normalize.ImportOptions(mapping=body.mapping, decimal_separator=body.decimal_separator,
                                   date_format=body.date_format, default_currency=body.default_currency,
                                   default_fiscal_year=body.default_fiscal_year)
    try:
        result = normalize.normalize(table, opts)
    except normalize.OptionsError as e:
        raise HTTPException(422, {"code": e.code, "message": str(e)}) from None
    flagged = sum(r.has_error for r in result.records)
    summary = {"rows": len(result.records), "rows_with_errors": flagged, "issue_counts": result.counts,
               "issues_truncated": result.truncated, "totals": result.totals}
    issues_preview = [vars(i) for i in result.issues[:PREVIEW_ROWS]]
    if body.dry_run:
        return {"dry_run": True, "summary": summary, "issues_preview": issues_preview}
    with repo.LOCK:
        fresh = repo.get_document(store, document_id)
        if fresh is None or fresh["status"] != "uploaded":
            raise HTTPException(409, "Ce document a déjà été importé.")
        audit_strict("audit_document_imported", document_id=document_id, rows=len(result.records),
                     rows_with_errors=flagged, issue_counts=result.counts, actor=actor)
        cur = store.con.cursor()          # transaction sur un curseur dédié : n'affecte pas les autres requêtes
        cur.execute("BEGIN TRANSACTION")
        try:
            repo.insert_records(store, document_id, result.records, cur)
            repo.insert_issues(store, document_id, result.issues, cur)
            repo.mark_imported(store, document_id, by=actor, rows=len(result.records),
                               options=body.model_dump(exclude={"dry_run"}), summary=summary, con=cur)
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            audit_soft("audit_document_import_failed", document_id=document_id, actor=actor)
            raise
        finally:
            cur.close()
        audit_soft("audit_document_import_committed", document_id=document_id, rows=len(result.records), actor=actor)
    return {"dry_run": False, "document": _redact(repo.get_document(store, document_id), role), "summary": summary,
            "issues_preview": issues_preview}


@router.get("/documents/{document_id}/issues")
def list_issues(document_id: str, request: Request, status: Literal["open", "resolved"] | None = Query(None),
                severity: Literal["error", "warning"] | None = Query(None), limit: int = Query(100, ge=1, le=500),
                offset: int = Query(0, ge=0), role: str = Depends(_EDITOR)):
    _content_guard(role)
    store = _store(request)
    _doc_or_404(store, document_id)
    try:
        return {"issues": repo.list_issues(store, document_id, status=status, severity=severity, limit=limit, offset=offset),
                "counts": repo.issue_counts(store, document_id)}
    except row_policy.AccessDenied as e:
        raise HTTPException(403, str(e)) from None


@router.post("/issues/{issue_id}/resolve")
def resolve_issue(issue_id: str, body: ResolveBody, request: Request, role: str = Depends(_EDITOR_SESSION)):
    store, actor = _store(request), actor_label(request, role)
    try:
        issue = repo.get_issue(store, issue_id)
    except row_policy.AccessDenied as e:
        raise HTTPException(403, str(e)) from None
    if issue is None:
        raise HTTPException(404, "Anomalie introuvable.")
    if issue["severity"] == "error" and role != "admin":
        raise HTTPException(403, "Une anomalie de gravité « error » ne peut être résolue que par un administrateur.")
    if issue["status"] != "open":
        raise HTTPException(409, "Anomalie déjà résolue.")
    if issue["severity"] == "error":
        parent = repo.get_document(store, issue["document_id"])
        if parent and parent.get("imported_by") == actor:      # séparation des tâches : on ne clôt pas ses propres erreurs
            raise HTTPException(403, "Séparation des tâches : l'auteur de l'import ne peut pas résoudre seul ses erreurs.")
    justification = body.justification.strip()
    if len(justification) < 10:
        raise HTTPException(422, "Justification trop courte (10 caractères minimum).")
    audit_strict("audit_issue_resolved", issue_id=issue_id, document_id=issue["document_id"], code=issue["code"],
                 severity=issue["severity"], justification_sha256=hashlib.sha256(justification.encode()).hexdigest(), actor=actor)
    if not repo.resolve_issue(store, issue_id, by=actor, justification=justification):
        raise HTTPException(409, "Anomalie déjà résolue.")
    return repo.get_issue(store, issue_id)
