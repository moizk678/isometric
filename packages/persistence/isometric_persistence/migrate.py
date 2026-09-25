"""Apply versioned SQL migrations from supabase/migrations."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from psycopg import Connection

MIGRATION_DIR = Path(__file__).resolve().parents[3] / "supabase" / "migrations"
VERSION_RE = re.compile(r"^(\d+)_.*\.sql$")


def migration_files() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for path in sorted(MIGRATION_DIR.glob("*.sql")):
        match = VERSION_RE.match(path.name)
        if not match:
            continue
        files.append((match.group(1), path))
    return files


def ensure_tracking_table(conn: Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS public.schema_migrations (
          version text PRIMARY KEY,
          checksum_sha256 text NOT NULL,
          applied_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def applied_versions(conn: Connection) -> dict[str, str]:
    ensure_tracking_table(conn)
    rows = conn.execute(
        "SELECT version, checksum_sha256 FROM public.schema_migrations"
    ).fetchall()
    return {row["version"]: row["checksum_sha256"] for row in rows}


def apply_migrations(conn: Connection) -> list[str]:
    ensure_tracking_table(conn)
    applied = applied_versions(conn)
    newly_applied: list[str] = []
    for version, path in migration_files():
        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        if version in applied:
            if applied[version] != checksum:
                raise RuntimeError(
                    f"migration drift for {path.name}: recorded checksum differs"
                )
            continue
        conn.execute(sql)
        conn.execute(
            """
            INSERT INTO public.schema_migrations (version, checksum_sha256)
            VALUES (%s, %s)
            """,
            (version, checksum),
        )
        newly_applied.append(path.name)
    return newly_applied
