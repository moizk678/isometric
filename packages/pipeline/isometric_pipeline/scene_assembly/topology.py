"""Topology candidates to junctions and pipe segments."""

from __future__ import annotations

from isometric_pipeline.scene.models import (
    DrawingObject,
    Interpretation,
    Junction,
    LinePrimitive,
    OriginalPrimitive,
    PagePoint,
    PipeSegment,
)
from isometric_pipeline.snapping.artifact import (
    SnappedPrimitiveCandidate,
    SnappedPrimitivesMetadata,
)
from isometric_pipeline.topology.artifact import EdgeCandidate, TopologyMetadata

from .context import AssemblyContext
from .evidence import machine_evidence, point_evidence_polygon
from .id_map import AssemblyIdMap


def _snapped_by_primitive(
    snapped: SnappedPrimitivesMetadata | None,
) -> dict[str, SnappedPrimitiveCandidate]:
    if snapped is None:
        return {}
    return {item.primitive_id: item for item in snapped.candidates}


def _original_for_edge(
    edge: EdgeCandidate, snapped_map: dict[str, SnappedPrimitiveCandidate]
) -> OriginalPrimitive | None:
    for prim_id in edge.source_primitive_ids:
        snap = snapped_map.get(prim_id)
        if snap is not None:
            return OriginalPrimitive(
                start=PagePoint(x=snap.pre_snap.start.x, y=snap.pre_snap.start.y),
                end=PagePoint(x=snap.pre_snap.end.x, y=snap.pre_snap.end.y),
            )
    return None


def build_topology_objects(
    ctx: AssemblyContext,
    id_map: AssemblyIdMap,
    layers: list,
) -> list[DrawingObject]:
    if ctx.topology is None:
        return []
    from .page import layer_uuid_for_pipeline_layer

    topo: TopologyMetadata = ctx.topology
    snapped_map = _snapped_by_primitive(ctx.snapped)
    page_to_source = ctx.normalize.page_to_source
    objects: list[DrawingObject] = []

    for node in topo.nodes:
        scene_id = id_map.object_id(node.id)
        id_map.register_node(node.id, scene_id)
        layer_id = layer_uuid_for_pipeline_layer(
            ctx.document_id, node.layer_ids[0] if node.layer_ids else "default", layers
        )
        poly = point_evidence_polygon(
            node.position.x,
            node.position.y,
            page_to_source=page_to_source,
        )
        interp = Interpretation(
            state="machine",
            score=0.85 if node.status == "confirmed_structure" else 0.7,
            evidence=[
                machine_evidence(
                    stage="infer_topology",
                    artifact_id=node.id,
                    source_polygon=poly,
                    observations={"kind": node.kind},
                )
            ],
        )
        objects.append(
            Junction(
                type="junction",
                id=scene_id,
                layer_id=layer_id,
                position=PagePoint(x=node.position.x, y=node.position.y),
                kind=node.kind,
                interpretation=interp,
            )
        )

    for edge in topo.edges:
        scene_id = id_map.object_id(edge.id)
        id_map.register_edge(edge.id, scene_id)
        layer_id = layer_uuid_for_pipeline_layer(ctx.document_id, edge.layer_id, layers)
        start_scene = id_map.node_to_scene.get(edge.start_node_id)
        end_scene = id_map.node_to_scene.get(edge.end_node_id)
        if start_scene is None or end_scene is None:
            continue
        poly = point_evidence_polygon(
            (edge.start.x + edge.end.x) / 2,
            (edge.start.y + edge.end.y) / 2,
            page_to_source=page_to_source,
            radius=6.0,
        )
        interp = Interpretation(
            state="machine",
            score=0.82,
            evidence=[
                machine_evidence(
                    stage="infer_topology",
                    artifact_id=edge.id,
                    source_polygon=poly,
                )
            ],
        )
        original = _original_for_edge(edge, snapped_map)
        objects.append(
            PipeSegment(
                type="pipe_segment",
                id=scene_id,
                layer_id=layer_id,
                start_node_id=start_scene,
                end_node_id=end_scene,
                primitive=LinePrimitive(
                    kind="line",
                    start=PagePoint(x=edge.start.x, y=edge.start.y),
                    end=PagePoint(x=edge.end.x, y=edge.end.y),
                ),
                original_primitive=original,
                interpretation=interp,
            )
        )
    return objects
