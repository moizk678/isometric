"""Immutable artifact key helpers from architecture section 6."""

from __future__ import annotations

import uuid


def document_original_key(document_id: uuid.UUID) -> str:
    return f"documents/{document_id}/original"


def job_stage_artifact_key(job_id: uuid.UUID, stage: str, content_hash: str) -> str:
    return f"jobs/{job_id}/stages/{stage}/{content_hash}"


def revision_scene_key(document_id: uuid.UUID, revision_id: uuid.UUID) -> str:
    return f"documents/{document_id}/revisions/{revision_id}/scene.json"


def revision_export_key(
    document_id: uuid.UUID, revision_id: uuid.UUID, format: str
) -> str:
    return f"documents/{document_id}/exports/{revision_id}/{format}"
