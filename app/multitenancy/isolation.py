"""Isolation helpers for multi-tenant access control."""
from __future__ import annotations

from typing import Optional

from app.multitenancy.org import OrgRegistry, Organisation


def require_same_org(key_a: str, key_b: str, registry: OrgRegistry) -> bool:
    """Return True if both keys belong to the same organisation."""
    org_a = registry.get_by_key(key_a)
    org_b = registry.get_by_key(key_b)
    if org_a is None or org_b is None:
        return False
    return org_a.org_id == org_b.org_id


def get_org_context(api_key: str, registry: OrgRegistry) -> Optional[Organisation]:
    """Return the organisation context for this API key."""
    return registry.get_by_key(api_key)
