"""GeoAI Agent — P-027: natural-language → spatial analysis.

Design principles:
- LLM outputs structured JSON only (no free SQL generation).
- layer_id and analysis validated against catalog/allowlist before dispatch.
- llm_fn is injected to keep this module testable without a live LLM.
- Prompt injection guard strips known patterns before forwarding to the LLM.
- No hardcoded external URLs — LLM access via app.llm module only.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from app.geo_catalog.registry import load_catalog
from app.geo_catalog.spatial_engine import SUPPORTED_ANALYSES, SpatialEngine

# ── Types ─────────────────────────────────────────────────────────────────────

@dataclass
class GeoIntent:
    analysis: str
    layer_id: str
    params: dict[str, Any]
    reasoning: str = ""


@dataclass
class GeoAIResult:
    intent: GeoIntent
    columns: list[str]
    rows: list[list[Any]]
    map_config: dict[str, Any] | None
    prose: str
    error: str | None = None


# ── Constants ─────────────────────────────────────────────────────────────────

_QUESTION_MAX = 500
_PARAM_LIMIT_MAX = 200

# Columns that can be safely used as value_col in density analysis
_KNOWN_VALUE_COLS = {
    "population_est", "population", "pop_estimated", "area_km2",
    "density", "gdp", "income", "unemployment", "chomage",
}

# Prompt injection patterns — block these before forwarding to LLM
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|all)\s+instructions?",
    r"jailbreak",
    r"system\s*prompt",
    r"<\s*/?s\s*>",          # XML/HTML system tags
    r"\[INST\]",              # Llama instruction tag
    r"act\s+as\s+",
    r"you\s+are\s+now\s+",
    r"forget\s+everything",
    r"disregard\s+",
    r"override\s+(your\s+)?instructions?",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# JSON extractor — LLM sometimes wraps JSON in markdown code blocks
_JSON_EXTRACT_RE = re.compile(r"\{[\s\S]*\}", re.MULTILINE)


# ── System prompt builder ─────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    catalog = load_catalog()
    layer_lines = "\n".join(
        f"- {layer.id} : {layer.description_fr} ({layer.geometry_type})"
        for layer in catalog.layers
        if layer.enabled
    )
    analysis_lines = "\n".join(
        f"- {name} : {desc}"
        for name, desc in SUPPORTED_ANALYSES.items()
    )
    return f"""Tu es un assistant d'analyse géographique. Analyse la demande et retourne UNIQUEMENT un objet JSON valide, sans texte autour, sans balises markdown.

Structure attendue :
{{
  "analysis": "<une des analyses ci-dessous>",
  "layer_id": "<une des couches ci-dessous>",
  "params": {{
    "lon": <float, si analysis=buffer|nearest>,
    "lat": <float, si analysis=buffer|nearest>,
    "radius_km": <float, si analysis=buffer>,
    "limit": <int, si analysis=buffer|nearest, défaut 50 pour buffer 5 pour nearest>,
    "layer_id_b": "<layer_id, si analysis=intersection>",
    "value_col": "<nom de colonne numérique, si analysis=density>"
  }},
  "reasoning": "<explication courte en une phrase>"
}}

Couches disponibles :
{layer_lines}

Analyses disponibles :
{analysis_lines}

Règles :
- Si la demande est ambiguë, choisir l'analyse la plus simple (area ou density).
- Si aucune coordonnée n'est fournie pour buffer/nearest, utiliser le centre de Djibouti-ville : lon=43.1450, lat=11.5886.
- Pour density, préférer value_col="population_est" si disponible, sinon omettre.
- Ne jamais inventer une couche ou une analyse qui n'est pas dans les listes ci-dessus.
- Retourner UNIQUEMENT le JSON, rien d'autre."""


# ── Intent parsing ────────────────────────────────────────────────────────────

