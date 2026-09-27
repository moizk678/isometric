"""Deterministic scene object UUIDs from pipeline candidate IDs."""

from __future__ import annotations

import uuid

SCENE_OBJECT_NAMESPACE = uuid.UUID("7c4e2a10-9b3d-4e1f-a6c5-2d8f91e0b14a")
SCENE_LAYER_NAMESPACE = uuid.UUID("8d5f3b21-ac4e-4f2a-b7d6-3e9a02f1c25b")


def scene_object_id(document_id: uuid.UUID, candidate_id: str) -> str:
    return str(uuid.uuid5(SCENE_OBJECT_NAMESPACE, f"{document_id}:{candidate_id}"))


def scene_layer_id(document_id: uuid.UUID, layer_key: str) -> str:
    return str(uuid.uuid5(SCENE_LAYER_NAMESPACE, f"{document_id}:{layer_key}"))
