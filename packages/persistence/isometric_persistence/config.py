"""Server-side database connection settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseSettings:
    url: str
    min_pool_size: int = 1
    max_pool_size: int = 5


def load_database_settings() -> DatabaseSettings:
    url = os.environ.get("LOCAL_DATABASE_URL") or os.environ.get(
        "SUPABASE_DEVELOPMENT_DATABASE_URL"
    )
    if not url:
        raise RuntimeError(
            "Set LOCAL_DATABASE_URL or SUPABASE_DEVELOPMENT_DATABASE_URL"
        )
    return DatabaseSettings(url=url)
