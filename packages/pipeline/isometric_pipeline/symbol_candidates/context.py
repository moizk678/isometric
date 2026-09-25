"""Nearby OCR and topology context for symbol classification."""

from __future__ import annotations

import math

from isometric_pipeline.ocr.artifact import (
    PageBBox,
    TextCandidate,
    TextCandidatesMetadata,
)
from isometric_pipeline.symbol_candidates.artifact import NearbyTopologyRef, PagePoint
from isometric_pipeline.topology.artifact import TopologyMetadata


def region_center(bbox: PageBBox) -> tuple[float, float]:
    return (bbox.x + bbox.width / 2.0, bbox.y + bbox.height / 2.0)


def nearby_text_candidates(
    bbox: PageBBox,
    text: TextCandidatesMetadata | None,
    *,
    radius_px: float,
) -> list[TextCandidate]:
    if text is None:
        return []
    cx, cy = region_center(bbox)
    out: list[TextCandidate] = []
    for candidate in text.candidates:
        tx = candidate.bbox.x + candidate.bbox.width / 2.0
        ty = candidate.bbox.y + candidate.bbox.height / 2.0
        if math.hypot(tx - cx, ty - cy) <= radius_px:
            out.append(candidate)
    return out


def nearby_topology(
    bbox: PageBBox,
    topology: TopologyMetadata | None,
    *,
    radius_px: float,
) -> NearbyTopologyRef:
    if topology is None:
        return NearbyTopologyRef()
    cx, cy = region_center(bbox)
    node_ids: list[str] = []
    edge_ids: list[str] = []
    for node in topology.nodes:
        if math.hypot(node.position.x - cx, node.position.y - cy) <= radius_px:
            node_ids.append(node.id)
    for edge in topology.edges:
        mid_x = (edge.start.x + edge.end.x) / 2.0
        mid_y = (edge.start.y + edge.end.y) / 2.0
        if math.hypot(mid_x - cx, mid_y - cy) <= radius_px:
            edge_ids.append(edge.id)
    return NearbyTopologyRef(
        node_ids=node_ids,
        edge_ids=edge_ids,
        evidence="radius",
    )


def incident_edge_count(node_id: str, topology: TopologyMetadata) -> int:
    count = 0
    for edge in topology.edges:
        if edge.start_node_id == node_id or edge.end_node_id == node_id:
            count += 1
    return count


def dominant_edge_rotation(
    node_id: str,
    topology: TopologyMetadata,
) -> float:
    angles: list[float] = []
    for edge in topology.edges:
        if edge.start_node_id == node_id:
            dx = edge.end.x - edge.start.x
            dy = edge.end.y - edge.start.y
        elif edge.end_node_id == node_id:
            dx = edge.start.x - edge.end.x
            dy = edge.start.y - edge.end.y
        else:
            continue
        if dx == 0 and dy == 0:
            continue
        angles.append(math.degrees(math.atan2(dy, dx)))
    if not angles:
        return 0.0
    return angles[0]


def structural_junction_only(
    bbox: PageBBox,
    topology: TopologyMetadata | None,
    *,
    tolerance_px: float,
) -> tuple[bool, str | None]:
    if topology is None:
        return False, None
    cx, cy = region_center(bbox)
    for node in topology.nodes:
        if node.kind not in ("tee", "elbow"):
            continue
        if node.status != "confirmed_structure":
            continue
        if math.hypot(node.position.x - cx, node.position.y - cy) <= tolerance_px:
            return True, node.id
    return False, None


def anchor_point(bbox: PageBBox) -> PagePoint:
    cx, cy = region_center(bbox)
    return PagePoint(x=cx, y=cy)
