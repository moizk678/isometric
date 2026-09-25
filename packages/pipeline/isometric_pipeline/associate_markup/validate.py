"""Validate association candidate artifacts."""

from __future__ import annotations

from isometric_pipeline.associate_markup.artifact import (
    AssociationCandidatesMetadata,
    TargetRefKind,
)


def validate_association_candidates(
    metadata: AssociationCandidatesMetadata,
    *,
    text_candidate_ids: set[str],
    region_ids: set[str],
    topology_edge_ids: set[str],
    topology_node_ids: set[str],
    symbol_candidate_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    dim_ids = {c.id for c in metadata.dimension_candidates}
    ann_ids = {c.id for c in metadata.annotation_targets}
    geo_ids = {g.id for g in metadata.dimension_geometry}

    for geo in metadata.dimension_geometry:
        if not geo.evidence:
            errors.append(f"dimension geometry {geo.id} missing evidence")

    for dim in metadata.dimension_candidates:
        if dim.text_candidate_id not in text_candidate_ids:
            errors.append(f"unknown text candidate {dim.text_candidate_id} on {dim.id}")
        if dim.region_id not in region_ids:
            errors.append(f"unknown region {dim.region_id} on {dim.id}")
        if dim.geometry_candidate_id and dim.geometry_candidate_id not in geo_ids:
            errors.append(
                f"unknown geometry candidate {dim.geometry_candidate_id} on {dim.id}"
            )
        if dim.status == "proposed" and not dim.target_refs:
            errors.append(f"proposed dimension {dim.id} has no target refs")
        for ref in dim.target_refs:
            errors.extend(
                _validate_target_ref(
                    ref.ref_kind,
                    ref.ref_id,
                    topology_edge_ids,
                    topology_node_ids,
                    symbol_candidate_ids,
                    context=dim.id,
                )
            )

    for ann in metadata.annotation_targets:
        if ann.text_candidate_id not in text_candidate_ids:
            errors.append(f"unknown text candidate {ann.text_candidate_id} on {ann.id}")
        if ann.status == "proposed" and not ann.alternatives:
            errors.append(f"proposed annotation {ann.id} has no alternatives")
        for alt in ann.alternatives:
            errors.extend(
                _validate_target_ref(
                    alt.ref_kind,
                    alt.ref_id,
                    topology_edge_ids,
                    topology_node_ids,
                    symbol_candidate_ids,
                    context=ann.id,
                )
            )

    for rel in metadata.relationships:
        if rel.type == "measures":
            if rel.to_ref_kind != "topology_edge":
                errors.append(
                    f"relationship {rel.id} measures must target a topology edge"
                )
        if rel.type == "measures" and rel.from_candidate_id not in dim_ids:
            errors.append(
                f"relationship {rel.id} measures from unknown dimension "
                f"{rel.from_candidate_id}"
            )
        if rel.type in ("annotates", "callout_targets"):
            if rel.from_candidate_id not in ann_ids:
                errors.append(
                    f"relationship {rel.id} {rel.type} from unknown annotation "
                    f"{rel.from_candidate_id}"
                )
        errors.extend(
            _validate_target_ref(
                rel.to_ref_kind,
                rel.to_ref_id,
                topology_edge_ids,
                topology_node_ids,
                symbol_candidate_ids,
                context=rel.id,
            )
        )
        if rel.interpretation == "proposed" and not rel.evidence:
            errors.append(f"relationship {rel.id} missing evidence")

    for item in metadata.review_items:
        if item.dimension_candidate_id and item.dimension_candidate_id not in dim_ids:
            errors.append(
                f"review item references missing dimension {item.dimension_candidate_id}"
            )
        if item.annotation_candidate_id and item.annotation_candidate_id not in ann_ids:
            errors.append(
                f"review item references missing annotation {item.annotation_candidate_id}"
            )
        if item.text_candidate_id and item.text_candidate_id not in text_candidate_ids:
            errors.append(
                f"review item references missing text {item.text_candidate_id}"
            )

    return errors


def _validate_target_ref(
    kind: TargetRefKind,
    ref_id: str,
    edge_ids: set[str],
    node_ids: set[str],
    symbol_ids: set[str],
    *,
    context: str,
) -> list[str]:
    if kind == "topology_edge" and ref_id not in edge_ids:
        return [f"{context}: unknown topology edge {ref_id}"]
    if kind == "topology_node" and ref_id not in node_ids:
        return [f"{context}: unknown topology node {ref_id}"]
    if kind == "symbol_candidate" and ref_id not in symbol_ids:
        return [f"{context}: unknown symbol candidate {ref_id}"]
    return []
