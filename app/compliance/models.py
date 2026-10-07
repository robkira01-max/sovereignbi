"""Modèles de conformité Loi 25 / PIPEDA."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

CONSENT_PATH = Path("data/compliance_consents.jsonl")
REQUESTS_PATH = Path("data/compliance_requests.jsonl")
INVENTORY_PATH = Path("data/compliance_inventory.jsonl")

RetentionPolicy = Literal["session", "30d", "90d", "1y", "indefinite"]
RequestStatus = Literal["pending", "completed", "rejected"]
RequestType = Literal["access", "delete", "export", "rectification"]
ConsentPurpose = Literal["analytics", "ai_processing", "data_sharing", "marketing"]


@dataclass
class ConsentRecord:
    consent_id: str
    user_id: str
    purpose: str
    granted: bool
    granted_at: str
    withdrawn_at: str | None = None
    ip_address: str | None = None


@dataclass
class DataSubjectRequest:
    request_id: str
    user_id: str
    request_type: str
    status: RequestStatus = "pending"
    created_at: str = ""
    completed_at: str | None = None
    notes: str = ""


@dataclass
class DataInventoryItem:
    item_id: str
    data_category: str
    description: str
    retention_policy: RetentionPolicy
    legal_basis: str
    location: str
    created_at: str = ""


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def record_consent(
    user_id: str,
    purpose: str,
    granted: bool,
    ip_address: str | None = None,
    path: Path = CONSENT_PATH,
) -> ConsentRecord:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = ConsentRecord(
        consent_id=str(uuid.uuid4()),
        user_id=user_id,
        purpose=purpose,
        granted=granted,
        granted_at=_now(),
        ip_address=ip_address,
    )
    with path.open("a") as f:
        f.write(json.dumps(asdict(c)) + "\n")
    return c


def withdraw_consent(
    user_id: str,
    purpose: str,
    path: Path = CONSENT_PATH,
) -> int:
    """Mark all active consents for user+purpose as withdrawn. Returns count updated."""
    if not path.exists():
        return 0
    records = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    updated = 0
    for r in records:
        if r["user_id"] == user_id and r["purpose"] == purpose and r["withdrawn_at"] is None:
            r["withdrawn_at"] = _now()
            updated += 1
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return updated


def list_consents(user_id: str, path: Path = CONSENT_PATH) -> list[ConsentRecord]:
    if not path.exists():
        return []
    return [
        ConsentRecord(**json.loads(l))
        for l in path.read_text().splitlines()
        if l.strip() and json.loads(l)["user_id"] == user_id
    ]


def create_subject_request(
    user_id: str,
    request_type: str,
    notes: str = "",
    path: Path = REQUESTS_PATH,
) -> DataSubjectRequest:
    valid_types = {"access", "delete", "export", "rectification"}
    if request_type not in valid_types:
        raise ValueError(f"Type de demande invalide : {request_type!r}. Valeurs : {valid_types}")
    path.parent.mkdir(parents=True, exist_ok=True)
    r = DataSubjectRequest(
        request_id=str(uuid.uuid4()),
        user_id=user_id,
        request_type=request_type,
        status="pending",
        created_at=_now(),
        notes=notes,
    )
    with path.open("a") as f:
        f.write(json.dumps(asdict(r)) + "\n")
    return r


def list_requests(
    user_id: str | None = None,
    path: Path = REQUESTS_PATH,
) -> list[DataSubjectRequest]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if user_id is None or d["user_id"] == user_id:
            out.append(DataSubjectRequest(**d))
    return out


def update_request_status(
    request_id: str,
    status: RequestStatus,
    notes: str = "",
    path: Path = REQUESTS_PATH,
) -> DataSubjectRequest:
    if not path.exists():
        raise KeyError(request_id)
    records = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    found = None
    for r in records:
        if r["request_id"] == request_id:
            r["status"] = status
            if status == "completed":
                r["completed_at"] = _now()
            if notes:
                r["notes"] = notes
            found = r
    if found is None:
        raise KeyError(request_id)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return DataSubjectRequest(**found)


def add_inventory_item(
    data_category: str,
    description: str,
    retention_policy: RetentionPolicy,
    legal_basis: str,
    location: str,
    path: Path = INVENTORY_PATH,
) -> DataInventoryItem:
    valid_policies = {"session", "30d", "90d", "1y", "indefinite"}
    if retention_policy not in valid_policies:
        raise ValueError(f"Politique de rétention invalide : {retention_policy!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    item = DataInventoryItem(
        item_id=str(uuid.uuid4()),
        data_category=data_category,
        description=description,
        retention_policy=retention_policy,
        legal_basis=legal_basis,
        location=location,
        created_at=_now(),
    )
    with path.open("a") as f:
        f.write(json.dumps(asdict(item)) + "\n")
    return item


def list_inventory(path: Path = INVENTORY_PATH) -> list[DataInventoryItem]:
    if not path.exists():
        return []
    return [
        DataInventoryItem(**json.loads(l))
        for l in path.read_text().splitlines()
        if l.strip()
    ]
