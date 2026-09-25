"""Protected region detection stage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

import numpy as np

from isometric_pipeline.masks.artifact import MasksMetadata
from isometric_pipeline.masks.diagnostics import masks_overlay_png
from isometric_pipeline.masks.util import decode_page_rgb, encode_mask_png
from isometric_pipeline.normalize.page import json_bytes
from isometric_pipeline.regions.artifact import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    RegionsMetadata,
)
from isometric_pipeline.regions.heuristics import (
    build_protection_mask,
    propose_regions,
)

StageStatus = Literal["succeeded", "partial"]


@dataclass(frozen=True)
class DetectRegionsResult:
    status: StageStatus
    regions_metadata: RegionsMetadata
    regions_json: bytes
    crop_pngs: dict[str, bytes]
    protection_png: bytes
    geometry_ink_png: bytes
    updated_masks_metadata: MasksMetadata
    masks_json: bytes
    overlay_png: bytes
    warnings: list[str]
    metrics: dict[str, float | int | bool]
    content_hash: str


def detect_regions(
    page_png: bytes,
    masks_metadata: MasksMetadata,
    retained_ink_png: bytes,
    black_ink_png: bytes,
    *,
    document_id: str,
    masks_json_uri: str,
) -> DetectRegionsResult:
    rgb = decode_page_rgb(page_png)
    height, width = rgb.shape[:2]
    retained = _decode_mask(retained_ink_png, height, width)
    black_ink = _decode_mask(black_ink_png, height, width)

    annotation_mask = black_ink.copy()
    crops_prefix = f"documents/{document_id}/crops"
    regions, crop_pngs = propose_regions(rgb, annotation_mask, crops_prefix)

    protection = build_protection_mask(height, width, regions, annotation_mask)
    geometry_ink = retained.copy()
    geometry_ink[protection > 0] = 0

    prefix = f"documents/{document_id}/masks"
    protection_uri = f"{prefix}/protection.png"
    geometry_uri = f"{prefix}/geometry-ink.png"

    updated_masks = masks_metadata.model_copy(deep=True)
    updated_masks.geometry_ink_mask.uri = geometry_uri
    updated_masks.protection_mask.uri = protection_uri

    regions_meta = RegionsMetadata(
        schema_version=SCHEMA_VERSION,
        producer_version=PRODUCER_VERSION,
        page_width_px=width,
        page_height_px=height,
        masks_metadata_uri=masks_json_uri,
        regions=regions,
        protection_mask_uri=protection_uri,
        geometry_ink_mask_uri=geometry_uri,
        warnings=[],
    )

    protection_png = encode_mask_png(protection)
    geometry_ink_png = encode_mask_png(geometry_ink)
    regions_json = json_bytes(regions_meta.to_wire())
    masks_json = json_bytes(updated_masks.to_wire())
    boxes = [
        (
            int(r.bbox.x),
            int(r.bbox.y),
            int(r.bbox.x + r.bbox.width),
            int(r.bbox.y + r.bbox.height),
        )
        for r in regions
    ]
    overlay_png = masks_overlay_png(
        rgb, _zeros(height, width), retained, protection, boxes
    )

    content_hash = hashlib.sha256(
        regions_json + protection_png + geometry_ink_png
    ).hexdigest()

    metrics = {
        "region_count": len(regions),
        "protection_pixels": int(np.count_nonzero(protection)),
        "geometry_ink_pixels": int(np.count_nonzero(geometry_ink)),
    }

    return DetectRegionsResult(
        status="succeeded",
        regions_metadata=regions_meta,
        regions_json=regions_json,
        crop_pngs=crop_pngs,
        protection_png=protection_png,
        geometry_ink_png=geometry_ink_png,
        updated_masks_metadata=updated_masks,
        masks_json=masks_json,
        overlay_png=overlay_png,
        warnings=[],
        metrics=metrics,
        content_hash=content_hash,
    )


def _decode_mask(png: bytes, height: int, width: int) -> np.ndarray:
    import io

    from PIL import Image

    with Image.open(io.BytesIO(png)) as image:
        gray = np.array(image.convert("L"))
    if gray.shape != (height, width):
        raise ValueError("mask dimensions do not match page")
    return gray


def _zeros(height: int, width: int) -> np.ndarray:
    return np.zeros((height, width), dtype=np.uint8)
