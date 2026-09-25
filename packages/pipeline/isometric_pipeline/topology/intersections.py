"""Segment intersection utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass

from isometric_pipeline.topology.segments import WorkingSegment, point_distance


@dataclass(frozen=True)
class SegmentIntersection:
    segment_a_id: str
    segment_b_id: str
    x: float
    y: float
    param_a: float
    param_b: float


def _segment_intersection(
    seg_a: WorkingSegment,
    seg_b: WorkingSegment,
    endpoint_tol: float,
) -> SegmentIntersection | None:
    x1, y1 = seg_a.start_x, seg_a.start_y
    x2, y2 = seg_a.end_x, seg_a.end_y
    x3, y3 = seg_b.start_x, seg_b.start_y
    x4, y4 = seg_b.end_x, seg_b.end_y
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    px = (
        (x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)
    ) / denom
    py = (
        (x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)
    ) / denom

    def _param(x0: float, y0: float, x1p: float, y1p: float, x: float, y: float) -> float:
        dx, dy = x1p - x0, y1p - y0
        length_sq = dx * dx + dy * dy
        if length_sq < 1e-9:
            return 0.0
        return ((x - x0) * dx + (y - y0) * dy) / length_sq

    ta = _param(x1, y1, x2, y2, px, py)
    tb = _param(x3, y3, x4, y4, px, py)
    if ta < -0.02 or ta > 1.02 or tb < -0.02 or tb > 1.02:
        return None

    def _near_endpoint(seg: WorkingSegment, x: float, y: float) -> bool:
        return (
            point_distance(x, y, seg.start_x, seg.start_y) <= endpoint_tol
            or point_distance(x, y, seg.end_x, seg.end_y) <= endpoint_tol
        )

    if _near_endpoint(seg_a, px, py) and _near_endpoint(seg_b, px, py):
        return None
    if _near_endpoint(seg_a, px, py) or _near_endpoint(seg_b, px, py):
        return None

    return SegmentIntersection(
        segment_a_id=seg_a.segment_id,
        segment_b_id=seg_b.segment_id,
        x=px,
        y=py,
        param_a=ta,
        param_b=tb,
    )


def find_interior_intersections(
    segments: list[WorkingSegment],
    proximity_px: float,
) -> list[SegmentIntersection]:
    found: list[SegmentIntersection] = []
    for i, seg_a in enumerate(segments):
        for seg_b in segments[i + 1 :]:
            hit = _segment_intersection(seg_a, seg_b, proximity_px)
            if hit is not None:
                found.append(hit)
    return found


def angle_between_segments_at_point(
    seg_a: WorkingSegment,
    seg_b: WorkingSegment,
    x: float,
    y: float,
) -> float:
    def _dir_from_point(seg: WorkingSegment) -> tuple[float, float]:
        d_start = point_distance(x, y, seg.start_x, seg.start_y)
        d_end = point_distance(x, y, seg.end_x, seg.end_y)
        if d_start <= d_end:
            return (seg.end_x - seg.start_x, seg.end_y - seg.start_y)
        return (seg.start_x - seg.end_x, seg.start_y - seg.end_y)

    ax, ay = _dir_from_point(seg_a)
    bx, by = _dir_from_point(seg_b)
    la = math.hypot(ax, ay)
    lb = math.hypot(bx, by)
    if la < 1e-6 or lb < 1e-6:
        return 0.0
    dot = (ax * bx + ay * by) / (la * lb)
    dot = max(-1.0, min(1.0, dot))
    return math.degrees(math.acos(dot))
