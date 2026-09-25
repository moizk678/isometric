"""Deterministic relationship candidate ids."""

from __future__ import annotations

import hashlib


def relationship_id(
    rel_type: str,
    from_id: str,
    to_kind: str,
    to_id: str,
) -> str:
    payload = f"{rel_type}|{from_id}|{to_kind}|{to_id}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"rel_{digest}"
