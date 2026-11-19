"""Indexation légère d'un fichier importé : type, dimensions, colonnes, nombre de pages (aucune IA, aucun envoi externe).

Plafonds (revue P-086a) : taille (déjà bornée à la copie), pages, lignes, feuilles, colonnes, taille décompressée XLSX
(contrôle partagé avec le pack Audit), délai d'extraction. Un dépassement donne le statut « Anomalies » avec la raison,
jamais un plantage. Le délai est coopératif (vérifié entre lignes, feuilles et pages) : un seul objet démesuré dans un
PDF peut le dépasser ; c'est une limite connue, notée dans la revue."""
from __future__ import annotations

import csv
import io
import os
import time
from dataclasses import dataclass, field

from app.audit_data.files import FileRefused, _check_zip

MAX_PAGES = 500
MAX_CSV_BYTES = 25 * 1024 * 1024
MAX_ROWS = 1_000_000
MAX_SHEETS = 50
MAX_COLS = 500
_COL_NAME = 64

INDEXED, ANOMALIES = "Indexé", "Anomalies"


def _timeout() -> float:
    try:
        return max(1.0, float(os.environ.get("WORKSPACE_EXTRACT_TIMEOUT", "20")))
    except ValueError:
        return 20.0


class _Timeout(Exception):
    pass


@dataclass
class Result:
    status: str
    kind: str
    summary: dict = field(default_factory=dict)
    anomalies: list[str] = field(default_factory=list)


def _clip(cells) -> list[str]:
    return [str(c)[:_COL_NAME] for c in list(cells)[:MAX_COLS]]


def _csv(data: bytes, deadline: float) -> Result:
    if len(data) > MAX_CSV_BYTES:
        return Result(ANOMALIES, "csv", anomalies=[f"CSV de plus de {MAX_CSV_BYTES // (1024 * 1024)} Mo : non indexé."])
    text = data.decode("utf-8-sig", errors="replace")
    kind, anomalies = "csv", []
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader, None)
    except csv.Error as e:
        return Result(ANOMALIES, kind, anomalies=[f"CSV illisible : {e}"])
    if not header:
        return Result(ANOMALIES, kind, anomalies=["Fichier vide."])
    if header[0].strip().upper() in ("STRUCTURE", "DATAFLOW"):
        from app.sdmx.csv_format import SdmxError, read_sdmx_csv
        try:
            d = read_sdmx_csv(text, max_rows=MAX_ROWS)
        except SdmxError as e:
            return Result(ANOMALIES, "sdmx", anomalies=[str(e)[:300]])
        return Result(INDEXED, "sdmx", {"rows": len(d.rows), "columns": _clip(d.columns), "structure_id": d.structure_id})
    rows = 0
    try:
        for i, row in enumerate(reader, 1):
            rows = i
            if i > MAX_ROWS:
                return Result(ANOMALIES, kind, {"columns": _clip(header)}, [f"Plus de {MAX_ROWS} lignes : non indexé."])
            if i % 2000 == 0 and time.monotonic() > deadline:
                raise _Timeout
            if len(row) != len(header) and len(anomalies) < 5:
                anomalies.append(f"Ligne {i + 1} : {len(row)} colonnes au lieu de {len(header)}.")
    except csv.Error as e:
        anomalies.append(f"CSV invalide à la ligne {rows + 2} : {e}")
    return Result(ANOMALIES if anomalies else INDEXED, kind, {"rows": rows, "columns": _clip(header)}, anomalies)


def _xlsx(data: bytes, deadline: float) -> Result:
    try:
        _check_zip(data)
    except FileRefused as e:
        return Result(ANOMALIES, "xlsx", anomalies=[str(e)])
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True, keep_links=False)
    try:
        sheets, total = [], 0
        for ws in wb.worksheets[:MAX_SHEETS]:
            if time.monotonic() > deadline:
                raise _Timeout
            header, n = None, 0
            for n, row in enumerate(ws.iter_rows(values_only=True), 1):
                if header is None:
                    header = _clip("" if c is None else c for c in row)
                if n > MAX_ROWS or (n % 2000 == 0 and time.monotonic() > deadline):
                    if n > MAX_ROWS:
                        return Result(ANOMALIES, "xlsx", {"sheets": sheets}, [f"Feuille « {ws.title[:60]} » : plus de {MAX_ROWS} lignes."])
                    raise _Timeout
            total += n
            sheets.append({"name": ws.title[:60], "rows": n, "columns": header or []})
        extra = [f"Plus de {MAX_SHEETS} feuilles : les suivantes ne sont pas indexées."] if len(wb.worksheets) > MAX_SHEETS else []
        return Result(ANOMALIES if extra else INDEXED, "xlsx", {"sheets": sheets, "rows": total}, extra)
    finally:
        wb.close()


def _pdf(data: bytes, deadline: float) -> Result:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data), strict=False)
    if reader.is_encrypted:
        return Result(ANOMALIES, "pdf", anomalies=["PDF chiffré : non indexé."])
    pages = len(reader.pages)
    if pages > MAX_PAGES:
        return Result(ANOMALIES, "pdf", {"pages": pages}, [f"Plus de {MAX_PAGES} pages : non indexé."])
    chars = 0
    for i, page in enumerate(reader.pages):
        if time.monotonic() > deadline:
            raise _Timeout
        chars += len(page.extract_text() or "")
    if chars == 0:
        return Result(ANOMALIES, "pdf", {"pages": pages, "chars": 0}, ["Aucun texte extractible (PDF numérisé ? l'OCR n'est pas pris en charge)."])
    return Result(INDEXED, "pdf", {"pages": pages, "chars": chars})


def index_bytes(rel_path: str, data: bytes) -> Result:
    """Toujours un `Result` : toute erreur d'analyse devient une anomalie (le journal reçoit la raison, pas la trace)."""
    name = rel_path.lower()
    deadline = time.monotonic() + _timeout()
    try:
        if name.endswith(".csv"):
            return _csv(data, deadline)
        if name.endswith(".xlsx"):
            return _xlsx(data, deadline)
        if name.endswith(".pdf"):
            return _pdf(data, deadline)
        return Result(ANOMALIES, "autre", anomalies=["Type non pris en charge (CSV, XLSX, SDMX-CSV et PDF texte seulement)."])
    except _Timeout:
        return Result(ANOMALIES, name.rsplit(".", 1)[-1][:8], anomalies=["Délai d'extraction dépassé : non indexé."])
    except Exception as e:      # fichier hostile ou corrompu : jamais de plantage du serveur
        return Result(ANOMALIES, name.rsplit(".", 1)[-1][:8], anomalies=[f"Fichier illisible ({type(e).__name__})."])
