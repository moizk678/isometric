"""Intersection hypothesis and review item generation."""

from __future__ import annotations

import math

import numpy as np

from isometric_pipeline.profiles.loader import TopologyProfile
from isometric_pipeline.topology.artifact import (
    HypothesisAlternative,
    IntersectionHypothesis,
    PageBBox,
    PagePoint,
    TopologyReviewItem,
)
from isometric_pipeline.topology.intersections import (
    SegmentIntersection,
    angle_between_segments_at_point,
)
from isometric_pipeline.topology.segments import WorkingSegment


def _disk_ink_coverage(
    mask: np.ndarray | None,
    x: float,
    y: float,
    radius: float,
) -> float:
    if mask is None:
        return 0.0
    h, w = mask.shape
    r = int(math.ceil(radius))
    ix = int(round(x))
    iy = int(round(y))
    hits = 0
    total = 0
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > radius * radius:
                continue
            px, py = ix + dx, iy + dy
            if 0 <= px < w and 0 <= py < h:
                total += 1
                if mask[py, px] > 0:
                    hits += 1
    return hits / total if total else 0.0


def build_intersection_hypothesis(
    hit: SegmentIntersection,
    seg_a: WorkingSegment,
    seg_b: WorkingSegment,
    profile: TopologyProfile,
    ink_mask: np.ndarray | None,
    hypothesis_index: int,
    crossing_node_ids: list[str],
) -> tuple[IntersectionHypothesis, TopologyReviewItem | None]:
    group_id = f"hyp_{hypothesis_index:04d}"
    angle = angle_between_segments_at_point(seg_a, seg_b, hit.x, hit.y)
    same_layer = seg_a.layer_id == seg_b.layer_id
    ink = _disk_ink_coverage(ink_mask, hit.x, hit.y, profile.intersection_proximity_px)
    tee_score = 0.0
    crossing_score = 0.2
    if same_layer:
        crossing_score += 0.25
        if ink >= profile.min_ink_bridge_coverage:
            tee_score += 0.55
        if angle >= profile.min_branch_angle_deg:
            tee_score += 0.2
    else:
        crossing_score += 0.55
        tee_score += 0.05

    crossing_alt = HypothesisAlternative(
        id=f"{group_id}_crossing",
        label="crossing",
        node_ids=crossing_node_ids,
        edge_ids=[],
        score=crossing_score,
    )
    tee_alt = HypothesisAlternative(
        id=f"{group_id}_tee",
        label="tee",
        node_ids=[],
        edge_ids=[],
        score=tee_score,
    )
    margin = abs(tee_score - crossing_score)
    recommended: str | None = None
    review: TopologyReviewItem | None = None
    if margin >= profile.min_hypothesis_margin:
        recommended = crossing_alt.id if crossing_score >= tee_score else tee_alt.id
    else:
        review = TopologyReviewItem(
            id=f"rev_{hypothesis_index:04d}",
            code="topology.crossing_unresolved",
            message="Ambiguous intersection; pixel overlap is insufficient for connectivity.",
            hypothesis_group_id=group_id,
            bbox=PageBBox(
                x=hit.x - 12,
                y=hit.y - 12,
                width=24,
                height=24,
            ),
            related_node_ids=crossing_node_ids,
        )

    hypothesis = IntersectionHypothesis(
        id=group_id,
        position=PagePoint(x=hit.x, y=hit.y),
        segment_ids=[seg_a.segment_id, seg_b.segment_id],
        alternatives=[crossing_alt, tee_alt],
        recommended_alternative_id=recommended,
    )
    return hypothesis, review
