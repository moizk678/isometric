"""Detect dimension lines, arrows, and callout leaders on markup ink."""

from __future__ import annotations

import math

import cv2
import numpy as np

from isometric_pipeline.associate_markup.artifact import (
    DimensionGeometryCandidate,
    LineSegment,
    PageBBox,
    PagePoint,
)
from isometric_pipeline.profiles.loader import AssociationsProfile
from isometric_pipeline.regions.artifact import RegionCandidate
from isometric_pipeline.topology.artifact import TopologyMetadata


def detect_markup_geometry(
    geometry_ink: np.ndarray,
    *,
    regions: list[RegionCandidate],
    topology: TopologyMetadata | None,
    profile: AssociationsProfile,
) -> list[DimensionGeometryCandidate]:
    height, width = geometry_ink.shape
    markup = _markup_mask(geometry_ink, regions, topology, profile, height, width)
    if not np.any(markup):
        return []

    lines = cv2.HoughLinesP(
        markup,
        rho=1,
        theta=np.pi / 180,
        threshold=max(8, profile.hough_threshold),
        minLineLength=int(profile.min_witness_length_px),
        maxLineGap=int(profile.witness_max_gap_px),
    )
    segments: list[tuple[PagePoint, PagePoint, float]] = []
    if lines is not None:
        for raw in lines:
            x1, y1, x2, y2 = raw[0]
            start = PagePoint(x=float(x1), y=float(y1))
            end = PagePoint(x=float(x2), y=float(y2))
            length = math.hypot(end.x - start.x, end.y - start.y)
            if length < profile.min_witness_length_px:
                continue
            angle = abs(
                math.degrees(math.atan2(end.y - start.y, end.x - start.x)) % 180.0
            )
            if (
                angle > profile.max_witness_angle_from_axis_deg
                and (180.0 - angle) > profile.max_witness_angle_from_axis_deg
            ):
                continue
            segments.append((start, end, length))

    dimension_regions = [r for r in regions if r.kind == "dimension"]
    arrow_regions = {r.id: r for r in regions if r.kind == "arrow"}
    candidates: list[DimensionGeometryCandidate] = []
    used: set[int] = set()

    for region in dimension_regions:
        cx = region.bbox.x + region.bbox.width / 2.0
        cy = region.bbox.y + region.bbox.height / 2.0
        center = PagePoint(x=cx, y=cy)
        best_i: int | None = None
        best_score = -1.0
        for i, (start, end, length) in enumerate(segments):
            if i in used:
                continue
            dist = _point_to_segment(center, start, end)
            if dist > profile.max_witness_text_distance_px:
                continue
            score = length / max(1.0, dist)
            if score > best_score:
                best_score = score
                best_i = i
        if best_i is None:
            continue
        used.add(best_i)
        start, end, _ = segments[best_i]
        witness = _orient_witness(start, end, center)
        arrows, arrow_ids = _arrowheads_near_witness(
            witness, arrow_regions, profile.arrow_alignment_tolerance_deg
        )
        geo_id = f"dim_geo_{region.id}"
        candidates.append(
            DimensionGeometryCandidate(
                id=geo_id,
                witness_line=witness,
                arrowhead_points=arrows,
                arrow_region_ids=arrow_ids,
                evidence=f"witness near dimension region {region.id}",
            )
        )

    return candidates


def trace_leader_polyline(
    text_bbox: PageBBox,
    geometry_ink: np.ndarray,
    *,
    topology: TopologyMetadata | None,
    regions: list[RegionCandidate],
    profile: AssociationsProfile,
) -> list[PagePoint]:
    start = PagePoint(
        x=text_bbox.x + text_bbox.width / 2.0,
        y=text_bbox.y + text_bbox.height,
    )
    height, width = geometry_ink.shape
    markup = _markup_mask(geometry_ink, regions, topology, profile, height, width)

    visited = np.zeros_like(markup, dtype=np.uint8)
    points: list[PagePoint] = [start]
    current = start
    if not _on_markup(current, markup):
        seed = _closest_markup_point(
            current, markup, radius=int(profile.leader_step_px * 6)
        )
        if seed is None:
            return []
        points = [start, seed]
        current = seed
        visited[int(seed.y), int(seed.x)] = 255
    for _ in range(int(profile.leader_max_steps)):
        step = _best_neighbor(current, markup, visited, profile.leader_step_px)
        if step is None:
            break
        nx, ny = step
        nxt = PagePoint(x=float(nx), y=float(ny))
        points.append(nxt)
        visited[ny, nx] = 255
        current = nxt
    return points if len(points) >= 2 else []


