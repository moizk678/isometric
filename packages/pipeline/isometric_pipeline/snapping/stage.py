"""Snap fitted primitives to inferred isometric axes."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

import numpy as np

from isometric_pipeline.centerlines.util import decode_mask_png
from isometric_pipeline.masks.util import decode_page_rgb
from isometric_pipeline.normalize.page import json_bytes
from isometric_pipeline.primitives.artifact import PrimitivesMetadata
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.artifact import RegionsMetadata
from isometric_pipeline.snapping.align import align_snapped_endpoints
from isometric_pipeline.snapping.artifact import (
    AXES_PRODUCER_VERSION,
    AXES_SCHEMA_VERSION,
    SNAPPED_PRODUCER_VERSION,
    SNAPPED_SCHEMA_VERSION,
    AxesMetadata,
    SnappedPrimitivesMetadata,
)
from isometric_pipeline.snapping.axes import infer_axis_model
from isometric_pipeline.snapping.diagnostics import snapping_overlay_png
from isometric_pipeline.snapping.snap import snap_all_primitives

StageStatus = Literal["succeeded", "partial"]


@dataclass(frozen=True)
class SnapPrimitivesResult:
    status: StageStatus
    axes_metadata: AxesMetadata
    snapped_metadata: SnappedPrimitivesMetadata
    axes_json: bytes
    snapped_primitives_json: bytes
    overlay_png: bytes
    warnings: list[str]
    metrics: dict[str, float | int | bool]
    content_hash: str


def snap_primitives(
    page_png: bytes,
    primitives: PrimitivesMetadata,
    *,
    primitives_json_uri: str,
    axes_json_uri: str,
    snapped_primitives_json_uri: str,
    masks_json_uri: str | None = None,
    regions: RegionsMetadata | None = None,
    regions_json_uri: str | None = None,
    grid_mask_png: bytes | None = None,
    grid_confidence: float | None = None,
    profile_version: str = DEFAULT_PIPING_PROFILE_VERSION,
) -> SnapPrimitivesResult:
    profile = load_piping_profile(profile_version)
    snap_profile = profile.snapping
    rgb = decode_page_rgb(page_png)
    height, width = rgb.shape[:2]

    grid_mask: np.ndarray | None = None
    if grid_mask_png is not None:
        grid_mask = decode_mask_png(grid_mask_png, height, width)

    axis_model = infer_axis_model(
        primitives.primitives,
        snap_profile,
        grid_confidence=grid_confidence,
        grid_mask=grid_mask,
    )

    warnings: list[str] = []
    if axis_model.model_confidence < snap_profile.min_axis_model_confidence:
        warnings.append("axis_model_low_confidence")

    region_list = regions.regions if regions is not None else []
    candidates = snap_all_primitives(
        primitives.primitives,
        axis_model,
        snap_profile,
        region_list,
    )
    candidates = align_snapped_endpoints(candidates, snap_profile)

    axes_meta = AxesMetadata(
        schema_version=AXES_SCHEMA_VERSION,
        producer_version=AXES_PRODUCER_VERSION,
        profile_version=profile_version,
        page_width_px=width,
        page_height_px=height,
        primitives_metadata_uri=primitives_json_uri,
        masks_metadata_uri=masks_json_uri,
        inference_method=axis_model.inference_method,
        rotation_deg=axis_model.rotation_deg,
        axes=axis_model.axes,
        model_confidence=axis_model.model_confidence,
        grid_confidence=grid_confidence,
        warnings=warnings,
    )

    snapped_meta = SnappedPrimitivesMetadata(
        schema_version=SNAPPED_SCHEMA_VERSION,
        producer_version=SNAPPED_PRODUCER_VERSION,
        profile_version=profile_version,
        page_width_px=width,
        page_height_px=height,
        primitives_metadata_uri=primitives_json_uri,
        axes_metadata_uri=axes_json_uri,
        regions_metadata_uri=regions_json_uri,
        candidates=candidates,
        warnings=warnings,
    )

    axes_json = json_bytes(axes_meta.to_wire())
    snapped_json = json_bytes(snapped_meta.to_wire())
    overlay_png = snapping_overlay_png(rgb, candidates, axes_meta)
    content_hash = hashlib.sha256(axes_json + snapped_json + overlay_png).hexdigest()

    snapped_count = sum(1 for c in candidates if c.status == "snapped")
    preserved_count = sum(1 for c in candidates if c.status == "preserved")

    metrics = {
        "candidate_count": len(candidates),
        "snapped_count": snapped_count,
        "preserved_count": preserved_count,
        "axis_model_confidence": axis_model.model_confidence,
        "axis_count": len(axis_model.axes),
    }

    status: StageStatus = "partial" if warnings else "succeeded"
    return SnapPrimitivesResult(
        status=status,
        axes_metadata=axes_meta,
        snapped_metadata=snapped_meta,
        axes_json=axes_json,
        snapped_primitives_json=snapped_json,
        overlay_png=overlay_png,
        warnings=warnings,
        metrics=metrics,
        content_hash=content_hash,
    )
