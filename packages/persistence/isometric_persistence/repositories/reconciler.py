"""Artifact reconciler: dry-run and grace-period cleanup."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from psycopg import Connection

from ..artifacts import ArtifactStore


@dataclass(frozen=True)
class ReconcileReport:
    unreferenced_keys: list[str]
    deleted_keys: list[str]


class ArtifactReconciler:
    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    def referenced_keys(self, conn: Connection[Any]) -> set[str]:
        keys: set[str] = set()
        for row in conn.execute(
            "SELECT source_uri FROM drawing.documents WHERE source_uri <> ''"
        ).fetchall():
            keys.add(row["source_uri"])
        for row in conn.execute(
            "SELECT scene_uri FROM drawing.scene_revisions"
        ).fetchall():
            keys.add(row["scene_uri"])
        for row in conn.execute("SELECT uri FROM drawing.exports").fetchall():
            keys.add(row["uri"])
        for row in conn.execute(
            "SELECT artifact_uri FROM drawing.stage_runs WHERE artifact_uri IS NOT NULL"
        ).fetchall():
            keys.add(row["artifact_uri"])
        for row in conn.execute(
            """
            SELECT unnest(artifact_keys) AS key
            FROM drawing.publication_intents
            WHERE grace_until > now()
            """
        ).fetchall():
            keys.add(row["key"])
        return keys

    def dry_run(self, conn: Connection[Any]) -> ReconcileReport:
        referenced = self.referenced_keys(conn)
        orphans = [k for k in self._store.list_keys() if k not in referenced]
        return ReconcileReport(unreferenced_keys=orphans, deleted_keys=[])

    def cleanup_grace_expired(
        self,
        conn: Connection[Any],
        store_delete: Callable[[str], None],
        *,
        now: datetime | None = None,
    ) -> ReconcileReport:
        if now is None:
            now = datetime.now(UTC)
        referenced = self.referenced_keys(conn)
        deleted: list[str] = []
        for key in self._store.list_keys():
            if key in referenced:
                continue
            deleted.append(key)
            store_delete(key)
        return ReconcileReport(unreferenced_keys=[], deleted_keys=deleted)

    def register_publication_intent(
        self,
        conn: Connection[Any],
        *,
        document_id: uuid.UUID,
        expected_parent_revision_id: uuid.UUID | None,
        artifact_keys: list[str],
        grace_until: datetime,
    ) -> uuid.UUID:
        intent_id = uuid.uuid4()
        conn.execute(
            """
            INSERT INTO drawing.publication_intents (
              id, document_id, expected_parent_revision_id, artifact_keys, grace_until
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                intent_id,
                document_id,
                expected_parent_revision_id,
                artifact_keys,
                grace_until,
            ),
        )
        return intent_id
