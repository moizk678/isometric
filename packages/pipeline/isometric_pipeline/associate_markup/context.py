"""Shared spatial scoring for markup association."""

from __future__ import annotations

import math

from isometric_pipeline.associate_markup.artifact import PageBBox, PagePoint
from isometric_pipeline.topology.artifact import EdgeCandidate
from isometric_pipeline.topology.artifact import PagePoint as TopoPoint


def bbox_center(bbox: PageBBox) -> PagePoint:
    return PagePoint(
        x=bbox.x + bbox.width / 2.0,
        y=bbox.y + bbox.height / 2.0,
    )


def point_distance(a: PagePoint, b: PagePoint) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def point_to_segment_distance(
    point: PagePoint, start: PagePoint, end: PagePoint
) -> float:
    dx = end.x - start.x
    dy = end.y - start.y
    if dx == 0.0 and dy == 0.0:
        return point_distance(point, start)
    t = ((point.x - start.x) * dx + (point.y - start.y) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj = PagePoint(x=start.x + t * dx, y=start.y + t * dy)
    return point_distance(point, proj)


def edge_midpoint(edge: EdgeCandidate) -> PagePoint:
    return PagePoint(
        x=(edge.start.x + edge.end.x) / 2.0,
        y=(edge.start.y + edge.end.y) / 2.0,
    )


def segment_angle_deg(start: PagePoint, end: PagePoint) -> float:
    return math.degrees(math.atan2(end.y - start.y, end.x - start.x))


def angle_delta_deg(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def score_distance(distance: float, max_distance: float) -> float:
    if max_distance <= 0:
        return 0.0
    return max(0.0, 1.0 - distance / max_distance)


def topo_point(p: TopoPoint) -> PagePoint:
    return PagePoint(x=p.x, y=p.y)
