"""Revision publish CAS rules for initial jobs vs reprocess candidates."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from isometric_persistence.repositories.documents import DocumentRepository
from isometric_persistence.repositories.revisions import RevisionRepository
from psycopg import Connection


@dataclass(frozen=True)
class PublishPolicy:
    expected_parent_revision_id: uuid.UUID | None
    scene_parent_revision_id: uuid.UUID | None
    advance_current_revision: bool


def resolve_publish_policy(
    conn: Connection,
    *,
    document_id: uuid.UUID,
    revs: RevisionRepository,
) -> PublishPolicy:
    docs = DocumentRepository()
    document = docs.get(conn, document_id)
    if document is None or document.current_revision_id is None:
        return PublishPolicy(None, None, True)
    current = document.current_revision_id
    meta = revs.get_publish_meta(conn, current)
    if meta is None:
        return PublishPolicy(current, current, True)
    if meta.author_type != "machine" or meta.review_state == "ready":
        return PublishPolicy(current, current, False)
    return PublishPolicy(current, current, True)
