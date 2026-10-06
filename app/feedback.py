"""Feedback and audit journal — JSONL files, chained SHA-256 hashes for audit."""
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

FEEDBACK_PATH = Path("data/feedback.jsonl")
AUDIT_PATH = Path("data/audit.jsonl")


@dataclass
class FeedbackEntry:
    timestamp: str
    question: str
    sql: str
    rating: str  # "good" | "bad"
    comment: str = ""


@dataclass
class AuditEntry:
    timestamp: str
    action: str  # "upload" | "ask" | "dashboard_pin" | "dashboard_save"
    details: dict
    hash: str = field(default="")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _last_hash(path: Path) -> str:
    if not path.exists():
        return ""
    last = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            last = line
    if not last:
        return ""
    try:
        return json.loads(last).get("hash", "")
    except json.JSONDecodeError:
        return ""


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def record_feedback(
    question: str,
    sql: str,
    rating: str,
    comment: str = "",
    path: Path | None = None,
) -> None:
    if rating not in ("good", "bad"):
        raise ValueError(f"rating must be 'good' or 'bad', got {rating!r}")
    p = path or FEEDBACK_PATH
    _ensure_dir(p)
    entry = FeedbackEntry(
        timestamp=_now(),
        question=question,
        sql=sql,
        rating=rating,
        comment=comment,
    )
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")


def record_audit(
    action: str,
    details: dict,
    path: Path | None = None,
) -> None:
    p = path or AUDIT_PATH
    _ensure_dir(p)
    prev_hash = _last_hash(p)
    entry_dict = {
        "timestamp": _now(),
        "action": action,
        "details": details,
    }
    content = json.dumps(entry_dict, ensure_ascii=False, sort_keys=True)
    entry_dict["hash"] = _sha256(prev_hash + content)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry_dict, ensure_ascii=False) + "\n")


def load_feedback(path: Path | None = None) -> list[FeedbackEntry]:
    p = path or FEEDBACK_PATH
    if not p.exists():
        return []
    entries = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            entries.append(FeedbackEntry(**d))
        except (json.JSONDecodeError, TypeError):
            continue
    return entries


def load_audit(path: Path | None = None) -> list[AuditEntry]:
    p = path or AUDIT_PATH
    if not p.exists():
        return []
    entries = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            entries.append(AuditEntry(**d))
        except (json.JSONDecodeError, TypeError):
            continue
    return entries
