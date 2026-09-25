"""Topology context for ranking OCR alternatives (not inventing text)."""

from __future__ import annotations

from isometric_pipeline.ocr.artifact import NearbyTopologyRef, PageBBox, TextAlternative
from isometric_pipeline.topology.artifact import TopologyMetadata


def nearby_topology(
    bbox: PageBBox,
    topology: TopologyMetadata | None,
    *,
    max_distance_px: float = 48.0,
) -> NearbyTopologyRef:
    if topology is None:
        return NearbyTopologyRef()
    cx = bbox.x + bbox.width / 2.0
    cy = bbox.y + bbox.height / 2.0
    node_ids: list[str] = []
    for node in topology.nodes:
        dx = node.position.x - cx
        dy = node.position.y - cy
        if (dx * dx + dy * dy) ** 0.5 <= max_distance_px:
            node_ids.append(node.id)
    edge_ids: list[str] = []
    for edge in topology.edges:
        mid_x = (edge.start.x + edge.end.x) / 2.0
        mid_y = (edge.start.y + edge.end.y) / 2.0
        dx = mid_x - cx
        dy = mid_y - cy
        if (dx * dx + dy * dy) ** 0.5 <= max_distance_px:
            edge_ids.append(edge.id)
    evidence = ""
    if node_ids or edge_ids:
        evidence = f"within {int(max_distance_px)}px of {len(node_ids)} nodes, {len(edge_ids)} edges"
    return NearbyTopologyRef(
        node_ids=node_ids[:8],
        edge_ids=edge_ids[:8],
        evidence=evidence,
    )


def rerank_alternatives(
    alternatives: list[TextAlternative],
    *,
    nearby_node_count: int,
) -> list[TextAlternative]:
    """Slight boost when graph context exists; never add new strings."""
    if nearby_node_count == 0:
        return sorted(alternatives, key=lambda a: a.score, reverse=True)
    boosted: list[TextAlternative] = []
    for alt in alternatives:
        bonus = 0.02 if alt.source == "vocabulary" else 0.0
        boosted.append(
            TextAlternative(
                text=alt.text,
                score=min(1.0, alt.score + bonus),
                source=alt.source,
            )
        )
    return sorted(boosted, key=lambda a: a.score, reverse=True)
