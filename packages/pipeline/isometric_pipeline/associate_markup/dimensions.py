"""Associate parsed dimension text with witness geometry and pipe targets."""

from __future__ import annotations

from isometric_pipeline.associate_markup.artifact import (
    AssociationReviewItem,
    DimensionCandidate,
    DimensionGeometryCandidate,
    PageBBox,
    TargetRef,
)
from isometric_pipeline.associate_markup.context import (
    bbox_center,
    edge_midpoint,
    point_to_segment_distance,
    score_distance,
)
from isometric_pipeline.associate_markup.review import review_item_id
from isometric_pipeline.ocr.artifact import TextCandidate
from isometric_pipeline.profiles.loader import AssociationsProfile
from isometric_pipeline.topology.artifact import TopologyMetadata


def build_dimension_candidates(
    text_candidates: list[TextCandidate],
    geometry: list[DimensionGeometryCandidate],
    topology: TopologyMetadata | None,
    profile: AssociationsProfile,
) -> tuple[list[DimensionCandidate], list[AssociationReviewItem]]:
    dimension_texts = [
        t
        for t in text_candidates
        if t.region_kind == "dimension"
        or (t.parsed_dimension is not None and t.parsed_dimension.status == "parsed")
    ]
    candidates: list[DimensionCandidate] = []
    reviews: list[AssociationReviewItem] = []
    geo_by_text = _geometry_by_text_proximity(dimension_texts, geometry, profile)

    for text in dimension_texts:
        dim_id = f"dim_{text.id}"
        bbox = PageBBox(
            x=text.bbox.x,
            y=text.bbox.y,
            width=text.bbox.width,
            height=text.bbox.height,
        )
        center = bbox_center(bbox)
        geo = geo_by_text.get(text.id)

        if geo is None:
            reviews.append(
                AssociationReviewItem(
                    id=review_item_id("dimension.no_witness_line", dim_id, text.id),
                    code="dimension.no_witness_line",
                    message="Dimension text has no supported witness line",
                    dimension_candidate_id=dim_id,
                    text_candidate_id=text.id,
                    bbox=bbox,
                )
            )
            display = (
                text.parsed_dimension.display_text
                if text.parsed_dimension
                else (text.normalized_text or text.raw_text or "")
            )
            candidates.append(
                DimensionCandidate(
                    id=dim_id,
                    text_candidate_id=text.id,
                    region_id=text.region_id,
                    display_text=display,
                    parsed_dimension=text.parsed_dimension,
                    witness_start=center,
                    witness_end=center,
                    status="unresolved",
                )
            )
            continue

        witness = geo.witness_line
        if not geo.arrowhead_points and not geo.arrow_region_ids:
            reviews.append(
                AssociationReviewItem(
                    id=review_item_id("dimension.missing_arrow", dim_id, text.id),
                    code="dimension.missing_arrow",
                    message="Witness line lacks arrow evidence",
                    dimension_candidate_id=dim_id,
                    text_candidate_id=text.id,
                    bbox=bbox,
                )
            )

        targets, target_reviews = _rank_edge_targets(
            witness, topology, profile, dimension_id=dim_id, text_bbox=bbox
        )
        reviews.extend(target_reviews)

        parsed = text.parsed_dimension
        display = (
            parsed.display_text
            if parsed
            else (text.normalized_text or text.raw_text or "")
        )
        status = "proposed" if targets else "unresolved"
        if not targets:
            reviews.append(
                AssociationReviewItem(
                    id=review_item_id("association.unresolved", dim_id, text.id),
                    code="association.unresolved",
                    message="No topology edge target for dimension",
                    dimension_candidate_id=dim_id,
                    text_candidate_id=text.id,
                    bbox=bbox,
                )
            )

        candidates.append(
            DimensionCandidate(
                id=dim_id,
                text_candidate_id=text.id,
                region_id=text.region_id,
                display_text=display,
                parsed_dimension=parsed,
                witness_start=witness.start,
                witness_end=witness.end,
                geometry_candidate_id=geo.id,
                target_refs=targets,
                status=status,
            )
        )

    reviews.extend(_unit_conflict_reviews(candidates))
    return candidates, reviews


def _geometry_by_text_proximity(
    texts: list[TextCandidate],
    geometry: list[DimensionGeometryCandidate],
    profile: AssociationsProfile,
) -> dict[str, DimensionGeometryCandidate]:
    mapping: dict[str, DimensionGeometryCandidate] = {}
    for text in texts:
        center = bbox_center(
            PageBBox(
                x=text.bbox.x,
                y=text.bbox.y,
                width=text.bbox.width,
                height=text.bbox.height,
            )
        )
        best: DimensionGeometryCandidate | None = None
        best_dist = float("inf")
        for geo in geometry:
            dist = point_to_segment_distance(
                center, geo.witness_line.start, geo.witness_line.end
            )
            if dist < best_dist and dist <= profile.max_witness_text_distance_px:
                best_dist = dist
                best = geo
        if best is not None:
            mapping[text.id] = best
    return mapping


def _rank_edge_targets(
    witness,
    topology: TopologyMetadata | None,
    profile: AssociationsProfile,
    *,
    dimension_id: str,
    text_bbox: PageBBox,
) -> tuple[list[TargetRef], list[AssociationReviewItem]]:
    if topology is None or not topology.edges:
        return [], []
    scored: list[TargetRef] = []
    for edge in topology.edges:
        em = edge_midpoint(edge)
        dist = point_to_segment_distance(em, witness.start, witness.end)
        if dist > profile.max_dimension_target_distance_px:
            continue
        score = score_distance(dist, profile.max_dimension_target_distance_px)
        scored.append(TargetRef(ref_kind="topology_edge", ref_id=edge.id, score=score))
    scored.sort(key=lambda r: r.score, reverse=True)
    if not scored:
        return [], []

    reviews: list[AssociationReviewItem] = []
    top = scored[0]
    if len(scored) > 1:
        margin = top.score - scored[1].score
        if margin < profile.target_ambiguity_margin:
            reviews.append(
                AssociationReviewItem(
                    id=review_item_id("dimension.multiple_targets", dimension_id),
                    message="Multiple topology edges equally plausible for dimension",
                    dimension_candidate_id=dimension_id,
                    bbox=text_bbox,
                )
            )
            return scored[:2], reviews
    return [top], reviews


def _unit_conflict_reviews(
    candidates: list[DimensionCandidate],
) -> list[AssociationReviewItem]:
    reviews: list[AssociationReviewItem] = []
    by_region: dict[str, list[DimensionCandidate]] = {}
    for dim in candidates:
        by_region.setdefault(dim.region_id, []).append(dim)
    for region_id, group in by_region.items():
        unit_set = {
            d.parsed_dimension.unit
            for d in group
            if d.parsed_dimension and d.parsed_dimension.unit
        }
        if len(unit_set) > 1:
            for dim in group:
                reviews.append(
                    AssociationReviewItem(
                        id=review_item_id("dimension.unit_conflict", dim.id, region_id),
                        message=f"Conflicting units near region {region_id}",
                        dimension_candidate_id=dim.id,
                        text_candidate_id=dim.text_candidate_id,
                    )
                )
    return reviews
