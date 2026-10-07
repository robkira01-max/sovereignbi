"""Calcul du score de confiance par requête."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfidenceScore:
    score: float
    factors: dict[str, float]
    label: str
    explanation: str


def compute_confidence(state: dict, few_shot_count: int = 0) -> ConfidenceScore:
    """Calcule le score de confiance depuis l'état final du pipeline.

    Facteurs et poids :
    - attempts (0.35) : 1.0 si 1 tentative, 0.6 si 2, 0.2 si 3+
    - has_results (0.25) : 1.0 si rows > 0, 0.5 si vide sans erreur, 0.0 si erreur
    - few_shot_hit (0.20) : min(few_shot_count / 2, 1.0)
    - no_error (0.20) : 1.0 si pas d'erreur, 0.0 sinon
    """
    attempts = state.get("attempts", 1) or 1
    error = state.get("error")
    rows = state.get("rows") or []

    attempts_score = 1.0 if attempts == 1 else (0.6 if attempts == 2 else 0.2)
    no_error_score = 0.0 if error else 1.0
    if error:
        results_score = 0.0
    elif rows:
        results_score = 1.0
    else:
        results_score = 0.5
    few_shot_score = min(few_shot_count / 2.0, 1.0)

    score = (
        0.35 * attempts_score
        + 0.25 * results_score
        + 0.20 * few_shot_score
        + 0.20 * no_error_score
    )
    score = round(min(max(score, 0.0), 1.0), 4)

    factors = {
        "attempts": round(attempts_score, 4),
        "has_results": round(results_score, 4),
        "few_shot_hit": round(few_shot_score, 4),
        "no_error": round(no_error_score, 4),
    }

    if score >= 0.75:
        label = "élevée"
    elif score >= 0.45:
        label = "moyenne"
    else:
        label = "faible"

    parts = [f"Requête générée en {attempts} tentative{'s' if attempts > 1 else ''}."]
    if few_shot_count:
        parts.append(f"{few_shot_count} exemple{'s' if few_shot_count > 1 else ''} similaire{'s' if few_shot_count > 1 else ''} trouvé{'s' if few_shot_count > 1 else ''}.")
    if error:
        parts.append("Erreur lors de l'exécution.")
    elif not rows:
        parts.append("Aucun résultat retourné.")
    explanation = " ".join(parts)

    return ConfidenceScore(score=score, factors=factors, label=label, explanation=explanation)
