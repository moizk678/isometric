"""Residual unknown regions without committed interpretations."""

from __future__ import annotations

from isometric_pipeline.scene.models import DrawingObject, Interpretation, UnknownMark

from .context import AssemblyContext
from .evidence import bbox_to_source_polygon, machine_evidence
from .id_map import AssemblyIdMap
from .page import layer_uuid_for_pipeline_layer


def build_unknown_marks(
    ctx: AssemblyContext,
    id_map: AssemblyIdMap,
    layers: list,
    *,
    covered_region_ids: set[str],
) -> list[DrawingObject]:
    if ctx.regions is None:
        return []
    page_to_source = ctx.normalize.page_to_source
    objects: list[DrawingObject] = []
    for region in ctx.regions.regions:
        if region.id in covered_region_ids:
            continue
        if region.kind == "arrow":
            continue
        scene_id = id_map.object_id(f"region_{region.id}")
        layer_id = layer_uuid_for_pipeline_layer(ctx.document_id, "default", layers)
        poly = bbox_to_source_polygon(
            x=region.bbox.x,
            y=region.bbox.y,
            width=region.bbox.width,
            height=region.bbox.height,
            page_to_source=page_to_source,
        )
        objects.append(
            UnknownMark(
                type="unknown_mark",
                id=scene_id,
                layer_id=layer_id,
                source_crop_id=region.crop_uri,
                candidate_labels=[region.kind],
                interpretation=Interpretation(
                    state="machine",
                    score=0.35,
                    evidence=[
                        machine_evidence(
                            stage="detect_regions",
                            artifact_id=region.id,
                            source_polygon=poly,
                        )
                    ],
                ),
            )
        )
    return objects
