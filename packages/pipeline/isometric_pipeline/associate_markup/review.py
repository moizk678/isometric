"""Stable review item ids for association artifacts."""

from __future__ import annotations

import hashlib


def review_item_id(*parts: str) -> str:
    payload = "|".join(parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"rev_{digest}"