def point_distance(a: PagePoint, b: PagePoint) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _markup_mask(
    geometry_ink: np.ndarray,
    regions: list[RegionCandidate],
    topology: TopologyMetadata | None,
    profile: AssociationsProfile,
    height: int,
    width: int,
) -> np.ndarray:
    markup = (geometry_ink > 0).astype(np.uint8) * 255
    if topology:
        buffer_px = int(profile.pipe_exclusion_buffer_px)
        for edge in topology.edges:
            cv2.line(
                markup,
                (int(edge.start.x), int(edge.start.y)),
                (int(edge.end.x), int(edge.end.y)),
                0,
                thickness=buffer_px,
            )
    dimension_pad = int(profile.max_witness_text_distance_px)
    for region in regions:
        if region.kind == "dimension":
            x0 = max(0, int(region.bbox.x) - dimension_pad)
            y0 = max(0, int(region.bbox.y) - dimension_pad)
            x1 = min(width, int(region.bbox.x + region.bbox.width) + dimension_pad)
            y1 = min(height, int(region.bbox.y + region.bbox.height) + dimension_pad)
            markup[y0:y1, x0:x1] = (geometry_ink[y0:y1, x0:x1] > 0).astype(
                np.uint8
            ) * 255
    for region in regions:
        if region.kind in ("text", "dimension", "symbol"):
            x0 = max(0, int(region.bbox.x))
            y0 = max(0, int(region.bbox.y))
            x1 = min(width, int(region.bbox.x + region.bbox.width))
            y1 = min(height, int(region.bbox.y + region.bbox.height))
            markup[y0:y1, x0:x1] = 0
    return markup


def _point_to_segment(point: PagePoint, start: PagePoint, end: PagePoint) -> float:
    dx = end.x - start.x
    dy = end.y - start.y
    if dx == 0.0 and dy == 0.0:
        return point_distance(point, start)
    t = ((point.x - start.x) * dx + (point.y - start.y) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj = PagePoint(x=start.x + t * dx, y=start.y + t * dy)
    return point_distance(point, proj)


def _orient_witness(start: PagePoint, end: PagePoint, near: PagePoint) -> LineSegment:
    d_start = point_distance(near, start)
    d_end = point_distance(near, end)
    if d_start <= d_end:
        return LineSegment(start=start, end=end)
    return LineSegment(start=end, end=start)


def _arrowheads_near_witness(
    witness: LineSegment,
    arrow_regions: dict[str, RegionCandidate],
    tolerance_deg: float,
) -> tuple[list[PagePoint], list[str]]:
    points: list[PagePoint] = []
    ids: list[str] = []
    w_angle = math.degrees(
        math.atan2(
            witness.end.y - witness.start.y,
            witness.end.x - witness.start.x,
        )
    )
    for region_id, region in arrow_regions.items():
        cx = region.bbox.x + region.bbox.width / 2.0
        cy = region.bbox.y + region.bbox.height / 2.0
        center = PagePoint(x=cx, y=cy)
        for tip in (witness.start, witness.end):
            if (
                point_distance(center, tip)
                > max(region.bbox.width, region.bbox.height) + 8
            ):
                continue
            a_angle = math.degrees(math.atan2(tip.y - center.y, tip.x - center.x))
            delta = abs(a_angle - w_angle) % 360.0
            delta = min(delta, 360.0 - delta)
            if delta <= tolerance_deg or abs(delta - 180.0) <= tolerance_deg:
                points.append(tip)
                ids.append(region_id)
                break
    return points, ids


def _on_markup(point: PagePoint, markup: np.ndarray) -> bool:
    x = int(point.x)
    y = int(point.y)
    height, width = markup.shape
    if x < 0 or y < 0 or x >= width or y >= height:
        return False
    return bool(markup[y, x])


def _closest_markup_point(
    point: PagePoint, markup: np.ndarray, *, radius: int
) -> PagePoint | None:
    height, width = markup.shape
    cx = int(point.x)
    cy = int(point.y)
    best: PagePoint | None = None
    best_dist = float("inf")
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            nx, ny = cx + dx, cy + dy
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            if not markup[ny, nx]:
                continue
            dist = math.hypot(dx, dy)
            if dist < best_dist:
                best_dist = dist
                best = PagePoint(x=float(nx), y=float(ny))
    return best


def _best_neighbor(
    current: PagePoint,
    markup: np.ndarray,
    visited: np.ndarray,
    step_px: float,
) -> tuple[int, int] | None:
    height, width = markup.shape
    best: tuple[int, int] | None = None
    best_dist = float("inf")
    radius = int(max(2, step_px))
    cx = int(current.x)
    cy = int(current.y)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            nx, ny = cx + dx, cy + dy
            if nx < 0 or ny < 0 or nx >= width or ny >= height:
                continue
            if not markup[ny, nx] or visited[ny, nx]:
                continue
            dist = math.hypot(dx, dy)
            if dist < best_dist:
                best_dist = dist
                best = (nx, ny)
    return best
