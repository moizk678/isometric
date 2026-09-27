"""Merge stage review artifacts into revision review rows."""

from __future__ import annotations

from dataclasses import dataclass

from isometric_pipeline.topology.artifact import TopologyReviewItem

from .context import AssemblyContext
from .id_map import AssemblyIdMap


@dataclass(frozen=True)
class PlannedReviewItem:
    issue_key: str
    issue_type: str
    severity: str
    object_id: str | None
    state: str = "open"


def _severity_for_code(code: str) -> str:
    if code.startswith("dimension.") and "conflict" in code:
        return "critical"
    if code.startswith("topology.") and "crossing" in code:
        return "high"
    if "unresolved" in code or "ambiguous" in code:
        return "high"
    return "medium"


def _object_for_topology(item: TopologyReviewItem, id_map: AssemblyIdMap) -> str | None:
    if item.related_node_ids:
        mapped = id_map.node_to_scene.get(item.related_node_ids[0])
        if mapped:
            return mapped
    if item.related_edge_ids:
        mapped = id_map.edge_to_scene.get(item.related_edge_ids[0])
        if mapped:
            return mapped
    return None


def plan_review_items(
    ctx: AssemblyContext, id_map: AssemblyIdMap
) -> list[PlannedReviewItem]:
    planned: list[PlannedReviewItem] = []

    if ctx.topology is not None:
        for item in ctx.topology.review_items:
            planned.append(
                PlannedReviewItem(
                    issue_key=item.id,
                    issue_type=item.code,
                    severity=_severity_for_code(item.code),
                    object_id=_object_for_topology(item, id_map),
                )
            )

    if ctx.text is not None:
        for item in ctx.text.review_items:
            object_id = None
            if item.text_candidate_id:
                object_id = id_map.text_to_scene.get(item.text_candidate_id)
            planned.append(
                PlannedReviewItem(
                    issue_key=item.id,
                    issue_type=item.code,
                    severity=_severity_for_code(item.code),
                    object_id=object_id,
                )
            )

    if ctx.symbols is not None:
        for item in ctx.symbols.review_items:
            object_id = None
            if item.symbol_candidate_id:
                object_id = id_map.symbol_to_scene.get(item.symbol_candidate_id)
            planned.append(
                PlannedReviewItem(
                    issue_key=item.id,
                    issue_type=item.code,
                    severity=_severity_for_code(item.code),
                    object_id=object_id,
                )
            )

    if ctx.associations is not None:
        for item in ctx.associations.review_items:
            object_id = None
            if item.dimension_candidate_id:
                object_id = id_map.dimension_to_scene.get(item.dimension_candidate_id)
            elif item.annotation_candidate_id:
                object_id = id_map.annotation_to_scene.get(item.annotation_candidate_id)
            elif item.text_candidate_id:
                object_id = id_map.text_to_scene.get(item.text_candidate_id)
            planned.append(
                PlannedReviewItem(
                    issue_key=item.id,
                    issue_type=item.code,
                    severity=_severity_for_code(item.code),
                    object_id=object_id,
                )
            )

    return planned
