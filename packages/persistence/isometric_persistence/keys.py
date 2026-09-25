"""Immutable artifact key helpers from architecture section 6."""

from __future__ import annotations

import uuid


def document_original_key(document_id: uuid.UUID) -> str:
    return f"documents/{document_id}/original"


def document_display_key(document_id: uuid.UUID) -> str:
    return f"documents/{document_id}/display.png"


def document_page_key(document_id: uuid.UUID) -> str:
    return f"documents/{document_id}/page.png"


def document_normalize_metadata_key(document_id: uuid.UUID) -> str:
    return f"documents/{document_id}/normalize.json"


def document_masks_metadata_key(document_id: uuid.UUID) -> str:
    return f"documents/{document_id}/masks.json"


def document_regions_metadata_key(document_id: uuid.UUID) -> str:
    return f"documents/{document_id}/regions.json"


def document_mask_key(document_id: uuid.UUID, name: str) -> str:
    return f"documents/{document_id}/masks/{name}.png"


def document_color_mask_key(document_id: uuid.UUID, layer_id: str) -> str:
    return f"documents/{document_id}/masks/color/{layer_id}.png"


def document_crop_key(document_id: uuid.UUID, crop_id: str) -> str:
    return f"documents/{document_id}/crops/{crop_id}.png"


def job_stage_artifact_key(job_id: uuid.UUID, stage: str, content_hash: str) -> str:
    return f"jobs/{job_id}/stages/{stage}/{content_hash}"


def revision_scene_key(document_id: uuid.UUID, revision_id: uuid.UUID) -> str:
    return f"documents/{document_id}/revisions/{revision_id}/scene.json"


def revision_export_key(
    document_id: uuid.UUID, revision_id: uuid.UUID, format: str
) -> str:
    return f"documents/{document_id}/exports/{revision_id}/{format}"
