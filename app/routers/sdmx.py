"""Import SDMX-CSV (P-066) : POST /sdmx/import — éditeur seulement."""
from __future__ import annotations

import os
import re

import pandas as pd
import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile

from app.sdmx.csv_format import SdmxError, read_sdmx_csv
from app.security.rbac import RequireRole

router = APIRouter(prefix="/sdmx", tags=["sdmx"])
log = structlog.get_logger()

_EDITOR = RequireRole("editor")
_MAX_BYTES = int(os.environ.get("SOVEREIGN_MAX_UPLOAD_MB", "50")) * 1024 * 1024
_TABLE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,60}$")
PREFIX = "sdmx_"


def _table_name(requested: str | None, structure_id: str) -> str:
    base = requested or re.sub(r"[^A-Za-z0-9]+", "_", structure_id.split(":")[-1].split("(")[0]).strip("_").lower()
    if not _TABLE_RE.match(base or "x"):
        raise HTTPException(422, "Nom de table invalide (lettres, chiffres et _, 61 caractères maximum).")
    # Toujours préfixée : un import ne peut ni écraser ni remplacer une table existante qui ne vient pas d'un import SDMX.
    return base if base.lower().startswith(PREFIX) else PREFIX + base.lower()


@router.post("/import")
async def import_sdmx_csv(
    request: Request,
    file: UploadFile = File(...),
    table: str | None = Query(None, max_length=61),
    replace: bool = Query(False, description="Remplacer la table sdmx_* si elle existe"),
    dry_run: bool = Query(False, description="Valider et décrire sans charger"),
    _: str = Depends(_EDITOR),
):
    """Valide un fichier SDMX-CSV (2.0 ou 1.0) puis le charge dans une table `sdmx_*` (colonnes = composants SDMX)."""
    data = await file.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise HTTPException(413, f"Fichier trop volumineux (limite {_MAX_BYTES // 1024 // 1024} Mo).")
    if data[:64].lstrip().startswith(b"<"):
        raise HTTPException(400, "Fichier invalide : du XML/HTML a été détecté (seul SDMX-CSV est accepté, pas SDMX-ML).")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "Le fichier doit être encodé en UTF-8.") from None
    try:
        parsed = read_sdmx_csv(text)
    except SdmxError as exc:
        raise HTTPException(422, str(exc)) from exc
    if parsed.action == "D":
        raise HTTPException(422, "L'action D (suppression) n'est pas prise en charge à l'import.")

    name = _table_name(table, parsed.structure_id)
    store = request.app.state.store
    summary = {
        "table": name, "structure_id": parsed.structure_id, "version": parsed.version, "action": parsed.action,
        "columns": parsed.columns, "rows": len(parsed.rows), "has_time_period": parsed.has_time,
    }
    if dry_run:
        return {**summary, "loaded": False}
    if name in store.tables and not replace:
        raise HTTPException(409, f"La table « {name} » existe déjà : utilisez replace=true pour la remplacer.")
    df = pd.DataFrame(parsed.rows, columns=parsed.columns)
    loaded = store.load_dataframe(name, df)
    cache = getattr(request.app.state, "query_cache", None)
    if cache is not None:
        cache.invalidate()
    log.info("sdmx_import", table=loaded, rows=len(parsed.rows), structure_id=parsed.structure_id)
    return {**summary, "table": loaded, "loaded": True}
