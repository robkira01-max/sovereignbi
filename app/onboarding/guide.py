"""Onboarding guidé — étapes, progression, démo sandbox."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ONBOARDING_PATH = Path("data/onboarding_progress.jsonl")

StepStatus = Literal["pending", "completed", "skipped"]


ONBOARDING_STEPS = [
    {
        "step_id": "step-upload",
        "order": 1,
        "title": "Charger des données",
        "description": "Importez votre premier fichier CSV ou Excel via /upload.",
        "action": "POST /upload",
        "doc_url": "/docs#/default/upload_upload_post",
    },
    {
        "step_id": "step-ask",
        "order": 2,
        "title": "Poser une question",
        "description": "Posez une question en langage naturel sur vos données.",
        "action": "POST /ask",
        "doc_url": "/docs#/default/ask_ask_post",
    },
    {
        "step_id": "step-dashboard",
        "order": 3,
        "title": "Créer un tableau de bord",
        "description": "Sauvegardez vos questions favorites sous forme de tableau de bord.",
        "action": "POST /dashboards",
        "doc_url": "/docs#/dashboards",
    },
    {
        "step_id": "step-alert",
        "order": 4,
        "title": "Configurer une alerte",
        "description": "Définissez un seuil pour être notifié automatiquement.",
        "action": "POST /alerts/rules",
        "doc_url": "/docs#/alerts",
    },
    {
        "step_id": "step-export",
        "order": 5,
        "title": "Exporter les résultats",
        "description": "Exportez vos résultats en Excel ou PDF.",
        "action": "POST /export/excel",
        "doc_url": "/docs#/export",
    },
]


@dataclass
class StepProgress:
    session_id: str
    step_id: str
    status: StepStatus = "pending"
    completed_at: str | None = None
    notes: str = ""


@dataclass
class OnboardingSession:
    session_id: str
    user_id: str
    created_at: str
    steps: list[StepProgress] = field(default_factory=list)
    completed: bool = False


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def create_session(user_id: str, path: Path = ONBOARDING_PATH) -> OnboardingSession:
    path.parent.mkdir(parents=True, exist_ok=True)
    session_id = str(uuid.uuid4())
    steps = [
        StepProgress(session_id=session_id, step_id=s["step_id"])
        for s in ONBOARDING_STEPS
    ]
    session = OnboardingSession(
        session_id=session_id,
        user_id=user_id,
        created_at=_now(),
        steps=steps,
    )
    with path.open("a") as f:
        f.write(json.dumps(_session_to_dict(session)) + "\n")
    return session


def _session_to_dict(s: OnboardingSession) -> dict:
    return {
        "session_id": s.session_id,
        "user_id": s.user_id,
        "created_at": s.created_at,
        "completed": s.completed,
        "steps": [asdict(step) for step in s.steps],
    }


def _dict_to_session(d: dict) -> OnboardingSession:
    return OnboardingSession(
        session_id=d["session_id"],
        user_id=d["user_id"],
        created_at=d["created_at"],
        completed=d.get("completed", False),
        steps=[StepProgress(**s) for s in d.get("steps", [])],
    )


def get_session(session_id: str, path: Path = ONBOARDING_PATH) -> OnboardingSession | None:
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if d["session_id"] == session_id:
            return _dict_to_session(d)
    return None


def complete_step(
    session_id: str,
    step_id: str,
    path: Path = ONBOARDING_PATH,
) -> OnboardingSession:
    if not path.exists():
        raise KeyError(session_id)
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    sessions = [json.loads(l) for l in lines]
    found = None
    for d in sessions:
        if d["session_id"] == session_id:
            for step in d["steps"]:
                if step["step_id"] == step_id:
                    step["status"] = "completed"
                    step["completed_at"] = _now()
            d["completed"] = all(s["status"] == "completed" for s in d["steps"])
            found = d
    if found is None:
        raise KeyError(session_id)
    path.write_text("\n".join(json.dumps(d) for d in sessions) + "\n")
    return _dict_to_session(found)


def get_progress(session_id: str, path: Path = ONBOARDING_PATH) -> dict:
    session = get_session(session_id, path)
    if session is None:
        raise KeyError(session_id)
    total = len(session.steps)
    done = sum(1 for s in session.steps if s.status == "completed")
    return {
        "session_id": session_id,
        "user_id": session.user_id,
        "total_steps": total,
        "completed_steps": done,
        "progress_pct": round(done / total * 100) if total else 0,
        "completed": session.completed,
        "steps": [asdict(s) for s in session.steps],
    }
