"""SDMX-CSV 2.0 : écriture et lecture d'un jeu de données (P-066).

Disposition (SDMX-CSV 2.0) : colonnes fixes STRUCTURE, STRUCTURE_ID, ACTION, puis les
dimensions, TIME_PERIOD, OBS_VALUE et les attributs, dans cet ordre.
Limites assumées : seule la forme « une observation par ligne » est gérée ; pas de SDMX-ML ;
la structure (DSD) n'est pas vérifiée contre un registre ; le fichier produit n'a pas été
validé avec l'outil officiel d'un registre SDMX (à faire avant diffusion).
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence

FIXED_V2 = ("STRUCTURE", "STRUCTURE_ID", "ACTION")
RESERVED = set(FIXED_V2) | {"TIME_PERIOD", "OBS_VALUE", "DATAFLOW"}
ACTIONS = {"I", "M", "R", "D"}
STRUCTURES = {"dataflow", "datastructure", "dataprovision"}
MAX_ROWS = 200_000

_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_@$\-]*$")
_STRUCT_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]+:[A-Za-z0-9_@$\-]+\(\d+(\.\d+){0,2}\)$")
_TIME_RE = re.compile(r"^\d{4}(-(0[1-9]|1[0-2]|Q[1-4]|S[12]|W(0[1-9]|[1-4]\d|5[0-3])|(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])))?$")


class SdmxError(ValueError):
    """Fichier ou paramètre SDMX invalide (message destiné à l'utilisateur)."""


def component_id(name: str) -> str:
    """« Région » → REGION ; « taux chômage (%) » → TAUX_CHOMAGE ; erreur si rien d'exploitable."""
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").upper()
    if not s or not s[0].isalpha():
        raise SdmxError(f"Nom de colonne inutilisable comme identifiant SDMX : « {name} »")
    return s


def default_structure_id(label: str, agency: str = "MIZANBI", version: str = "1.0") -> str:
    return f"{agency}:{component_id(label)}({version})"


def to_time_period(value: Any, freq: str | None = None) -> str:
    """Valeur → période SDMX (2024, 2024-Q1, 2024-03, 2024-03-15). Refuse ce qui n'est pas une période."""
    if isinstance(value, (datetime, date)):
        d = value.date() if isinstance(value, datetime) else value
        f = (freq or "D").upper()
        if f == "A":
            return f"{d.year:04d}"
        if f == "M":
            return f"{d.year:04d}-{d.month:02d}"
        if f == "Q":
            return f"{d.year:04d}-Q{(d.month - 1) // 3 + 1}"
        return d.isoformat()
    s = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value).strip()
    if _TIME_RE.match(s):
        return s
    raise SdmxError(f"TIME_PERIOD invalide : « {value} » (attendu 2024, 2024-Q1, 2024-03 ou 2024-03-15)")


