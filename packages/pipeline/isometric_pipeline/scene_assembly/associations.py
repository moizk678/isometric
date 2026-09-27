"""Association artifacts to dimensions and relationships."""

from __future__ import annotations

from isometric_pipeline.scene.models import (
    Dimension,
    DrawingObject,
    Interpretation,
    PagePoint,
    Relationship,
)

from .context import AssemblyContext
from .evidence import machine_evidence
from .id_map import AssemblyIdMap
from .page import layer_uuid_for_pipeline_layer


def build_dimensions_and_relationships(
    ctx: AssemblyContext,
    id_map: AssemblyIdMap,
    layers: list,
) -> tuple[list[DrawingObject], list[Relationship]]:
    if ctx.associations is None:
        return [], []
    page_to_source = ctx.normalize.page_to_source
    objects: list[DrawingObject] = []
    relationships: list[Relationship] = []

    for dim in ctx.associations.dimension_candidates:
        if dim.status != "proposed":
            continue
        scene_id = id_map.object_id(dim.id)
        id_map.register_dimension(dim.id, scene_id)
        layer_id = layer_uuid_for_pipeline_layer(ctx.document_id, "default", layers)
        target_ids: list[str] = []
        for ref in dim.target_refs:
            resolved = id_map.resolve_target(ref.ref_kind, ref.ref_id)
            if resolved is not None:
                target_ids.append(resolved)
        poly = point_witness_polygon(
            dim.witness_start.x,
            dim.witness_start.y,
            dim.witness_end.x,
            dim.witness_end.y,
            page_to_source=page_to_source,
        )
        parsed_value = None
        unit = None
        if dim.parsed_dimension is not None:
            parsed_value = dim.parsed_dimension.value
            unit = dim.parsed_dimension.unit
        objects.append(
            Dimension(
                type="dimension",
                id=scene_id,
                layer_id=layer_id,
                display_text=dim.display_text,
                parsed_value=parsed_value,
                unit=unit,
                witness_start=PagePoint(x=dim.witness_start.x, y=dim.witness_start.y),
                witness_end=PagePoint(x=dim.witness_end.x, y=dim.witness_end.y),
                target_object_ids=target_ids,
                interpretation=Interpretation(
                    state="machine",
                    score=0.78,
                    evidence=[
                        machine_evidence(
                            stage="associate_markup",
                            artifact_id=dim.id,
                            source_polygon=poly,
                        )
                    ],
                ),
            )
        )

    for rel in ctx.associations.relationships:
        if rel.interpretation != "proposed":
            continue
        from_id = id_map.dimension_to_scene.get(rel.from_candidate_id)
        if from_id is None:
            from_id = id_map.annotation_to_scene.get(rel.from_candidate_id)
        if from_id is None:
            from_id = id_map.text_to_scene.get(rel.from_candidate_id)
        to_id = id_map.resolve_target(rel.to_ref_kind, rel.to_ref_id)
        if from_id is None or to_id is None:
            continue
        rel_scene_id = id_map.object_id(rel.id)
        relationships.append(
            Relationship(
                id=rel_scene_id,
                type=rel.type,
                from_id=from_id,
                to_id=to_id,
                interpretation=Interpretation(
                    state="machine",
                    score=0.75,
                    evidence=[
                        machine_evidence(
                            stage="associate_markup",
                            artifact_id=rel.id,
                            source_polygon=point_witness_polygon(
                                0,
                                0,
                                1,
                                1,
                                page_to_source=page_to_source,
                            ),
                            observations={
                                "note": rel.evidence[:120]
                                if len(rel.evidence) <= 120
                                else rel.evidence[:117] + "..."
                            },
                        )
                    ],
                ),
            )
        )
    return objects, relationships


def point_witness_polygon(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    page_to_source,
) -> list:
    from isometric_pipeline.geometry.transforms import apply_mat3
    from isometric_pipeline.scene.models import SourcePoint

    mid_x = (x0 + x1) / 2
    mid_y = (y0 + y1) / 2
    return [
        SourcePoint(x=sx, y=sy)
        for px, py in ((x0, y0), (x1, y1), (mid_x, mid_y))
        for sx, sy in [apply_mat3(page_to_source, px, py)]
    ]
