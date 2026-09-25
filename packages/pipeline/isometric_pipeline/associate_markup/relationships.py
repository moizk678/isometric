"""Emit relationship candidates from dimension and annotation links."""

from __future__ import annotations

from isometric_pipeline.associate_markup.artifact import (
    AnnotationTargetCandidate,
    DimensionCandidate,
    RelationshipCandidate,
)
from isometric_pipeline.associate_markup.rel_ids import relationship_id
from isometric_pipeline.profiles.loader import AssociationsProfile


def build_relationships(
    dimensions: list[DimensionCandidate],
    annotations: list[AnnotationTargetCandidate],
    profile: AssociationsProfile,
) -> list[RelationshipCandidate]:
    relationships: list[RelationshipCandidate] = []

    for dim in dimensions:
        if dim.status != "proposed" or not dim.target_refs:
            continue
        primary = dim.target_refs[0]
        state = "proposed" if len(dim.target_refs) == 1 else "unresolved"
        relationships.append(
            RelationshipCandidate(
                id=relationship_id(
                    "measures", dim.id, primary.ref_kind, primary.ref_id
                ),
                type="measures",
                from_candidate_id=dim.id,
                to_ref_kind=primary.ref_kind,
                to_ref_id=primary.ref_id,
                interpretation=state,
                evidence=(
                    f"dimension {dim.id} witness to {primary.ref_kind} {primary.ref_id}"
                ),
            )
        )

    for ann in annotations:
        if not ann.alternatives:
            continue
        primary = ann.alternatives[0]
        rel_type = "callout_targets" if ann.leader_polyline else "annotates"
        state = "proposed" if ann.status == "proposed" else "unresolved"
        if len(ann.alternatives) > 1:
            margin = ann.alternatives[0].score - ann.alternatives[1].score
            if margin < profile.target_ambiguity_margin:
                state = "unresolved"
        relationships.append(
            RelationshipCandidate(
                id=relationship_id(rel_type, ann.id, primary.ref_kind, primary.ref_id),
                type=rel_type,
                from_candidate_id=ann.id,
                to_ref_kind=primary.ref_kind,
                to_ref_id=primary.ref_id,
                interpretation=state,
                evidence=primary.evidence or f"annotation {ann.id} target ranking",
            )
        )

    return relationships