def _number(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        raise SdmxError("OBS_VALUE ne peut pas être un booléen")
    if isinstance(value, (int, float, Decimal)):
        if isinstance(value, float) and value != value:  # NaN
            return ""
        return str(value)
    try:
        float(str(value))
    except ValueError as e:
        raise SdmxError(f"OBS_VALUE non numérique : « {value} »") from e
    return str(value).strip()


def _safe_text(value: Any) -> str:
    """Texte de dimension/attribut ; neutralise l'injection de formule si le fichier est ouvert dans un tableur."""
    if value is None:
        return ""
    s = str(value)
    return "'" + s if s[:1] in ("=", "+", "@") else s


def write_sdmx_csv(
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    structure_id: str,
    value_col: str,
    time_col: str | None = None,
    dims: Sequence[str] | None = None,
    unit: str | None = None,
    freq: str | None = None,
    structure: str = "dataflow",
    action: str = "I",
) -> str:
    """Résultat tabulaire → texte SDMX-CSV 2.0. `dims` : colonnes-dimensions (par défaut toutes les autres)."""
    if structure not in STRUCTURES:
        raise SdmxError(f"Type de structure inconnu : {structure}")
    if action not in ACTIONS:
        raise SdmxError(f"Action inconnue : {action} (attendu I, M, R ou D)")
    if not _STRUCT_ID_RE.match(structure_id):
        raise SdmxError("STRUCTURE_ID invalide : attendu AGENCE:IDENTIFIANT(VERSION), ex. MIZANBI:PIB(1.0)")
    if len(rows) > MAX_ROWS:
        raise SdmxError(f"Trop de lignes : {len(rows)} (maximum {MAX_ROWS})")
    cols = list(columns)
    for c in (value_col, *([time_col] if time_col else [])):
        if c not in cols:
            raise SdmxError(f"Colonne introuvable dans le résultat : « {c} »")
    dim_cols = [c for c in (dims if dims is not None else cols) if c not in (value_col, time_col)]
    for c in dim_cols:
        if c not in cols:
            raise SdmxError(f"Colonne introuvable dans le résultat : « {c} »")
    dim_ids = [component_id(c) for c in dim_cols]
    if len(set(dim_ids)) != len(dim_ids):
        raise SdmxError("Deux colonnes donnent le même identifiant SDMX : renommez-les")
    clash = RESERVED & set(dim_ids)
    if clash:
        raise SdmxError(f"Identifiant réservé par SDMX-CSV : {', '.join(sorted(clash))}")
    idx = {c: i for i, c in enumerate(cols)}

    header = [*FIXED_V2, *dim_ids, *(["TIME_PERIOD"] if time_col else []), "OBS_VALUE", *(["UNIT_MEASURE"] if unit else [])]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        line = [structure, structure_id, action, *(_safe_text(r[idx[c]]) for c in dim_cols)]
        if time_col:
            line.append(to_time_period(r[idx[time_col]], freq))
        line.append(_number(r[idx[value_col]]))
        if unit:
            line.append(_safe_text(unit))
        w.writerow(line)
    return buf.getvalue()


@dataclass
class SdmxData:
    version: str                       # "2.0" ou "1.0"
    structure: str                     # dataflow, datastructure, dataprovision
    structure_id: str
    action: str                        # I, M, R, D
    columns: list[str]                 # composants (dimensions, TIME_PERIOD, OBS_VALUE, attributs)
    rows: list[tuple]                  # OBS_VALUE converti en float ou None
    has_time: bool


def read_sdmx_csv(text: str, *, max_rows: int = MAX_ROWS) -> SdmxData:
    """Texte SDMX-CSV (2.0 ou 1.0) → données validées. Lève SdmxError avec le numéro de ligne fautif."""
    text = text.lstrip("﻿")
    reader = csv.reader(io.StringIO(text))
    try:
        header = [h.strip() for h in next(reader)]
    except StopIteration:
        raise SdmxError("Fichier vide") from None
    if header[:2] == ["STRUCTURE", "STRUCTURE_ID"]:
        version, fixed = "2.0", 3 if header[2:3] == ["ACTION"] else 2
    elif header[:1] == ["DATAFLOW"]:
        version, fixed = "1.0", 1
    else:
        raise SdmxError("Première colonne attendue : STRUCTURE, STRUCTURE_ID (SDMX-CSV 2.0) ou DATAFLOW (1.0)")
    comps = header[fixed:]
    if len(set(comps)) != len(comps):
        raise SdmxError("Colonnes en double dans l'en-tête")
    for c in comps:
        if not _ID_RE.match(c):
            raise SdmxError(f"Identifiant de colonne invalide : « {c} »")
    if "OBS_VALUE" not in comps:
        raise SdmxError("Colonne OBS_VALUE absente")
    ti, vi = (comps.index("TIME_PERIOD") if "TIME_PERIOD" in comps else None), comps.index("OBS_VALUE")

    structure = structure_id = action = None
    rows: list[tuple] = []
    for n, rec in enumerate(reader, start=2):
        if not rec or all(not x.strip() for x in rec):
            continue
        if len(rec) != len(header):
            raise SdmxError(f"Ligne {n} : {len(rec)} colonnes, {len(header)} attendues")
        if len(rows) >= max_rows:
            raise SdmxError(f"Trop de lignes (maximum {max_rows})")
        if version == "2.0":
            st, sid, act = rec[0].strip().lower(), rec[1].strip(), (rec[2].strip().upper() if fixed == 3 and rec[2].strip() else "I")
        else:
            st, sid, act = "dataflow", rec[0].strip(), "I"
        if st not in STRUCTURES:
            raise SdmxError(f"Ligne {n} : type de structure inconnu « {st} »")
        if act not in ACTIONS:
            raise SdmxError(f"Ligne {n} : action inconnue « {act} »")
        if structure is None:
            structure, structure_id, action = st, sid, act
        elif (st, sid, act) != (structure, structure_id, action):
            raise SdmxError(f"Ligne {n} : un seul dataflow et une seule action par fichier")
        vals = rec[fixed:]
        if ti is not None and vals[ti].strip():
            try:
                to_time_period(vals[ti].strip())
            except SdmxError as e:
                raise SdmxError(f"Ligne {n} : {e}") from None
        raw_v = vals[vi].strip()
        try:
            obs = float(raw_v) if raw_v != "" else None
        except ValueError:
            raise SdmxError(f"Ligne {n} : OBS_VALUE non numérique « {raw_v} »") from None
        if obs is not None and (obs != obs or obs in (float("inf"), float("-inf"))):
            raise SdmxError(f"Ligne {n} : OBS_VALUE invalide « {raw_v} »")
        rows.append(tuple(obs if i == vi else (v if v != "" else None) for i, v in enumerate(vals)))
    if not rows:
        raise SdmxError("Aucune observation dans le fichier")
    return SdmxData(version, structure, structure_id, action, comps, rows, ti is not None)
