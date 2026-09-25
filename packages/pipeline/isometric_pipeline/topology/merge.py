"""Collinear fragment merging with ink-bridge evidence."""

from __future__ import annotations

import math

import numpy as np

from isometric_pipeline.profiles.loader import TopologyProfile
from isometric_pipeline.topology.segments import (
    WorkingSegment,
    collinear_compatible,
    point_distance,
)


def _ink_bridge_coverage(
    mask: np.ndarray | None,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    profile: TopologyProfile,
) -> float:
    if mask is None:
        return 0.0
    h, w = mask.shape
    length = point_distance(x0, y0, x1, y1)
    if length < 1.0:
        return 0.0
    step = max(1.0, profile.ink_bridge_sample_step_px)
    samples = int(max(2, math.ceil(length / step)))
    hits = 0
    for i in range(samples):
        t = i / (samples - 1)
        x = x0 + t * (x1 - x0)
        y = y0 + t * (y1 - y0)
        ix = int(round(x))
        iy = int(round(y))
        if 0 <= ix < w and 0 <= iy < h and mask[iy, ix] > 0:
            hits += 1
    return hits / samples


def _try_merge_pair(
    a: WorkingSegment,
    b: WorkingSegment,
    profile: TopologyProfile,
    ink_mask: np.ndarray | None,
) -> WorkingSegment | None:
    if not collinear_compatible(a, b, profile):
        return None
    pairs = (
        (a.end_x, a.end_y, b.start_x, b.start_y),
        (a.end_x, a.end_y, b.end_x, b.end_y),
        (a.start_x, a.start_y, b.start_x, b.start_y),
        (a.start_x, a.start_y, b.end_x, b.end_y),
    )
    best_gap = float("inf")
    best_orient: tuple[float, float, float, float] | None = None
    for ax, ay, bx, by in pairs:
        gap = point_distance(ax, ay, bx, by)
        if gap < best_gap:
            best_gap = gap
            best_orient = (ax, ay, bx, by)
    if best_orient is None or best_gap > profile.collinear_merge_max_gap_px:
        return None
    ax, ay, bx, by = best_orient
    coverage = _ink_bridge_coverage(ink_mask, ax, ay, bx, by, profile)
    if coverage < profile.min_ink_bridge_coverage:
        return None

    # Orient merged segment along the longer axis of the union of endpoints.
    pts = [
        (a.start_x, a.start_y),
        (a.end_x, a.end_y),
        (b.start_x, b.start_y),
        (b.end_x, b.end_y),
    ]
    max_dist = 0.0
    p0, p1 = pts[0], pts[1]
    for i, pi in enumerate(pts):
        for pj in pts[i + 1 :]:
            d = point_distance(pi[0], pi[1], pj[0], pj[1])
            if d >= max_dist:
                max_dist = d
                p0, p1 = pi, pj

    merged_ids = list(dict.fromkeys(a.merged_primitive_ids + b.merged_primitive_ids))
    merged_components = list(
        dict.fromkeys(a.merged_component_ids + b.merged_component_ids)
    )
    return WorkingSegment(
        segment_id=f"{a.segment_id}+{b.segment_id}",
        primitive_id=a.primitive_id,
        layer_id=a.layer_id,
        component_id=a.component_id,
        centerline_edge_id=a.centerline_edge_id,
        start_x=p0[0],
        start_y=p0[1],
        end_x=p1[0],
        end_y=p1[1],
        merged_primitive_ids=merged_ids,
        merged_component_ids=merged_components,
    )


def merge_collinear_segments(
    segments: list[WorkingSegment],
    profile: TopologyProfile,
    ink_mask: np.ndarray | None,
) -> list[WorkingSegment]:
    current = list(segments)
    if not current:
        return []
    while True:
        merged_any = False
        for i in range(len(current)):
            for j in range(i + 1, len(current)):
                candidate = _try_merge_pair(
                    current[i], current[j], profile, ink_mask
                )
                if candidate is None:
                    continue
                next_segments = [
                    current[k] for k in range(len(current)) if k not in (i, j)
                ]
                next_segments.append(candidate)
                current = next_segments
                merged_any = True
                break
            if merged_any:
                break
        if not merged_any:
            break
    return current
