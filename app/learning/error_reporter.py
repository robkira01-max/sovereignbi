"""Weekly error report: analyze 👎 feedback patterns to suggest semantic rules."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.feedback import FeedbackEntry

_COMPLEX_KEYWORDS: list[tuple[str, str]] = [
    ("marge", "marge brute"),
    ("taux de retour", "taux de retour"),
    ("taux", "taux"),
    ("croissance", "évolution temporelle"),
    ("prévision", "prévision ou tendance"),
    ("ratio", "ratio ou proportion"),
]

_TABLE_KEYWORDS: list[str] = ["employe", "client", "produit", "commande", "livraison"]


@dataclass
class ErrorPattern:
    pattern: str
    count: int
    examples: list[str]
    suggested_rule: str


@dataclass
class WeeklyReport:
    generated_at: str
    period_start: str
    period_end: str
    total_feedback: int
    good_count: int
    bad_count: int
    satisfaction_rate: float
    error_patterns: list[ErrorPattern]
    top_failing_questions: list[str]


def analyze_errors(entries: list[FeedbackEntry], days: int = 7) -> WeeklyReport:
    """Analyze feedback from the last N days and detect recurring error patterns."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    filtered: list[FeedbackEntry] = []
    for e in entries:
        try:
            ts = datetime.fromisoformat(e.timestamp)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                filtered.append(e)
        except ValueError:
            filtered.append(e)

    good = [e for e in filtered if e.rating == "good"]
    bad = [e for e in filtered if e.rating == "bad"]
    total = len(filtered)
    sat = len(good) / total if total > 0 else 1.0

    patterns: list[ErrorPattern] = []

    # Pattern: complex aggregation keywords in failing questions
    seen_kws: set[str] = set()
    for kw, label in _COMPLEX_KEYWORDS:
        if kw in seen_kws:
            continue
        matches = [e for e in bad if kw.lower() in e.question.lower()]
        if matches:
            seen_kws.add(kw)
            patterns.append(
                ErrorPattern(
                    pattern=f"Questions contenant « {kw} »",
                    count=len(matches),
                    examples=[e.question for e in matches[:3]],
                    suggested_rule=(
                        f"Définir la métrique « {label} » dans le modèle sémantique "
                        f"avec la formule SQL exacte."
                    ),
                )
            )

    # Pattern: table/entity references appearing frequently in failing questions
    for kw in _TABLE_KEYWORDS:
        matches = [e for e in bad if kw.lower() in e.question.lower()]
        if len(matches) >= 2:
            patterns.append(
                ErrorPattern(
                    pattern=f"Références fréquentes à « {kw} » avec erreur",
                    count=len(matches),
                    examples=[e.question for e in matches[:3]],
                    suggested_rule=(
                        f"Vérifier que la table correspondant à « {kw} » est bien "
                        f"référencée et que ses colonnes clés sont décrites dans le modèle."
                    ),
                )
            )

    return WeeklyReport(
        generated_at=now.isoformat(),
        period_start=cutoff.isoformat(),
        period_end=now.isoformat(),
        total_feedback=total,
        good_count=len(good),
        bad_count=len(bad),
        satisfaction_rate=round(sat, 4),
        error_patterns=patterns,
        top_failing_questions=[e.question for e in bad[:5]],
    )


def format_report_markdown(report: WeeklyReport) -> str:
    """Format the weekly report as Markdown for display or export."""
    lines: list[str] = [
        "# Rapport d'erreurs hebdomadaire",
        "",
        f"**Généré le** : {report.generated_at}",
        f"**Période** : {report.period_start} → {report.period_end}",
        "",
        "## Synthèse",
        "",
        "| Indicateur | Valeur |",
        "|---|---|",
        f"| Feedbacks total | {report.total_feedback} |",
        f"| 👍 Corrects | {report.good_count} |",
        f"| 👎 Erreurs | {report.bad_count} |",
        f"| Taux de satisfaction | {report.satisfaction_rate:.1%} |",
        "",
    ]

    if report.top_failing_questions:
        lines += ["## Questions échouées (top 5)", ""]
        for i, q in enumerate(report.top_failing_questions, 1):
            lines.append(f"{i}. {q}")
        lines.append("")

    if report.error_patterns:
        lines += ["## Patterns d'erreurs détectés", ""]
        for p in report.error_patterns:
            lines += [
                f"### {p.pattern} ({p.count} cas)",
                "",
                f"**Règle suggérée** : {p.suggested_rule}",
                "",
                "**Exemples** :",
            ]
            for ex in p.examples:
                lines.append(f"- {ex}")
            lines.append("")
    else:
        lines.append("*Aucun pattern d'erreur détecté.*")

    return "\n".join(lines)
