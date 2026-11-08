"""P-024 — Import GeoJSON / GeoPackage / GeoParquet route."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.geo_catalog.importer import ALLOWED_EXTENSIONS, MAX_BYTES, import_layer
from app.security.rbac import RequireRole

router = APIRouter(prefix="/api/v1/geo/import", tags=["geo-import"])

_EDITOR = Depends(RequireRole("editor"))


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_layer(
    file: UploadFile = File(...),
    name_fr: str = Form(...),
    name_en: str = Form(""),
    description_fr: str = Form(""),
    description_en: str = Form(""),
    source: str = Form("Import utilisateur"),
    license: str = Form("À vérifier"),
    license_url: str = Form(""),
    coverage: str = Form(""),
    _auth: None = _EDITOR,
):
    """
    Import a geographic file and register it as a draft layer in the catalog.
    Editor role required.
    Supported formats: GeoJSON (.geojson / .json), GeoPackage (.gpkg), GeoParquet (.parquet).
    Max file size: 50 MB.
    """
    if file.filename is None or file.filename == "":
        raise HTTPException(status_code=400, detail="No filename provided")

    import os
    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type {suffix!r}. "
                f"Allowed: {sorted(ALLOWED_EXTENSIONS)}"
            ),
        )

    content = await file.read()

    if len(content) > MAX_BYTES:
        mb = len(content) / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({mb:.1f} MB). Max: {MAX_BYTES // (1024*1024)} MB",
        )

    try:
        layer = import_layer(
            filename=file.filename,
            content=content,
            name_fr=name_fr,
            name_en=name_en,
            description_fr=description_fr,
            description_en=description_en,
            source=source,
            license=license,
            license_url=license_url,
            coverage=coverage,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Storage error: {exc}") from exc

    return {"layer": layer}
