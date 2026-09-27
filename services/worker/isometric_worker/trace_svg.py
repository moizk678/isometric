"""Build or read document-level trace.svg from persisted mask artifacts."""

from __future__ import annotations

import json
import logging
import uuid

from isometric_persistence.artifacts import ArtifactStore
from isometric_persistence.errors import PersistenceError
from isometric_persistence.keys import (
    document_color_mask_key,
    document_mask_key,
    document_masks_metadata_key,
    document_trace_key,
)
from isometric_pipeline.masks.artifact import MasksMetadata
from isometric_pipeline.profiles.loader import load_piping_profile, resolve_piping_profile_version
from isometric_pipeline.trace import TraceInkResult, trace_ink

logger = logging.getLogger(__name__)


def _load_trace_inputs(
    store: ArtifactStore, document_id: uuid.UUID
) -> tuple[bytes, MasksMetadata, dict[str, bytes], bytes, bytes]:
    masks_meta_key = document_masks_metadata_key(document_id)
    geometry_ink = store.read(document_mask_key(document_id, "geometry-ink"))
    black_ink = store.read(document_mask_key(document_id, "black-ink"))
    unclassified = store.read(document_mask_key(document_id, "unclassified-ink"))
    masks_wire = json.loads(store.read(masks_meta_key).decode("utf-8"))
    masks_metadata = MasksMetadata.model_validate(masks_wire)
    color_layer_masks: dict[str, bytes] = {}
    for layer in masks_metadata.color_layers:
        try:
            color_layer_masks[layer.layer_id] = store.read(
                document_color_mask_key(document_id, layer.layer_id)
            )
        except (FileNotFoundError, PersistenceError, OSError):
            continue
    return geometry_ink, masks_metadata, color_layer_masks, black_ink, unclassified


def run_document_trace(
    store: ArtifactStore,
    document_id: uuid.UUID,
    profile_version: str,
) -> TraceInkResult:
    """Vectorize persisted masks and overwrite documents/{id}/trace.svg."""
    resolved = resolve_piping_profile_version(profile_version)
    profile = load_piping_profile(resolved)
    geometry_ink, masks_metadata, color_layer_masks, black_ink, unclassified = (
        _load_trace_inputs(store, document_id)
    )
    traced = trace_ink(
        geometry_ink_png=geometry_ink,
        masks_metadata=masks_metadata,
        color_layer_masks=color_layer_masks,
        black_ink_png=black_ink,
        unclassified_ink_png=unclassified,
        profile=profile,
    )
    trace_key = document_trace_key(document_id)
    store.write_immutable(trace_key, traced.svg)
    return traced


def read_document_trace(store: ArtifactStore, document_id: uuid.UUID) -> bytes | None:
    try:
        return store.read(document_trace_key(document_id))
    except (FileNotFoundError, PersistenceError, OSError):
        return None


def read_or_build_document_trace(
    store: ArtifactStore,
    document_id: uuid.UUID,
    profile_version: str,
) -> bytes | None:
    existing = read_document_trace(store, document_id)
    if existing:
        return existing
    try:
        return run_document_trace(store, document_id, profile_version).svg
    except Exception:
        logger.exception("failed to build trace.svg for document %s", document_id)
        return None
