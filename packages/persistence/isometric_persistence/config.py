"""Server-side database connection settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseSettings:
    url: str
    min_pool_size: int = 1
    max_pool_size: int = 5


def resolve_database_url() -> str:
    """Return the Postgres URL for the Supabase Cloud project.

    Works with direct/session (:5432) and transaction pooler (:6543) URLs.
    The connection pool disables psycopg prepared statements so transaction
    pooler mode remains safe.
    """
    from isometric_persistence.env_files import load_repo_dotenv

    load_repo_dotenv()
    for name in (
        "SUPABASE_DATABASE_URL",
        "SUPABASE_DEVELOPMENT_DATABASE_URL",
    ):
        url = os.environ.get(name)
        if url:
            return url
    raise RuntimeError(
        "Set SUPABASE_DATABASE_URL to the Supabase direct Postgres connection string"
    )


def load_database_settings() -> DatabaseSettings:
    return DatabaseSettings(url=resolve_database_url())
