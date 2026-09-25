"""Primitive fitting stage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

import numpy as np

from isometric_pipeline.centerlines.artifact import CenterlinesMetadata
from isometric_pipeline.centerlines.util import decode_mask_png
from isometric_pipeline.masks.util import decode_page_rgb
from isometric_pipeline.normalize.page import json_bytes
from isometric_pipeline.primitives.artifact import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    PrimitiveCandidate,
    PrimitiveRejection,
    PrimitivesMetadata,
    UnresolvedEvidence,
)
from isometric_pipeline.primitives.diagnostics import primitives_overlay_png
from isometric_pipeline.primitives.fit import (
    edge_bbox,
    estimate_stroke_width,
    fit_line,
    is_straight_enough,
)
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)

StageStatus = Literal["succeeded", "partial"]


@dataclass(frozen=True)
class FitPrimitivesResult:
    status: StageStatus
    metadata: PrimitivesMetadata
    primitives_json: bytes
    overlay_png: bytes
    warnings: list[str]
    metrics: dict[str, float | int | bool]
    content_hash: str


def fit_primitives(
    page_png: bytes,
    centerlines: CenterlinesMetadata,
    layer_masks: dict[str, bytes],
    *,
    centerlines_json_uri: str,
    masks_json_uri: str,
    regions_json_uri: str | None,
    primitives_json_uri: str,
    profile_version: str = DEFAULT_PIPING_PROFILE_VERSION,
) -> FitPrimitivesResult:
    profile = load_piping_profile(profile_version)
    geo = profile.geometry
    rgb = decode_page_rgb(page_png)
    height, width = rgb.shape[:2]

    mask_by_layer: dict[str, np.ndarray] = {}
    for layer in centerlines.layers:
        png = layer_masks.get(layer.layer_id)
        if png is None and layer.layer_id == "geometry":
            png = layer_masks.get("geometry")
        if png is None:
            continue
        mask_by_layer[layer.layer_id] = decode_mask_png(png, height, width)

    primitives: list[PrimitiveCandidate] = []
    unresolved: list[UnresolvedEvidence] = []
    rejections: list[PrimitiveRejection] = []
    warnings: list[str] = []
    prim_index = 0
    unresolved_index = 0
    rejection_index = 0

    layer_uri = {layer.layer_id: layer.mask_uri for layer in centerlines.layers}

    for edge in centerlines.edges:
        samples = edge.samples
        if len(samples) < 2:
            rejections.append(
                PrimitiveRejection(
                    id=f"rej_{rejection_index:04d}",
                    centerline_edge_id=edge.id,
                    component_id=edge.component_id,
                    reason="insufficient_samples",
                    diagnostic_index=rejection_index,
                )
            )
            rejection_index += 1
            continue

        if not is_straight_enough(samples, geo):
            unresolved.append(
                UnresolvedEvidence(
                    id=f"unres_{unresolved_index:04d}",
                    layer_id=edge.layer_id,
                    component_id=edge.component_id,
                    centerline_edge_id=edge.id,
                    samples=samples,
                    bbox=edge_bbox(samples),
                    evidence="non_straight_stroke",
                )
            )
            unresolved_index += 1
            continue

        start, end, rms, r_squared = fit_line(samples)
        length = float(np.hypot(end.x - start.x, end.y - start.y))
        mask = mask_by_layer.get(edge.layer_id)
        stroke_width = (
            estimate_stroke_width(mask, edge, geo) if mask is not None else 1.0
        )

        status: Literal["accepted", "uncertain", "rejected"] = "accepted"
        if length < geo.min_line_length_px or rms > geo.max_line_fit_residual_px:
            status = "rejected"
        elif r_squared < geo.min_r_squared:
            status = "uncertain"

        if status == "rejected":
            rejections.append(
                PrimitiveRejection(
                    id=f"rej_{rejection_index:04d}",
                    centerline_edge_id=edge.id,
                    component_id=edge.component_id,
                    reason="fit_threshold",
                    diagnostic_index=rejection_index,
                )
            )
            rejection_index += 1
            continue

        confidence = max(0.0, min(1.0, r_squared * (1.0 - min(rms / 10.0, 0.5))))
        prim_id = f"prim_{prim_index:04d}"
        prim_index += 1
        primitives.append(
            PrimitiveCandidate(
                id=prim_id,
                layer_id=edge.layer_id,
                kind="line",
                start=start,
                end=end,
                samples=samples,
                residual_rms_px=rms,
                stroke_width_px=stroke_width,
                fit_metric=r_squared,
                confidence=confidence,
                status=status,
                centerline_edge_id=edge.id,
                component_id=edge.component_id,
                mask_uri=layer_uri.get(edge.layer_id, ""),
                evidence=f"edge_samples={len(samples)}",
            )
        )

    metadata = PrimitivesMetadata(
        schema_version=SCHEMA_VERSION,
        producer_version=PRODUCER_VERSION,
        profile_version=profile_version,
        page_width_px=width,
        page_height_px=height,
        centerlines_metadata_uri=centerlines_json_uri,
        masks_metadata_uri=masks_json_uri,
        regions_metadata_uri=regions_json_uri,
        primitives=primitives,
        unresolved=unresolved,
        rejections=rejections,
        warnings=warnings,
    )
    primitives_json = json_bytes(metadata.to_wire())
    overlay_png = primitives_overlay_png(rgb, primitives, unresolved)
    content_hash = hashlib.sha256(primitives_json + overlay_png).hexdigest()

    metrics = {
        "primitive_count": len(primitives),
        "accepted_primitive_count": sum(
            1 for p in primitives if p.status == "accepted"
        ),
        "uncertain_primitive_count": sum(
            1 for p in primitives if p.status == "uncertain"
        ),
        "unresolved_count": len(unresolved),
        "rejection_count": len(rejections),
    }
    status: StageStatus = "partial" if warnings else "succeeded"
    return FitPrimitivesResult(
        status=status,
        metadata=metadata,
        primitives_json=primitives_json,
        overlay_png=overlay_png,
        warnings=warnings,
        metrics=metrics,
        content_hash=content_hash,
    )
