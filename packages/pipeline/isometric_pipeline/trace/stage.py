"""Trace ink masks into raster-faithful SVG."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

import numpy as np

from isometric_pipeline.masks.artifact import MasksMetadata
from isometric_pipeline.profiles.loader import PipingIsometricProfile
from isometric_pipeline.trace.artifact import (
    PRODUCER_VERSION,
    WARNING_EMPTY_INK,
    WARNING_PATH_CAP,
)
from isometric_pipeline.trace.layers import build_trace_layers
from isometric_pipeline.trace.polylines import extract_layer_paths
from isometric_pipeline.trace.svg import render_trace_svg, trace_svg_sha256
from isometric_pipeline.trace.validate import TraceSvgError, validate_trace_svg

StageStatus = Literal["succeeded", "partial"]


@dataclass(frozen=True)
class TraceInkResult:
    status: StageStatus
    svg: bytes
    sha256: str
    warnings: list[str]
    metrics: dict[str, float | int | bool]
    content_hash: str


def trace_ink(
    *,
    geometry_ink_png: bytes,
    masks_metadata: MasksMetadata,
    color_layer_masks: dict[str, bytes],
    black_ink_png: bytes,
    unclassified_ink_png: bytes,
    profile: PipingIsometricProfile,
) -> TraceInkResult:
    trace = profile.trace
    warnings: list[str] = list(masks_metadata.warnings)
    layers, geometry = build_trace_layers(
        geometry_ink_png=geometry_ink_png,
        masks_metadata=masks_metadata,
        color_layer_masks=color_layer_masks,
        black_ink_png=black_ink_png,
        unclassified_ink_png=unclassified_ink_png,
        include_unclassified=trace.include_unclassified,
    )
    if not np.any(geometry > 0):
        warnings.append(WARNING_EMPTY_INK)

    layer_paths: list[tuple[str, list]] = []
    path_cap_hit = False
    total_paths = 0
    for layer in layers:
        paths, capped = extract_layer_paths(
            layer, trace=trace, geometry=profile.geometry
        )
        if capped:
            path_cap_hit = True
        if paths:
            layer_paths.append((layer.layer_id, paths))
            total_paths += len(paths)

    if path_cap_hit:
        warnings.append(WARNING_PATH_CAP)

    svg = render_trace_svg(
        width_px=masks_metadata.page_width_px,
        height_px=masks_metadata.page_height_px,
        page_hash=masks_metadata.page_hash,
        layer_paths=layer_paths,
        stroke_width_px=trace.stroke_width_px,
    )
    try:
        validate_trace_svg(
            svg,
            width_px=masks_metadata.page_width_px,
            height_px=masks_metadata.page_height_px,
        )
    except TraceSvgError as exc:
        raise ValueError(str(exc)) from exc

    digest = trace_svg_sha256(svg)
    content_hash = hashlib.sha256(
        geometry_ink_png + digest.encode("ascii") + PRODUCER_VERSION.encode("ascii")
    ).hexdigest()
    status: StageStatus = "partial" if warnings else "succeeded"
    metrics: dict[str, float | int | bool] = {
        "trace_layers": len(layer_paths),
        "trace_paths": total_paths,
        "geometry_ink_pixels": int(np.count_nonzero(geometry > 0)),
    }
    return TraceInkResult(
        status=status,
        svg=svg,
        sha256=digest,
        warnings=warnings,
        metrics=metrics,
        content_hash=content_hash,
    )
