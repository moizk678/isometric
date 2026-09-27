"""Symbol candidates to scene symbols and unknown marks."""

from __future__ import annotations

from isometric_pipeline.scene.models import (
    DrawingObject,
    Interpretation,
    PagePoint,
    SymbolObject,
    UnknownMark,
)

from .context import AssemblyContext
from .evidence import bbox_to_source_polygon, machine_evidence
from .id_map import AssemblyIdMap
from .page import layer_uuid_for_pipeline_layer


def build_symbol_objects(
    ctx: AssemblyContext,
    id_map: AssemblyIdMap,
    layers: list,
) -> list[DrawingObject]:
    if ctx.symbols is None:
        return []
    profile = ctx.profile.symbols
    assembly = ctx.profile.assembly
    page_to_source = ctx.normalize.page_to_source
    objects: list[DrawingObject] = []
    catalog = ctx.symbol_library

    for candidate in ctx.symbols.candidates:
        layer_id = layer_uuid_for_pipeline_layer(ctx.document_id, "default", layers)
        poly = bbox_to_source_polygon(
            x=candidate.bbox.x,
            y=candidate.bbox.y,
            width=candidate.bbox.width,
            height=candidate.bbox.height,
            page_to_source=page_to_source,
        )
        if candidate.status != "proposed" or not candidate.alternatives:
            scene_id = id_map.object_id(f"unknown_{candidate.id}")
            labels = [alt.symbol_id for alt in candidate.alternatives[:3]]
            if not labels:
                labels = ["unknown"]
            objects.append(
                UnknownMark(
                    type="unknown_mark",
                    id=scene_id,
                    layer_id=layer_id,
                    source_crop_id=candidate.crop_uri,
                    candidate_labels=labels,
                    interpretation=Interpretation(
                        state="machine",
                        score=0.4,
                        evidence=[
                            machine_evidence(
                                stage="classify_symbol_regions",
                                artifact_id=candidate.id,
                                source_polygon=poly,
                            )
                        ],
                    ),
                )
            )
            continue

        top = candidate.alternatives[0]
        combined = (top.shape_score + top.text_score + top.topology_score) / 3.0
        if combined < assembly.min_symbol_combined_score:
            continue
        if top.symbol_id not in profile.allowed_symbol_ids:
            continue
        if catalog.port_names(top.symbol_id) is None:
            continue

        scene_id = id_map.object_id(candidate.id)
        id_map.register_symbol(candidate.id, scene_id)
        port_names = catalog.port_names(top.symbol_id)
        assert port_names is not None
        port_node_ids: dict[str, str | None] = {
            port: None for port in sorted(port_names)
        }
        for attachment in candidate.proposed_port_attachments:
            if attachment.port_name not in port_node_ids:
                continue
            port_node_ids[attachment.port_name] = (
                id_map.node_to_scene.get(attachment.node_id)
                if attachment.node_id
                else None
            )

        objects.append(
            SymbolObject(
                type="symbol",
                id=scene_id,
                layer_id=layer_id,
                symbol_id=top.symbol_id,
                anchor=PagePoint(x=candidate.anchor.x, y=candidate.anchor.y),
                rotation_degrees=candidate.rotation_deg,
                port_node_ids=port_node_ids,
                interpretation=Interpretation(
                    state="machine",
                    score=min(1.0, combined),
                    evidence=[
                        machine_evidence(
                            stage="classify_symbol_regions",
                            artifact_id=candidate.id,
                            source_polygon=poly,
                            observations={"symbolId": top.symbol_id},
                        )
                    ],
                ),
            )
        )
    return objects
