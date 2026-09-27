"""Scene revision and review item repository."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from psycopg import Connection

from ..errors import ConflictError


@dataclass(frozen=True)
class ReviewItemSnapshot:
    issue_key: str
    object_id: str | None
    relationship_id: str | None
    issue_type: str
    severity: str
    crop_uri: str | None
    proposed_options: list[Any]
    state: str


@dataclass(frozen=True)
class SceneRevisionRow:
    id: uuid.UUID
    document_id: uuid.UUID
    parent_revision_id: uuid.UUID | None
    scene_uri: str
    scene_checksum_sha256: str


@dataclass(frozen=True)
class RevisionPublishMeta:
    author_type: str
    review_state: str


class RevisionRepository:
    def insert_revision(
        self,
        conn: Connection[Any],
        *,
        revision_id: uuid.UUID,
        document_id: uuid.UUID,
        parent_revision_id: uuid.UUID | None,
        schema_version: str,
        scene_uri: str,
        scene_checksum_sha256: str,
        author_type: str,
        review_state: str,
        validation_status: str,
    ) -> SceneRevisionRow:
        row = conn.execute(
            """
            INSERT INTO drawing.scene_revisions (
              id, document_id, parent_revision_id, schema_version,
              scene_uri, scene_checksum_sha256, author_type, review_state, validation_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, document_id, parent_revision_id, scene_uri, scene_checksum_sha256
            """,
            (
                revision_id,
                document_id,
                parent_revision_id,
                schema_version,
                scene_uri,
                scene_checksum_sha256,
                author_type,
                review_state,
                validation_status,
            ),
        ).fetchone()
        assert row is not None
        return SceneRevisionRow(
            id=row["id"],
            document_id=row["document_id"],
            parent_revision_id=row["parent_revision_id"],
            scene_uri=row["scene_uri"],
            scene_checksum_sha256=row["scene_checksum_sha256"],
        )

    def compare_and_swap_current(
        self,
        conn: Connection[Any],
        *,
        document_id: uuid.UUID,
        expected_parent_revision_id: uuid.UUID | None,
        new_revision_id: uuid.UUID,
    ) -> None:
        updated = conn.execute(
            """
            UPDATE drawing.documents
            SET current_revision_id = %s
            WHERE id = %s
              AND current_revision_id IS NOT DISTINCT FROM %s
            RETURNING id
            """,
            (new_revision_id, document_id, expected_parent_revision_id),
        ).fetchone()
        if updated is None:
            raise ConflictError(
                "document current_revision_id changed or document missing"
            )

    def insert_export(
        self,
        conn: Connection[Any],
        *,
        export_id: uuid.UUID,
        revision_id: uuid.UUID,
        kind: str,
        uri: str,
        checksum_sha256: str,
        renderer_version: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO drawing.exports (
              id, revision_id, kind, uri, checksum_sha256, renderer_version
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                export_id,
                revision_id,
                kind,
                uri,
                checksum_sha256,
                renderer_version,
            ),
        )

    def copy_review_items_forward(
        self,
        conn: Connection[Any],
        *,
        source_revision_id: uuid.UUID,
        target_revision_id: uuid.UUID,
        issue_keys: list[str] | None = None,
    ) -> list[str]:
        """Copy unresolved review items; preserve stable issue_key."""
        if issue_keys is None:
            rows = conn.execute(
                """
                SELECT issue_key, object_id, relationship_id, issue_type, severity,
                       crop_uri, proposed_options, state
                FROM drawing.review_items
                WHERE revision_id = %s AND state IN ('open', 'acknowledged_unknown')
                """,
                (source_revision_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT issue_key, object_id, relationship_id, issue_type, severity,
                       crop_uri, proposed_options, state
                FROM drawing.review_items
                WHERE revision_id = %s AND issue_key = ANY(%s)
                """,
                (source_revision_id, issue_keys),
            ).fetchall()
        copied: list[str] = []
        for row in rows:
            conn.execute(
                """
                INSERT INTO drawing.review_items (
                  issue_key, revision_id, object_id, relationship_id,
                  issue_type, severity, crop_uri, proposed_options, state
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                """,
                (
                    row["issue_key"],
                    target_revision_id,
                    row["object_id"],
                    row["relationship_id"],
                    row["issue_type"],
                    row["severity"],
                    row["crop_uri"],
                    json.dumps(row["proposed_options"] or []),
                    row["state"],
                ),
            )
            copied.append(row["issue_key"])
        return copied

    def insert_review_item(
        self,
        conn: Connection[Any],
        *,
        issue_key: str,
        revision_id: uuid.UUID,
        issue_type: str,
        severity: str,
        state: str,
        object_id: str | None = None,
        relationship_id: str | None = None,
        crop_uri: str | None = None,
        proposed_options: list[Any] | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO drawing.review_items (
              issue_key, revision_id, object_id, relationship_id,
              issue_type, severity, crop_uri, proposed_options, state
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            """,
            (
                issue_key,
                revision_id,
                object_id,
                relationship_id,
                issue_type,
                severity,
                crop_uri,
                json.dumps(proposed_options or []),
                state,
            ),
        )

    def insert_review_event(
        self,
        conn: Connection[Any],
        *,
        issue_key: str,
        source_revision_id: uuid.UUID,
        result_revision_id: uuid.UUID,
        actor_id: str,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO drawing.review_events (
              issue_key, source_revision_id, result_revision_id,
              old_value, new_value, actor_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                issue_key,
                source_revision_id,
                result_revision_id,
                old_value,
                new_value,
                actor_id,
            ),
        )

    def get_review_item(
        self,
        conn: Connection[Any],
        revision_id: uuid.UUID,
        item_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        return conn.execute(
            """
            SELECT id, issue_key, object_id, relationship_id, issue_type, severity,
                   crop_uri, proposed_options, state
            FROM drawing.review_items
            WHERE revision_id = %s AND id = %s
            """,
            (revision_id, item_id),
        ).fetchone()

    def set_revision_review_state(
        self,
        conn: Connection[Any],
        revision_id: uuid.UUID,
        review_state: str,
    ) -> None:
        conn.execute(
            """
            UPDATE drawing.scene_revisions
            SET review_state = %s
            WHERE id = %s
            """,
            (review_state, revision_id),
        )

    def promote_revision_to_current(
        self,
        conn: Connection[Any],
        *,
        document_id: uuid.UUID,
        expected_current_revision_id: uuid.UUID,
        candidate_revision_id: uuid.UUID,
    ) -> None:
        updated = conn.execute(
            """
            UPDATE drawing.documents
            SET current_revision_id = %s
            WHERE id = %s AND current_revision_id = %s
            RETURNING id
            """,
            (candidate_revision_id, document_id, expected_current_revision_id),
        ).fetchone()
        if updated is None:
            raise ConflictError(
                "document current_revision_id changed or document missing"
            )

    def get_publish_meta(
        self, conn: Connection[Any], revision_id: uuid.UUID
    ) -> RevisionPublishMeta | None:
        row = conn.execute(
            """
            SELECT author_type, review_state
            FROM drawing.scene_revisions
            WHERE id = %s
            """,
            (revision_id,),
        ).fetchone()
        if row is None:
            return None
        return RevisionPublishMeta(
            author_type=row["author_type"],
            review_state=row["review_state"],
        )

    def get_review_state(
        self, conn: Connection[Any], revision_id: uuid.UUID
    ) -> str | None:
        row = conn.execute(
            """
            SELECT review_state
            FROM drawing.scene_revisions
            WHERE id = %s
            """,
            (revision_id,),
        ).fetchone()
        return row["review_state"] if row else None

    def get_revision(
        self, conn: Connection[Any], revision_id: uuid.UUID
    ) -> SceneRevisionRow | None:
        row = conn.execute(
            """
            SELECT id, document_id, parent_revision_id, scene_uri, scene_checksum_sha256
            FROM drawing.scene_revisions
            WHERE id = %s
            """,
            (revision_id,),
        ).fetchone()
        if row is None:
            return None
        return SceneRevisionRow(
            id=row["id"],
            document_id=row["document_id"],
            parent_revision_id=row["parent_revision_id"],
            scene_uri=row["scene_uri"],
            scene_checksum_sha256=row["scene_checksum_sha256"],
        )

    def list_for_document(
        self, conn: Connection[Any], document_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        return conn.execute(
            """
            SELECT id, parent_revision_id, review_state, validation_status, created_at
            FROM drawing.scene_revisions
            WHERE document_id = %s
            ORDER BY created_at ASC
            """,
            (document_id,),
        ).fetchall()

    def list_review_items(
        self, conn: Connection[Any], revision_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        return conn.execute(
            """
            SELECT id, issue_key, object_id, relationship_id, issue_type, severity,
                   crop_uri, proposed_options, state
            FROM drawing.review_items
            WHERE revision_id = %s
            ORDER BY created_at ASC
            """,
            (revision_id,),
        ).fetchall()

    def get_export(
        self, conn: Connection[Any], revision_id: uuid.UUID, kind: str
    ) -> dict[str, Any] | None:
        return conn.execute(
            """
            SELECT id, kind, uri, checksum_sha256, renderer_version
            FROM drawing.exports
            WHERE revision_id = %s AND kind = %s
            """,
            (revision_id, kind),
        ).fetchone()
