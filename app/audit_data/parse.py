"""Lecture de tableaux CSV / XLSX (P-074) en cellules brutes, avec limites et rapports explicites.

Rien n'est corrigé ici : on lit, on borne, on rapporte (encodage supposé, séparateur, lignes vides ignorées,
en-têtes vides renommés). Toute situation ambiguë non rapportable est un refus (`TableRefused`).
- XLSX : `read_only` + `data_only` (valeurs mises en cache par Excel ; les formules ne sont JAMAIS évaluées ici).
- Limites : lignes, colonnes, longueur d'une cellule.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

MAX_ROWS = 200_000
MAX_COLS = 60
MAX_CELL = 2_000
DELIMITERS = (",", ";", "\t", "|")


class TableRefused(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class Table:
    headers: list[str]
    rows: list[tuple[int, list]]          # (numéro de ligne dans le fichier, cellules) ; ligne 1 = en-tête
    meta: dict = field(default_factory=dict)


Cell = str | int | float | Decimal | date | datetime | None


def _clean_cell(v, row: int) -> Cell:
    if isinstance(v, str):
        if len(v) > MAX_CELL:
            raise TableRefused("cell_too_long", f"Ligne {row} : cellule trop longue (limite {MAX_CELL} caractères).")
        v = v.strip()
        return v or None
    if isinstance(v, bool):
        return str(v)
    return v


def _headers(raw: list, meta: dict) -> list[str]:
    heads, renamed = [], []
    for i, h in enumerate(raw, start=1):
        name = str(h).strip() if h is not None else ""
        if not name:
            name = f"colonne_{i}"
            renamed.append(i)
        heads.append(name)
    lowered = [h.lower() for h in heads]
    dup = sorted({h for h in heads if lowered.count(h.lower()) > 1})
    if dup:
        raise TableRefused("duplicate_headers", f"En-têtes en double : {', '.join(dup[:5])}. Renommez-les dans le fichier.")
    if renamed:
        meta["blank_headers_renamed"] = renamed
    return heads


def _finish(raw_rows: list[tuple[int, list]], meta: dict) -> Table:
    # première ligne non vide = en-tête
    it = iter(raw_rows)
    head = None
    for n, cells in it:
        if any(c is not None for c in cells):
            head = (n, cells)
            break
    if head is None:
        raise TableRefused("no_data", "Aucune donnée lisible dans le fichier.")
    hn, hcells = head
    while hcells and hcells[-1] is None:
        hcells = hcells[:-1]
    if len(hcells) < 2:
        raise TableRefused("header_not_found", "En-tête introuvable (au moins deux colonnes attendues).")
    if len(hcells) > MAX_COLS:
        raise TableRefused("too_many_columns", f"Trop de colonnes (limite {MAX_COLS}).")
    headers = _headers(hcells, meta)
    width = len(headers)
    rows, blanks = [], 0
    for n, cells in it:
        if all(c is None for c in cells):
            blanks += 1
            continue
        extra = cells[width:]
        if any(c is not None for c in extra):
            raise TableRefused("ragged_row", f"Ligne {n} : plus de cellules que d'en-têtes ({width}). Fichier mal formé.")
        rows.append((n, list(cells[:width]) + [None] * (width - len(cells))))
        if len(rows) > MAX_ROWS:
            raise TableRefused("too_many_rows", f"Trop de lignes (limite {MAX_ROWS}).")
    if not rows:
        raise TableRefused("no_data", "Le fichier ne contient qu'un en-tête.")
    meta.update(header_row=hn, blank_rows_skipped=blanks)
    return Table(headers=headers, rows=rows, meta=meta)


# ── CSV ──────────────────────────────────────────────────────────────────────

def _decode(data: bytes, meta: dict) -> str:
    try:
        text = data.decode("utf-8-sig")
        meta["encoding"] = "utf-8"
        return text
    except UnicodeDecodeError:
        pass
    try:
        text = data.decode("cp1252")
        meta["encoding"] = "cp1252"
        meta["encoding_assumed"] = True      # ce n'est qu'une hypothèse : on le dit
        return text
    except UnicodeDecodeError:
        raise TableRefused("bad_encoding", "Encodage illisible (UTF-8 ou Windows-1252 attendus).") from None


def _sniff(text: str) -> str:
    """Choisit le séparateur dont la largeur d'en-tête est maximale ET qu'aucune ligne de l'échantillon ne dépasse.

    Les lignes plus courtes sont tolérées (cellules finales vides) ; une ligne plus large que l'en-tête rend le séparateur
    invraisemblable. Aucun candidat cohérent : refus, on ne devine pas.
    """
    sample = text[:16384]
    if len(text) > 16384:
        sample = sample[: sample.rfind("\n") + 1] or sample
    best, best_width = None, 1
    for d in DELIMITERS:
        try:
            rows = [r for r in csv.reader(io.StringIO(sample, newline=""), delimiter=d) if any(c.strip() for c in r)]
        except csv.Error:
            continue
        if not rows:
            continue
        width = len(rows[0])
        if width >= 2 and all(len(r) <= width for r in rows) and width > best_width:
            best, best_width = d, width
    if best is None:
        raise TableRefused("delimiter_undetermined", "Séparateur de colonnes indéterminé (en-tête à une seule colonne ou lignes plus larges que l'en-tête).")
    return best


def read_csv(data: bytes) -> Table:
    meta: dict = {"format": "csv"}
    text = _decode(data, meta)
    if not text.strip():
        raise TableRefused("no_data", "Aucune donnée lisible dans le fichier.")
    delim = _sniff(text)
    meta["delimiter"] = delim
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delim, strict=True)
        raw: list[tuple[int, list]] = []
        for cells in reader:
            n = reader.line_num
            if len(cells) > MAX_COLS + 1:       # borne AVANT d'accumuler : un CSV « a,a,a,… » ne doit pas exploser la mémoire
                raise TableRefused("too_many_columns", f"Trop de colonnes (limite {MAX_COLS}).")
            raw.append((n, [_clean_cell(c, n) for c in cells]))
            if len(raw) > MAX_ROWS + 50:
                raise TableRefused("too_many_rows", f"Trop de lignes (limite {MAX_ROWS}).")
    except csv.Error as e:
        raise TableRefused("csv_malformed", f"CSV mal formé : {str(e)[:120]}") from None
    return _finish(raw, meta)


# ── XLSX ─────────────────────────────────────────────────────────────────────

def read_xlsx(data: bytes, sheet: str | None = None) -> Table:
    import openpyxl
    meta: dict = {"format": "xlsx"}
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001 - openpyxl lève des types variés sur fichier corrompu
        raise TableRefused("xlsx_unreadable", f"Classeur illisible ({type(e).__name__}).") from None
    try:
        visible = [ws for ws in wb.worksheets if ws.sheet_state == "visible"]
        meta["sheets"] = [ws.title for ws in visible]
        if sheet is not None:
            ws = next((w for w in visible if w.title == sheet), None)
            if ws is None:
                raise TableRefused("unknown_sheet", f"Feuille inconnue : {sheet[:40]!r}.")
        elif len(visible) == 1:
            ws = visible[0]
        elif not visible:
            raise TableRefused("no_data", "Aucune feuille visible dans le classeur.")
        else:
            raise TableRefused("sheet_required", f"Plusieurs feuilles ({', '.join(w.title for w in visible[:6])}) : indiquez laquelle importer.")
        meta["sheet"] = ws.title
        ws.reset_dimensions()          # dimensions déclarées non fiables : on parcourt les données réelles
        raw: list[tuple[int, list]] = []
        scanned = 0
        for n, row in enumerate(ws.iter_rows(values_only=True, max_col=MAX_COLS + 1), start=1):
            scanned += 1
            if scanned > MAX_ROWS + 1000:
                raise TableRefused("too_many_rows", f"Trop de lignes (limite {MAX_ROWS}).")
            cells = [_clean_cell(c, n) for c in row]
            if len(cells) > MAX_COLS and cells[MAX_COLS] is not None:
                raise TableRefused("too_many_columns", f"Trop de colonnes (limite {MAX_COLS}).")
            raw.append((n, cells[:MAX_COLS]))
    finally:
        wb.close()
    return _finish(raw, meta)


def read_table(data: bytes, kind: str, sheet: str | None = None) -> Table:
    if kind == "csv":
        return read_csv(data)
    if kind == "xlsx":
        return read_xlsx(data, sheet)
    raise TableRefused("unsupported_type", "Type de fichier non pris en charge.")
