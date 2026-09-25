"""Grid, ink, and color separation stage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

import numpy as np

from isometric_pipeline.masks.artifact import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    WARNING_GRID_LOW_CONFIDENCE,
    ColorLayerRecord,
    GridDiagnostics,
    MaskArtifactRef,
    MasksMetadata,
)
from isometric_pipeline.masks.color import KMEANS_SEED, separate_color_layers
from isometric_pipeline.masks.diagnostics import masks_overlay_png
from isometric_pipeline.masks.grid import GRID_CONFIDENCE_MIN, estimate_grid
from isometric_pipeline.masks.ink import estimate_retained_ink
from isometric_pipeline.masks.util import decode_page_rgb, encode_mask_png
from isometric_pipeline.normalize.page import json_bytes

StageStatus = Literal["succeeded", "partial"]


@dataclass(frozen=True)
class SeparateMasksResult:
    status: StageStatus
    masks: dict[str, bytes]
    color_layer_masks: dict[str, bytes]
    metadata: MasksMetadata
    overlay_png: bytes
    warnings: list[str]
    metrics: dict[str, float | int | bool]
    content_hash: str


def separate_masks(
    page_png: bytes,
    *,
    document_id: str,
    page_uri: str,
    masks_json_uri: str,
) -> SeparateMasksResult:
    rgb = decode_page_rgb(page_png)
    height, width = rgb.shape[:2]
    page_hash = hashlib.sha256(page_png).hexdigest()

    grid_mask, grid_confidence, paper = estimate_grid(rgb)
    warnings: list[str] = []
    apply_grid = grid_confidence >= GRID_CONFIDENCE_MIN
    if not apply_grid and np.count_nonzero(grid_mask) > 0:
        grid_mask = np.zeros_like(grid_mask)
    if grid_confidence < GRID_CONFIDENCE_MIN:
        warnings.append(WARNING_GRID_LOW_CONFIDENCE)

    retained_ink = estimate_retained_ink(
        rgb,
        grid_mask,
        grid_confidence=grid_confidence,
        apply_grid_removal=apply_grid,
    )
    color_sep = separate_color_layers(rgb, retained_ink)

    protection = np.zeros((height, width), dtype=np.uint8)
    geometry_ink = retained_ink.copy()

    prefix = f"documents/{document_id}/masks"
    grid_uri = f"{prefix}/grid.png"
    retained_uri = f"{prefix}/retained-ink.png"
    black_uri = f"{prefix}/black-ink.png"
    unclassified_uri = f"{prefix}/unclassified-ink.png"
    geometry_uri = f"{prefix}/geometry-ink.png"
    protection_uri = f"{prefix}/protection.png"

    masks: dict[str, bytes] = {
        "grid": encode_mask_png(grid_mask),
        "retained_ink": encode_mask_png(retained_ink),
        "black_ink": encode_mask_png(color_sep.black_ink_mask),
        "unclassified_ink": encode_mask_png(color_sep.unclassified_ink_mask),
        "geometry_ink": encode_mask_png(geometry_ink),
        "protection": encode_mask_png(protection),
    }

    color_layer_masks: dict[str, bytes] = {}
    layer_records: list[ColorLayerRecord] = []
    for layer_id, layer_mask, normalized_rgb in color_sep.color_layers:
        layer_uri = f"{prefix}/color/{layer_id}.png"
        color_layer_masks[layer_id] = encode_mask_png(layer_mask)
        layer_records.append(
            ColorLayerRecord(
                layer_id=layer_id,
                mask_uri=layer_uri,
                normalized_rgb=normalized_rgb,
                pixel_count=int(np.count_nonzero(layer_mask)),
            )
        )

    metadata = MasksMetadata(
        schema_version=SCHEMA_VERSION,
        producer_version=PRODUCER_VERSION,
        page_width_px=width,
        page_height_px=height,
        page_hash=page_hash,
        grid_mask=MaskArtifactRef(uri=grid_uri, width_px=width, height_px=height),
        retained_ink_mask=MaskArtifactRef(
            uri=retained_uri, width_px=width, height_px=height
        ),
        black_ink_mask=MaskArtifactRef(uri=black_uri, width_px=width, height_px=height),
        unclassified_ink_mask=MaskArtifactRef(
            uri=unclassified_uri, width_px=width, height_px=height
        ),
        geometry_ink_mask=MaskArtifactRef(
            uri=geometry_uri, width_px=width, height_px=height
        ),
        protection_mask=MaskArtifactRef(
            uri=protection_uri, width_px=width, height_px=height
        ),
        color_layers=layer_records,
        diagnostics=GridDiagnostics(
            grid_confidence=grid_confidence,
            paper_lightness=paper,
            grid_pixel_count=int(np.count_nonzero(grid_mask)),
            retained_ink_pixel_count=int(np.count_nonzero(retained_ink)),
        ),
        parameters={
            "grid_confidence_min": GRID_CONFIDENCE_MIN,
            "kmeans_seed": KMEANS_SEED,
        },
        warnings=warnings,
    )

    overlay_png = masks_overlay_png(rgb, grid_mask, retained_ink, protection)
    wire = metadata.to_wire()
    content_hash = hashlib.sha256(
        json_bytes(wire) + page_png + masks["grid"] + masks["retained_ink"]
    ).hexdigest()

    status: StageStatus = "partial" if warnings else "succeeded"
    metrics = {
        "grid_confidence": grid_confidence,
        "grid_pixels": int(np.count_nonzero(grid_mask)),
        "retained_ink_pixels": int(np.count_nonzero(retained_ink)),
        "color_layers": len(layer_records),
    }

    return SeparateMasksResult(
        status=status,
        masks=masks,
        color_layer_masks=color_layer_masks,
        metadata=metadata,
        overlay_png=overlay_png,
        warnings=warnings,
        metrics=metrics,
        content_hash=content_hash,
    )
