"""Organisation registry — lightweight multi-tenant layer."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4


@dataclass
class Organisation:
    org_id: str
    name: str
    owner_key: str
    member_keys: list[str] = field(default_factory=list)
    created_at: str = ""

    def has_access(self, api_key: str) -> bool:
        return api_key == self.owner_key or api_key in self.member_keys

    def to_dict(self) -> dict:
        return {
            "org_id": self.org_id,
            "name": self.name,
            "owner_key": self.owner_key,
            "member_keys": self.member_keys,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Organisation":
        return cls(
            org_id=d["org_id"],
            name=d["name"],
            owner_key=d["owner_key"],
            member_keys=d.get("member_keys", []),
            created_at=d.get("created_at", ""),
        )


class OrgRegistry:
    """In-memory organisation registry backed by a JSONL file."""

    def __init__(self, path: str = "data/orgs.jsonl"):
        self._path = Path(path)
        self._orgs: dict[str, Organisation] = {}
        self._load()

    def create(self, name: str, owner_key: str) -> Organisation:
        org_id = f"org_{uuid4().hex[:8]}"
        org = Organisation(
            org_id=org_id,
            name=name,
            owner_key=owner_key,
            member_keys=[],
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        self._orgs[org_id] = org
        self._save()
        return org

    def get(self, org_id: str) -> Optional[Organisation]:
        return self._orgs.get(org_id)

    def get_by_key(self, api_key: str) -> Optional[Organisation]:
        """Return the first org this key belongs to (owner or member)."""
        for org in self._orgs.values():
            if org.has_access(api_key):
                return org
        return None

    def list_orgs(self, api_key: str) -> list[Organisation]:
        """Return all orgs where api_key is owner or member."""
        return [o for o in self._orgs.values() if o.has_access(api_key)]

    def add_member(self, org_id: str, key: str, requester_key: str) -> Organisation:
        org = self._orgs.get(org_id)
        if org is None:
            raise KeyError(f"Organisation {org_id!r} introuvable.")
        if org.owner_key != requester_key:
            raise PermissionError("Seul le propriétaire peut ajouter des membres.")
        if key not in org.member_keys:
            org.member_keys.append(key)
            self._save()
        return org

    def remove_member(self, org_id: str, key: str, requester_key: str) -> Organisation:
        org = self._orgs.get(org_id)
        if org is None:
            raise KeyError(f"Organisation {org_id!r} introuvable.")
        if org.owner_key != requester_key:
            raise PermissionError("Seul le propriétaire peut retirer des membres.")
        if key == org.owner_key:
            raise ValueError("Impossible de retirer le propriétaire.")
        if key in org.member_keys:
            org.member_keys.remove(key)
            self._save()
        return org

    def _load(self) -> None:
        if not self._path.exists():
            return
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    org = Organisation.from_dict(d)
                    self._orgs[org.org_id] = org
                except (json.JSONDecodeError, KeyError):
                    continue

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            for org in self._orgs.values():
                f.write(json.dumps(org.to_dict()) + "\n")
