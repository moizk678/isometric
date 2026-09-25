"""Associate note text with symbol, pipe, and junction targets."""

from __future__ import annotations

import numpy as np

from isometric_pipeline.associate_markup.artifact import (
    AnnotationAlternative,
    AnnotationTargetCandidate,
    AssociationReviewItem,
    PageBBox,
    PagePoint,
)
from isometric_pipeline.associate_markup.context import (
    bbox_center,
    edge_midpoint,
    point_distance,
    score_distance,
    topo_point,
)
from isometric_pipeline.associate_markup.geometry import trace_leader_polyline
from isometric_pipeline.associate_markup.review import review_item_id
from isometric_pipeline.ocr.artifact import TextCandidate
from isometric_pipeline.profiles.loader import AssociationsProfile
from isometric_pipeline.regions.artifact import RegionCandidate
from isometric_pipeline.symbol_candidates.artifact import SymbolCandidate
from isometric_pipeline.topology.artifact import TopologyMetadata


def build_annotation_targets(
    text_candidates: list[TextCandidate],
    regions: list[RegionCandidate],
    symbol_candidates: list[SymbolCandidate],
    topology: TopologyMetadata | None,
    geometry_ink: np.ndarray | None,
    profile: AssociationsProfile,
) -> tuple[list[AnnotationTargetCandidate], list[AssociationReviewItem]]:
    note_texts = [
        t
        for t in text_candidates
        if t.region_kind == "text"
        and (t.parsed_dimension is None or t.parsed_dimension.status != "parsed")
    ]
    candidates: list[AnnotationTargetCandidate] = []
    reviews: list[AssociationReviewItem] = []

    for text in note_texts:
        ann_id = f"ann_{text.id}"
        bbox = PageBBox(
            x=text.bbox.x,
            y=text.bbox.y,
            width=text.bbox.width,
            height=text.bbox.height,
        )
        center = bbox_center(bbox)
        leader: list[PagePoint] = []
        arrow_region_id: str | None = None
        if geometry_ink is not None:
            leader = trace_leader_polyline(
                bbox,
                geometry_ink,
                topology=topology,
                regions=regions,
                profile=profile,
            )
        if len(leader) < 2:
            reviews.append(
                AssociationReviewItem(
                    id=review_item_id("annotation.no_leader", ann_id, text.id),
                    code="annotation.no_leader",
                    message="Note lacks a traced callout leader",
                    annotation_candidate_id=ann_id,
                    text_candidate_id=text.id,
                    bbox=bbox,
                )
            )

        leader_tip = leader[-1] if leader else center
        alts = _rank_targets(
            leader_tip,
            symbol_candidates,
            topology,
            profile,
            leader_present=len(leader) >= 2,
        )
        status = "proposed" if alts else "unresolved"
        if not alts:
            reviews.append(
                AssociationReviewItem(
                    id=review_item_id("association.unresolved", ann_id, text.id),
                    code="association.unresolved",
                    message="No annotation target found",
                    annotation_candidate_id=ann_id,
                    text_candidate_id=text.id,
                    bbox=bbox,
                )
            )
        elif len(alts) > 1:
            margin = alts[0].score - alts[1].score
            if margin < profile.target_ambiguity_margin:
                status = "unresolved"
                reviews.append(
                    AssociationReviewItem(
                        id=review_item_id(
                            "annotation.ambiguous_target", ann_id, text.id
                        ),
                        code="annotation.ambiguous_target",
                        message="Multiple annotation targets within ranking margin",
                        annotation_candidate_id=ann_id,
                        text_candidate_id=text.id,
                        bbox=bbox,
                    )
                )

        for region in regions:
            if region.kind != "arrow":
                continue
            rc = bbox_center(
                PageBBox(
                    x=region.bbox.x,
                    y=region.bbox.y,
                    width=region.bbox.width,
                    height=region.bbox.height,
                )
            )
            if point_distance(rc, leader_tip) <= 12.0:
                arrow_region_id = region.id
                break

        candidates.append(
            AnnotationTargetCandidate(
                id=ann_id,
                text_candidate_id=text.id,
                region_id=text.region_id,
                leader_polyline=leader,
                arrow_region_id=arrow_region_id,
                alternatives=alts,
                status=status,
            )
        )

    return candidates, reviews


def _rank_targets(
    tip: PagePoint,
    symbols: list[SymbolCandidate],
    topology: TopologyMetadata | None,
    profile: AssociationsProfile,
    *,
    leader_present: bool,
) -> list[AnnotationAlternative]:
    alts: list[AnnotationAlternative] = []
    leader_bonus = 0.15 if leader_present else 0.0

    for sym in symbols:
        dist = point_distance(tip, PagePoint(x=sym.anchor.x, y=sym.anchor.y))
        if dist > profile.max_annotation_target_distance_px:
            continue
        score = (
            score_distance(dist, profile.max_annotation_target_distance_px)
            + leader_bonus
        )
        alts.append(
            AnnotationAlternative(
                ref_kind="symbol_candidate",
                ref_id=sym.id,
                score=min(1.0, score),
                evidence=f"distance to symbol anchor {dist:.1f}px",
            )
        )

    if topology:
        for edge in topology.edges:
            em = edge_midpoint(edge)
            dist = point_distance(tip, em)
            if dist > profile.max_annotation_target_distance_px:
                continue
            score = score_distance(dist, profile.max_annotation_target_distance_px)
            if leader_present:
                score += leader_bonus
            alts.append(
                AnnotationAlternative(
                    ref_kind="topology_edge",
                    ref_id=edge.id,
                    score=min(1.0, score),
                    evidence=f"distance to edge midpoint {dist:.1f}px",
                )
            )
        for node in topology.nodes:
            np_pt = topo_point(node.position)
            dist = point_distance(tip, np_pt)
            if dist > profile.max_annotation_target_distance_px:
                continue
            score = score_distance(dist, profile.max_annotation_target_distance_px)
            alts.append(
                AnnotationAlternative(
                    ref_kind="topology_node",
                    ref_id=node.id,
                    score=min(1.0, score),
                    evidence=f"distance to node {dist:.1f}px",
                )
            )

    alts.sort(key=lambda a: a.score, reverse=True)
    return alts[:3]