def _guard_injection(question: str) -> str:
    """Raise ValueError if the question contains prompt-injection patterns."""
    if _INJECTION_RE.search(question):
        raise ValueError("Question refusée : contenu non autorisé détecté.")
    return question


def _extract_json(text: str) -> dict:
    """Extract the first JSON object from an LLM response string."""
    m = _JSON_EXTRACT_RE.search(text)
    if not m:
        raise ValueError(f"Le LLM n'a pas retourné de JSON valide. Réponse : {text[:200]!r}")
    try:
        return json.loads(m.group())
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON malformé dans la réponse du LLM : {exc}") from exc


def _validate_intent(raw: dict) -> GeoIntent:
    """Validate and coerce raw LLM JSON into a GeoIntent."""
    analysis = str(raw.get("analysis", "")).strip().lower()
    if analysis not in SUPPORTED_ANALYSES:
        raise ValueError(
            f"Analyse inconnue : {analysis!r}. "
            f"Valeurs acceptées : {', '.join(SUPPORTED_ANALYSES)}"
        )

    layer_id = str(raw.get("layer_id", "")).strip()
    catalog = load_catalog()
    valid_ids = {l.id for l in catalog.layers if l.enabled}
    if layer_id not in valid_ids:
        raise ValueError(
            f"Couche inconnue : {layer_id!r}. "
            f"Couches disponibles : {', '.join(sorted(valid_ids))}"
        )

    params: dict[str, Any] = dict(raw.get("params") or {})

    # Per-analysis param validation
    if analysis == "buffer":
        params.setdefault("lon", 43.145)
        params.setdefault("lat", 11.5886)
        params.setdefault("radius_km", 50.0)
        params["radius_km"] = max(0.1, min(float(params["radius_km"]), 500.0))
        params.setdefault("limit", 50)
        params["limit"] = max(1, min(int(params["limit"]), _PARAM_LIMIT_MAX))

    elif analysis == "nearest":
        params.setdefault("lon", 43.145)
        params.setdefault("lat", 11.5886)
        params.setdefault("limit", 5)
        params["limit"] = max(1, min(int(params["limit"]), _PARAM_LIMIT_MAX))

    elif analysis == "intersection":
        b = str(params.get("layer_id_b", "")).strip()
        if b not in valid_ids:
            # Default to another available layer
            others = sorted(valid_ids - {layer_id})
            b = others[0] if others else layer_id
        params["layer_id_b"] = b

    elif analysis == "density":
        col = str(params.get("value_col", "")).strip()
        # Only allow known safe column names to avoid injection
        if col and not re.match(r"^[a-zA-Z0-9_]+$", col):
            col = ""
        if col:
            params["value_col"] = col
        else:
            params.pop("value_col", None)

    return GeoIntent(
        analysis=analysis,
        layer_id=layer_id,
        params=params,
        reasoning=str(raw.get("reasoning", "")),
    )


def parse_intent(
    question: str,
    llm_fn: Callable[[str, str], str],
) -> GeoIntent:
    """Call the LLM to extract a GeoIntent from a natural-language question."""
    _guard_injection(question)
    system = _build_system_prompt()
    response = llm_fn(system, question)
    raw = _extract_json(response)
    return _validate_intent(raw)


# ── Dispatch to SpatialEngine ─────────────────────────────────────────────────

def _dispatch(intent: GeoIntent) -> tuple[list[str], list[list[Any]]]:
    """Run the spatial analysis and return (columns, rows)."""
    engine = SpatialEngine()
    results = engine.analyze(
        layer_id=intent.layer_id,
        analysis=intent.analysis,
        params=intent.params,
        layer_id_b=intent.params.get("layer_id_b"),
    )
    if not results:
        return [], []
    columns = list(results[0].keys())
    rows = [[row[col] for col in columns] for row in results]
    return columns, rows


# ── Map config ────────────────────────────────────────────────────────────────

