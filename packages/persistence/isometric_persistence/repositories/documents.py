"""Document repository."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from psycopg import Connection


@dataclass(frozen=True)
class DocumentRow:
    id: uuid.UUID
    owner_id: str
    source_hash: str
    source_uri: str
    source_mime: str
    current_revision_id: uuid.UUID | None
    upload_idempotency_key: str | None = None
    upload_options_hash: str | None = None
    source_width_px: int | None = None
    source_height_px: int | None = None
    created_at: object | None = None
    original_filename: str | None = None
    profile_id: str | None = None


class DocumentRepository:
    def create(
        self,
        conn: Connection[Any],
        *,
        document_id: uuid.UUID | None = None,
        owner_id: str,
        source_hash: str,
        source_uri: str,
        source_mime: str,
        upload_idempotency_key: str | None = None,
        upload_options_hash: str | None = None,
        source_width_px: int | None = None,
        source_height_px: int | None = None,
        original_filename: str | None = None,
        profile_id: str | None = None,
    ) -> DocumentRow:
        row = conn.execute(
            """
            INSERT INTO drawing.documents (
              id, owner_id, source_hash, source_uri, source_mime,
              upload_idempotency_key, upload_options_hash,
              source_width_px, source_height_px,
              original_filename, profile_id
            )
            VALUES (
              COALESCE(%s, gen_random_uuid()), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id, owner_id, source_hash, source_uri, source_mime,
                      current_revision_id, upload_idempotency_key, upload_options_hash,
                      source_width_px, source_height_px, created_at,
                      original_filename, profile_id
            """,
            (
                document_id,
                owner_id,
                source_hash,
                source_uri,
                source_mime,
                upload_idempotency_key,
                upload_options_hash,
                source_width_px,
                source_height_px,
                original_filename,
                profile_id,
            ),
        ).fetchone()
        assert row is not None
        return _row_to_document(row)

    def get(self, conn: Connection[Any], document_id: uuid.UUID) -> DocumentRow | None:
        row = conn.execute(
            """
            SELECT id, owner_id, source_hash, source_uri, source_mime, current_revision_id,
                   upload_idempotency_key, upload_options_hash,
                   source_width_px, source_height_px, created_at,
                   original_filename, profile_id
            FROM drawing.documents
            WHERE id = %s
            """,
            (document_id,),
        ).fetchone()
        return _row_to_document(row) if row else None

    def find_by_idempotency(
        self, conn: Connection[Any], *, owner_id: str, idempotency_key: str
    ) -> DocumentRow | None:
        row = conn.execute(
            """
            SELECT id, owner_id, source_hash, source_uri, source_mime, current_revision_id,
                   upload_idempotency_key, upload_options_hash,
                   source_width_px, source_height_px, created_at,
                   original_filename, profile_id
            FROM drawing.documents
            WHERE owner_id = %s AND upload_idempotency_key = %s
            """,
            (owner_id, idempotency_key),
        ).fetchone()
        return _row_to_document(row) if row else None

    def list_for_owner(
        self,
        conn: Connection[Any],
        *,
        owner_id: str,
        limit: int,
        offset: int,
    ) -> list[DocumentRow]:
        rows = conn.execute(
            """
            SELECT id, owner_id, source_hash, source_uri, source_mime, current_revision_id,
                   upload_idempotency_key, upload_options_hash,
                   source_width_px, source_height_px, created_at,
                   original_filename, profile_id
            FROM drawing.documents
            WHERE owner_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (owner_id, limit, offset),
        ).fetchall()
        return [_row_to_document(row) for row in rows]


def _row_to_document(row: dict[str, Any]) -> DocumentRow:
    return DocumentRow(
        id=row["id"],
        owner_id=row["owner_id"],
        source_hash=row["source_hash"],
        source_uri=row["source_uri"],
        source_mime=row["source_mime"],
        current_revision_id=row["current_revision_id"],
        upload_idempotency_key=row.get("upload_idempotency_key"),
        upload_options_hash=row.get("upload_options_hash"),
        source_width_px=row.get("source_width_px"),
        source_height_px=row.get("source_height_px"),
        created_at=row.get("created_at"),
        original_filename=row.get("original_filename"),
        profile_id=row.get("profile_id"),
    )
