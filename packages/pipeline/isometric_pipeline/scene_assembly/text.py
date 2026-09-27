"""OCR text candidates to annotations (non-dimension)."""

from __future__ import annotations

from isometric_pipeline.ocr.artifact import TextCandidate
from isometric_pipeline.scene.models import (
    Annotation,
    DrawingObject,
    Interpretation,
    PagePoint,
)

from .context import AssemblyContext
from .evidence import bbox_to_source_polygon, machine_evidence
from .id_map import AssemblyIdMap
from .page import layer_uuid_for_pipeline_layer


def build_text_annotations(
    ctx: AssemblyContext,
    id_map: AssemblyIdMap,
    layers: list,
    *,
    dimension_text_ids: set[str],
    annotation_candidate_text_ids: set[str],
) -> list[DrawingObject]:
    if ctx.text is None:
        return []
    page_to_source = ctx.normalize.page_to_source
    objects: list[DrawingObject] = []

    for candidate in ctx.text.candidates:
        if candidate.id in dimension_text_ids:
            continue
        if candidate.id in annotation_candidate_text_ids:
            continue
        if candidate.region_kind not in ("text", "dimension"):
            continue
        if candidate.status not in ("proposed", "unknown"):
            continue
        display = candidate.normalized_text or candidate.raw_text
        if not display:
            continue

        scene_id = id_map.object_id(candidate.id)
        id_map.register_text(candidate.id, scene_id)
        id_map.register_annotation(candidate.id, scene_id)
        layer_id = layer_uuid_for_pipeline_layer(ctx.document_id, "default", layers)
        poly = bbox_to_source_polygon(
            x=candidate.bbox.x,
            y=candidate.bbox.y,
            width=candidate.bbox.width,
            height=candidate.bbox.height,
            page_to_source=page_to_source,
        )
        alts = [alt.text for alt in candidate.alternatives[:5]]
        score = (
            candidate.ocr_confidence if candidate.ocr_confidence is not None else 0.6
        )
        objects.append(
            Annotation(
                type="annotation",
                id=scene_id,
                layer_id=layer_id,
                recognized_text=candidate.raw_text or display,
                normalized_text=display,
                alternatives=alts,
                anchor=PagePoint(
                    x=candidate.bbox.x + candidate.bbox.width / 2,
                    y=candidate.bbox.y + candidate.bbox.height / 2,
                ),
                interpretation=Interpretation(
                    state="machine",
                    score=min(1.0, score),
                    evidence=[
                        machine_evidence(
                            stage="transcribe_regions",
                            artifact_id=candidate.id,
                            source_polygon=poly,
                        )
                    ],
                ),
            )
        )
    return objects


def build_annotation_from_targets(
    ctx: AssemblyContext,
    id_map: AssemblyIdMap,
    layers: list,
    text_by_id: dict[str, TextCandidate],
) -> list[DrawingObject]:
    if ctx.associations is None:
        return []
    page_to_source = ctx.normalize.page_to_source
    objects: list[DrawingObject] = []

    for ann in ctx.associations.annotation_targets:
        text = text_by_id.get(ann.text_candidate_id)
        if text is None:
            continue
        display = text.normalized_text or text.raw_text or ""
        scene_id = id_map.object_id(ann.id)
        id_map.register_text(ann.text_candidate_id, scene_id)
        id_map.register_annotation(ann.id, scene_id)
        layer_id = layer_uuid_for_pipeline_layer(ctx.document_id, "default", layers)
        poly = bbox_to_source_polygon(
            x=text.bbox.x,
            y=text.bbox.y,
            width=text.bbox.width,
            height=text.bbox.height,
            page_to_source=page_to_source,
        )
        target_id = None
        if ann.alternatives and ann.status == "proposed":
            primary = ann.alternatives[0]
            if len(ann.alternatives) == 1 or (
                ann.alternatives[0].score - ann.alternatives[1].score
                >= ctx.profile.associations.target_ambiguity_margin
            ):
                target_id = id_map.resolve_target(primary.ref_kind, primary.ref_id)

        alt_labels = [alt.text for alt in text.alternatives[:5]] if text.alternatives else []
        if not alt_labels:
            alt_labels = [display] if display else []

        annotation_kwargs: dict = {
            "type": "annotation",
            "id": scene_id,
            "layer_id": layer_id,
            "recognized_text": text.raw_text or display,
            "normalized_text": display,
            "alternatives": alt_labels,
            "anchor": PagePoint(
                x=text.bbox.x + text.bbox.width / 2,
                y=text.bbox.y + text.bbox.height / 2,
            ),
            "interpretation": Interpretation(
                state="machine",
                score=0.72,
                evidence=[
                    machine_evidence(
                        stage="associate_markup",
                        artifact_id=ann.id,
                        source_polygon=poly,
                    )
                ],
            ),
        }
        if target_id is not None:
            annotation_kwargs["target_object_id"] = target_id
        objects.append(Annotation(**annotation_kwargs))
    return objects
