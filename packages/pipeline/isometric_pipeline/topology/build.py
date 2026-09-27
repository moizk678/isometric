"""Assemble topology node/edge candidates from segments."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from isometric_pipeline.profiles.loader import TopologyProfile
from isometric_pipeline.regions.artifact import RegionCandidate
from isometric_pipeline.topology.artifact import (
    EdgeCandidate,
    EvidenceScores,
    NodeCandidate,
    NodeKind,
    PagePoint,
    TopologyReviewItem,
)
from isometric_pipeline.topology.endpoints import (
    cluster_endpoints,
    segment_endpoint_angle_at_node,
)
from isometric_pipeline.topology.hypotheses import build_intersection_hypothesis
from isometric_pipeline.topology.intersections import find_interior_intersections
from isometric_pipeline.topology.merge import merge_collinear_segments
from isometric_pipeline.topology.segments import WorkingSegment, point_distance


@dataclass
class BuiltTopology:
    segments: list[WorkingSegment]
    nodes: list[NodeCandidate]
    edges: list[EdgeCandidate]
    hypotheses: list
    review_items: list[TopologyReviewItem]
    endpoint_cluster_to_node: dict[int, str]
    segment_endpoint_nodes: dict[tuple[str, int], str]


def _in_symbol_region(
    x: float,
    y: float,
    regions: list[RegionCandidate],
    buffer_px: float,
) -> bool:
    for region in regions:
        if region.kind != "symbol":
            continue
        bx = region.bbox.x - buffer_px
        by = region.bbox.y - buffer_px
        bw = region.bbox.width + 2 * buffer_px
        bh = region.bbox.height + 2 * buffer_px
        if bx <= x <= bx + bw and by <= y <= by + bh:
            return True
    return False


def _segment_for_edge(
    edge: EdgeCandidate,
    segments_by_id: dict[str, WorkingSegment],
) -> WorkingSegment | None:
    seg_key = edge.id.removeprefix("edge_")
    seg = segments_by_id.get(seg_key)
    if seg is not None:
        return seg
    prim_set = set(edge.source_primitive_ids)
    for candidate in segments_by_id.values():
        if prim_set & set(candidate.merged_primitive_ids):
            return candidate
    return None


def _classify_node_kind(
    incident_edges: list[EdgeCandidate],
    segments_by_id: dict[str, WorkingSegment],
    node_x: float,
    node_y: float,
    profile: TopologyProfile,
) -> NodeKind:
    if len(incident_edges) <= 1:
        return "endpoint"
    if len(incident_edges) >= 3:
        return "tee"
    if len(incident_edges) == 2:
        angles: list[float] = []
        for edge in incident_edges:
            seg = _segment_for_edge(edge, segments_by_id)
            if seg is None:
                continue
            angles.append(segment_endpoint_angle_at_node(seg, node_x, node_y))
        if len(angles) >= 2:
            delta = abs(angles[0] - angles[1]) % 180.0
            delta = min(delta, 180.0 - delta)
            if profile.elbow_angle_min_deg <= delta <= profile.elbow_angle_max_deg:
                return "elbow"
        return "unknown"
    return "unknown"


def build_topology(
    segments: list[WorkingSegment],
    profile: TopologyProfile,
    ink_mask: np.ndarray | None,
    regions: list[RegionCandidate],
) -> BuiltTopology:
    merged = merge_collinear_segments(segments, profile, ink_mask)
    clusters = cluster_endpoints(merged, profile)
    segments_by_id = {seg.segment_id: seg for seg in merged}

    nodes: list[NodeCandidate] = []
    cluster_to_node: dict[int, str] = {}
    for cluster in clusters:
        cx, cy = cluster.centroid()
        node_id = f"node_{cluster.cluster_id:04d}"
        cluster_to_node[cluster.cluster_id] = node_id
        nodes.append(
            NodeCandidate(
                id=node_id,
                position=PagePoint(x=cx, y=cy),
                kind="endpoint",
                status="proposed",
                layer_ids=cluster.layer_ids(),
                source_evidence="endpoint_cluster",
            )
        )

    seg_endpoint_node: dict[tuple[str, int], str] = {}
    for cluster in clusters:
        node_id = cluster_to_node[cluster.cluster_id]
        for member in cluster.members:
            seg_endpoint_node[(member.segment_id, member.end_index)] = node_id

    node_by_id = {node.id: node for node in nodes}
    edges: list[EdgeCandidate] = []
    for seg in merged:
        start_node = seg_endpoint_node.get((seg.segment_id, 0))
        end_node = seg_endpoint_node.get((seg.segment_id, 1))
        if start_node is None or end_node is None:
            continue
        start_node_obj = node_by_id[start_node]
        end_node_obj = node_by_id[end_node]
        continuity = 1.0
        if _in_symbol_region(
            (seg.start_x + seg.end_x) / 2,
            (seg.start_y + seg.end_y) / 2,
            regions,
            profile.symbol_region_buffer_px,
        ):
            continuity = 0.2
        edges.append(
            EdgeCandidate(
                id=f"edge_{seg.segment_id}",
                start_node_id=start_node,
                end_node_id=end_node,
                layer_id=seg.layer_id,
                start=PagePoint(
                    x=start_node_obj.position.x,
                    y=start_node_obj.position.y,
                ),
                end=PagePoint(
                    x=end_node_obj.position.x,
                    y=end_node_obj.position.y,
                ),
                source_primitive_ids=seg.merged_primitive_ids,
                component_ids=seg.merged_component_ids,
                scores=EvidenceScores(
                    distance=1.0,
                    angle=1.0,
                    color=1.0 if seg.layer_id else 0.5,
                    continuity=continuity,
                ),
            )
        )

    # Reclassify node kinds from incident edges.
    incident: dict[str, list[EdgeCandidate]] = {n.id: [] for n in nodes}
    for edge in edges:
        incident[edge.start_node_id].append(edge)
        incident[edge.end_node_id].append(edge)
    for node in nodes:
        node.kind = _classify_node_kind(
            incident[node.id],
            segments_by_id,
            node.position.x,
            node.position.y,
            profile,
        )
        if node.kind in ("tee", "elbow"):
            node.status = "confirmed_structure"

    hypotheses: list = []
    review_items: list[TopologyReviewItem] = []
    interior = find_interior_intersections(merged, profile.intersection_proximity_px)
    hyp_index = 0
    for hit in interior:
        seg_a = segments_by_id.get(hit.segment_a_id)
        seg_b = segments_by_id.get(hit.segment_b_id)
        if seg_a is None or seg_b is None:
            continue
        crossing_nodes: list[str] = []
        for seg in (seg_a, seg_b):
            for end_idx in (0, 1):
                nid = seg_endpoint_node.get((seg.segment_id, end_idx))
                if nid and nid not in crossing_nodes:
                    crossing_nodes.append(nid)
        hypothesis, review = build_intersection_hypothesis(
            hit,
            seg_a,
            seg_b,
            profile,
            ink_mask,
            hyp_index,
            crossing_nodes,
        )
        hypotheses.append(hypothesis)
        if review is not None:
            review_items.append(review)
        hyp_index += 1

    # Near-miss endpoint pairs.
    rev_near = 0
    refs: list[tuple[str, int, float, float]] = []
    for seg in merged:
        refs.append((seg.segment_id, 0, seg.start_x, seg.start_y))
        refs.append((seg.segment_id, 1, seg.end_x, seg.end_y))
    for i, ref_a in enumerate(refs):
        for ref_b in refs[i + 1 :]:
            if ref_a[0] == ref_b[0]:
                continue
            dist = point_distance(ref_a[2], ref_a[3], ref_b[2], ref_b[3])
            tol = profile.endpoint_cluster_tolerance_px
            if tol < dist <= tol * 2.0:
                review_items.append(
                    TopologyReviewItem(
                        id=f"rev_near_{rev_near:04d}",
                        code="topology.near_miss_endpoints",
                        message="Endpoints are close but were not merged.",
                        bbox=None,
                        related_node_ids=[
                            nid
                            for nid in (
                                seg_endpoint_node.get((ref_a[0], ref_a[1])),
                                seg_endpoint_node.get((ref_b[0], ref_b[1])),
                            )
                            if nid
                        ],
                    )
                )
                rev_near += 1

    return BuiltTopology(
        segments=merged,
        nodes=nodes,
        edges=edges,
        hypotheses=hypotheses,
        review_items=review_items,
        endpoint_cluster_to_node=cluster_to_node,
        segment_endpoint_nodes=seg_endpoint_node,
    )