def _build_map_config(intent: GeoIntent, columns: list[str]) -> dict[str, Any] | None:
    """Return a tile config for TileRenderer if the analysis produces mappable data."""
    _map_analyses = {"area", "density", "centroid", "buffer", "nearest"}
    if intent.analysis not in _map_analyses:
        return None
    tile_type = "map" if intent.layer_id == "dj_adm1" else "map-adm2"
    # First numeric column after the name column is the value
    value_col = columns[1] if len(columns) > 1 else None
    if value_col:
        return {"type": tile_type, "layer_id": intent.layer_id, "value_col": value_col}
    return None


# ── Prose generator (deterministic — no second LLM call) ─────────────────────

def _build_prose(intent: GeoIntent, columns: list[str], rows: list[list[Any]]) -> str:
    n = len(rows)
    if n == 0:
        return "Aucun résultat trouvé pour cette analyse."
    analysis = intent.analysis
    if analysis == "area":
        # Find max area row
        try:
            area_idx = columns.index("area_km2")
            best = max(rows, key=lambda r: float(r[area_idx]))
            name = best[0]
            val = round(float(best[area_idx]), 1)
            return f"{n} entité(s) analysée(s). Plus grande superficie : {name} ({val} km²)."
        except (ValueError, IndexError):
            pass
    elif analysis == "density":
        try:
            d_idx = next(i for i, c in enumerate(columns) if "density" in c)
            vals = [float(r[d_idx]) for r in rows if r[d_idx] is not None]
            if vals:
                return (
                    f"{n} entité(s) analysée(s). Densité de {min(vals):.2f} "
                    f"à {max(vals):.2f} {columns[d_idx]}."
                )
        except (StopIteration, ValueError, IndexError):
            pass
    elif analysis == "buffer":
        p = intent.params
        return (
            f"{n} entité(s) trouvée(s) dans un rayon de {p.get('radius_km', '?')} km "
            f"autour de ({p.get('lon', '?')}, {p.get('lat', '?')})."
        )
    elif analysis == "nearest":
        return f"{n} entité(s) les plus proches trouvée(s)."
    elif analysis == "intersection":
        return f"{n} paire(s) d'intersection trouvée(s) entre {intent.layer_id} et {intent.params.get('layer_id_b', '?')}."
    elif analysis == "centroid":
        return f"Centroïdes calculés pour {n} entité(s)."
    elif analysis in {"bbox", "summary"}:
        return f"Analyse {analysis} complétée — {n} résultat(s)."
    return f"Analyse terminée — {n} résultat(s)."


# ── Public entry point ─────────────────────────────────────────────────────────

def run(
    question: str,
    llm_fn: Callable[[str, str], str],
) -> GeoAIResult:
    """Full pipeline: question → intent → spatial analysis → result."""
    if not question or not question.strip():
        return GeoAIResult(
            intent=GeoIntent("", "", {}),
            columns=[], rows=[], map_config=None,
            prose="", error="La question ne peut pas être vide.",
        )
    if len(question) > _QUESTION_MAX:
        return GeoAIResult(
            intent=GeoIntent("", "", {}),
            columns=[], rows=[], map_config=None,
            prose="", error=f"Question trop longue (max {_QUESTION_MAX} caractères).",
        )

    try:
        intent = parse_intent(question, llm_fn)
    except ValueError as exc:
        return GeoAIResult(
            intent=GeoIntent("", "", {}),
            columns=[], rows=[], map_config=None,
            prose="", error=str(exc),
        )

    try:
        columns, rows = _dispatch(intent)
    except Exception as exc:
        return GeoAIResult(
            intent=intent, columns=[], rows=[], map_config=None,
            prose="", error=f"Erreur lors de l'analyse spatiale : {exc}",
        )

    map_config = _build_map_config(intent, columns)
    prose = _build_prose(intent, columns, rows)

    return GeoAIResult(
        intent=intent,
        columns=columns,
        rows=rows,
        map_config=map_config,
        prose=prose,
    )
