"""Orchestrate scene assembly from pipeline artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field

from isometric_pipeline.scene import (
    DrawingScene,
    dump_scene,
    load_scene,
    validate_scene,
)
from isometric_pipeline.scene.models import (
    SCENE_SCHEMA_VERSION,
    DrawingObject,
)

from .associations import build_dimensions_and_relationships
from .context import AssemblyContext
from .id_map import AssemblyIdMap
from .page import build_layers, build_page
from .review_planner import PlannedReviewItem, plan_review_items
from .symbols import build_symbol_objects
from .text import build_annotation_from_targets, build_text_annotations
from .topology import build_topology_objects
from .unknowns import build_unknown_marks


@dataclass(frozen=True)
class AssemblyResult:
    scene: DrawingScene
    scene_json: str
    review_items: list[PlannedReviewItem]
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, int | float | str] = field(default_factory=dict)


def assemble_scene(ctx: AssemblyContext) -> AssemblyResult:
    id_map = AssemblyIdMap(ctx.document_id)
    warnings = list(ctx.warnings)
    default_layer_name = ctx.profile.assembly.default_layer_name
    layers = build_layers(ctx.document_id, ctx.masks, default_name=default_layer_name)
    page = build_page(ctx.normalize)

    objects: list[DrawingObject] = []
    objects.extend(build_topology_objects(ctx, id_map, layers))
    objects.extend(build_symbol_objects(ctx, id_map, layers))

    dimension_text_ids: set[str] = set()
    annotation_text_ids: set[str] = set()
    if ctx.associations is not None:
        for dim in ctx.associations.dimension_candidates:
            dimension_text_ids.add(dim.text_candidate_id)
        for ann in ctx.associations.annotation_targets:
            annotation_text_ids.add(ann.text_candidate_id)

    text_by_id = {}
    if ctx.text is not None:
        text_by_id = {c.id: c for c in ctx.text.candidates}

    objects.extend(
        build_text_annotations(
            ctx,
            id_map,
            layers,
            dimension_text_ids=dimension_text_ids,
            annotation_candidate_text_ids=annotation_text_ids,
        )
    )
    objects.extend(build_annotation_from_targets(ctx, id_map, layers, text_by_id))

    dim_objects, relationships = build_dimensions_and_relationships(ctx, id_map, layers)
    objects.extend(dim_objects)

    covered_regions: set[str] = set()
    if ctx.text is not None:
        covered_regions.update(c.region_id for c in ctx.text.candidates)
    if ctx.symbols is not None:
        covered_regions.update(c.region_id for c in ctx.symbols.candidates)
    if ctx.associations is not None:
        for dim in ctx.associations.dimension_candidates:
            covered_regions.add(dim.region_id)
        for ann in ctx.associations.annotation_targets:
            if ann.text_candidate_id in text_by_id:
                covered_regions.add(text_by_id[ann.text_candidate_id].region_id)
    objects.extend(
        build_unknown_marks(ctx, id_map, layers, covered_region_ids=covered_regions)
    )

    scene_kwargs: dict = {
        "schema_version": SCENE_SCHEMA_VERSION,
        "document_id": str(ctx.document_id),
        "revision_id": str(ctx.revision_id),
        "profile_id": "piping_isometric",
        "page": page,
        "layers": layers,
        "objects": objects,
        "relationships": relationships,
    }
    if ctx.parent_revision_id is not None:
        scene_kwargs["parent_revision_id"] = str(ctx.parent_revision_id)
    scene = DrawingScene(**scene_kwargs)

    validate_scene(scene, catalog=ctx.symbol_library)
    scene_json = dump_scene(scene)
    load_scene(scene_json, catalog=ctx.symbol_library)

    review_items = plan_review_items(ctx, id_map)
    metrics = {
        "object_count": len(objects),
        "relationship_count": len(relationships),
        "review_item_count": len(review_items),
        "junction_count": sum(1 for o in objects if o.type == "junction"),
        "pipe_count": sum(1 for o in objects if o.type == "pipe_segment"),
    }
    return AssemblyResult(
        scene=scene,
        scene_json=scene_json,
        review_items=review_items,
        warnings=warnings,
        metrics=metrics,
    )
