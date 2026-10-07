"""Rule proposals: generate, store, approve/reject, and apply to semantic model."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.learning.error_reporter import WeeklyReport

PROPOSALS_PATH = Path("data/rule_proposals.jsonl")


@dataclass
class RuleProposal:
    id: str
    proposed_at: str
    source: str  # "error_analysis" | "manual"
    rule_text: str
    rationale: str
    status: str  # "pending" | "approved" | "rejected"
    applied: bool = False
    reviewed_at: str | None = None
    reviewed_by: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def propose_rules(report: WeeklyReport) -> list[RuleProposal]:
    """Generate pending proposals from error patterns in a weekly report."""
    proposals = []
    for pattern in report.error_patterns:
        proposals.append(
            RuleProposal(
                id=str(uuid.uuid4())[:8],
                proposed_at=_now(),
                source="error_analysis",
                rule_text=pattern.suggested_rule,
                rationale=(
                    f"Pattern détecté : {pattern.pattern} ({pattern.count} cas). "
                    f"Exemples : {'; '.join(pattern.examples[:2])}"
                ),
                status="pending",
            )
        )
    return proposals


def save_proposal(p: RuleProposal, path: Path | None = None) -> None:
    target = path or PROPOSALS_PATH
    _ensure_dir(target)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")


def load_proposals(
    status: str | None = None, path: Path | None = None
) -> list[RuleProposal]:
    target = path or PROPOSALS_PATH
    if not target.exists():
        return []
    results = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            p = RuleProposal(**d)
            if status is None or p.status == status:
                results.append(p)
        except (json.JSONDecodeError, TypeError):
            continue
    return results


def _rewrite(proposals: list[RuleProposal], path: Path) -> None:
    _ensure_dir(path)
    with path.open("w", encoding="utf-8") as f:
        for p in proposals:
            f.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")


def approve_proposal(proposal_id: str, reviewer: str, path: Path | None = None) -> RuleProposal:
    target = path or PROPOSALS_PATH
    proposals = load_proposals(path=target)
    updated = None
    for p in proposals:
        if p.id == proposal_id:
            p.status = "approved"
            p.reviewed_at = _now()
            p.reviewed_by = reviewer
            updated = p
    if updated is None:
        raise ValueError(f"Proposition {proposal_id!r} introuvable")
    _rewrite(proposals, target)
    return updated


def reject_proposal(proposal_id: str, reviewer: str, path: Path | None = None) -> RuleProposal:
    target = path or PROPOSALS_PATH
    proposals = load_proposals(path=target)
    updated = None
    for p in proposals:
        if p.id == proposal_id:
            p.status = "rejected"
            p.reviewed_at = _now()
            p.reviewed_by = reviewer
            updated = p
    if updated is None:
        raise ValueError(f"Proposition {proposal_id!r} introuvable")
    _rewrite(proposals, target)
    return updated


def apply_approved_rules(
    model_path: Path = Path("semantic/model.yaml"),
    proposals_path: Path | None = None,
    versions_dir: Path | None = None,
) -> list[str]:
    """Add approved (not yet applied) proposals as rules in model.yaml.

    Snapshots the current model before any modification.
    Returns the list of newly added rule texts.
    """
    from app.learning.versioning import snapshot

    snapshot(label="pre_apply", model_path=model_path, versions_dir=versions_dir)

    target = proposals_path or PROPOSALS_PATH
    proposals = load_proposals(path=target)
    to_apply = [p for p in proposals if p.status == "approved" and not p.applied]
    if not to_apply:
        return []

    model_data = yaml.safe_load(model_path.read_text(encoding="utf-8")) or {}
    existing_rules: list[str] = model_data.get("rules", [])

    new_rules: list[str] = []
    for p in proposals:
        if p.status == "approved" and not p.applied:
            if p.rule_text not in existing_rules:
                existing_rules.append(p.rule_text)
                new_rules.append(p.rule_text)
            p.applied = True

    model_data["rules"] = existing_rules
    model_path.write_text(
        yaml.dump(model_data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    _rewrite(proposals, target)
    return new_rules
