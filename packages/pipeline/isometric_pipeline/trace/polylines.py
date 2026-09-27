"""Extract simplified polylines and blob paths from ink masks."""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from isometric_pipeline.centerlines.graph import (
    _junction_pixels,
    _split_polyline_on_turns,
    _trace_polylines,
)
from isometric_pipeline.centerlines.skeleton import clean_mask, skeletonize
from isometric_pipeline.profiles.loader import GeometryProfile, TraceProfile
from isometric_pipeline.trace.layers import TraceInkLayer


@dataclass(frozen=True)
class TracePath:
    d: str
    fill: str | None
    stroke: str | None


def _geometry_for_trace(trace: TraceProfile, geometry: GeometryProfile) -> GeometryProfile:
    return GeometryProfile(
        min_component_pixels=max(1, trace.min_blob_area_px // 2),
        max_spur_length_px=geometry.max_spur_length_px,
        morph_open_kernel_px=trace.morph_open_kernel_px,
        morph_close_kernel_px=max(1, trace.morph_open_kernel_px),
        skeleton_prune_iterations=geometry.skeleton_prune_iterations,
        max_line_fit_residual_px=geometry.max_line_fit_residual_px,
        min_line_length_px=trace.min_polyline_length_px,
        min_r_squared=geometry.min_r_squared,
        max_chord_deviation_px=geometry.max_chord_deviation_px,
        max_turning_angle_deg=geometry.max_turning_angle_deg,
        stroke_width_percentile=geometry.stroke_width_percentile,
    )


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02x}{g:02x}{b:02x}"


def _polyline_length(poly: list[tuple[float, float]]) -> float:
    total = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:], strict=False):
        total += math.hypot(x1 - x0, y1 - y0)
    return total


def _simplify_polyline(
    poly: list[tuple[int, int]], epsilon: float
) -> list[tuple[float, float]]:
    if len(poly) < 2:
        return []
    arr = np.array([[float(x), float(y)] for y, x in poly], dtype=np.float32)
    simplified = cv2.approxPolyDP(arr, epsilon, False)
    points = [(float(p[0][0]), float(p[0][1])) for p in simplified]
    return points if len(points) >= 2 else []


def _path_from_polyline(points: list[tuple[float, float]]) -> str:
    parts = [f"M {_fmt(points[0][0])} {_fmt(points[0][1])}"]
    for x, y in points[1:]:
        parts.append(f"L {_fmt(x)} {_fmt(y)}")
    return " ".join(parts)


def _fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def extract_layer_paths(
    layer: TraceInkLayer,
    *,
    trace: TraceProfile,
    geometry: GeometryProfile,
) -> tuple[list[TracePath], bool]:
    morph = _geometry_for_trace(trace, geometry)
    cleaned = clean_mask(layer.mask, morph)
    skel = skeletonize(cleaned)
    junctions = _junction_pixels((skel > 0).astype(np.uint8))
    raw_polylines = _trace_polylines((skel > 0).astype(np.uint8), junctions)
    stroke = _rgb_hex(layer.stroke_rgb)
    paths: list[TracePath] = []
    capped = False

    for poly in raw_polylines:
        for segment in _split_polyline_on_turns(poly, geometry.max_turning_angle_deg):
            simplified = _simplify_polyline(segment, trace.simplify_epsilon_px)
            if len(simplified) < 2:
                continue
            if _polyline_length(simplified) < trace.min_polyline_length_px:
                continue
            paths.append(
                TracePath(
                    d=_path_from_polyline(simplified),
                    fill=None,
                    stroke=stroke,
                )
            )
            if len(paths) >= trace.max_paths_per_layer:
                capped = True
                return paths, capped

    binary = (cleaned > 0).astype(np.uint8)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    skel_pixels = int(np.count_nonzero(skel))
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < trace.min_blob_area_px:
            continue
        if skel_pixels > 0 and area < trace.min_blob_area_px * 3:
            continue
        component = (labels == label).astype(np.uint8) * 255
        contours, _ = cv2.findContours(
            component, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for contour in contours:
            if cv2.contourArea(contour) < trace.min_blob_area_px:
                continue
            approx = cv2.approxPolyDP(
                contour, trace.simplify_epsilon_px, True
            )
            if len(approx) < 3:
                continue
            points = [(float(p[0][0]), float(p[0][1])) for p in approx]
            d = _path_from_polyline(points + [points[0]])
            paths.append(TracePath(d=d, fill=stroke, stroke=None))
            if len(paths) >= trace.max_paths_per_layer:
                capped = True
                return paths, capped

    return paths, capped
