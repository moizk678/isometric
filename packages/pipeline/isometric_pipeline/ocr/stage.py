"""Transcribe protected text/dimension regions."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Literal

import numpy as np

from isometric_pipeline.masks.util import decode_page_rgb
from isometric_pipeline.normalize.page import json_bytes
from isometric_pipeline.ocr.adapter import OcrEngine, default_ocr_engine
from isometric_pipeline.ocr.artifact import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    OcrModelInfo,
    OcrReviewItem,
    PageBBox,
    TextAlternative,
    TextCandidate,
    TextCandidatesMetadata,
)
from isometric_pipeline.ocr.context import nearby_topology, rerank_alternatives
from isometric_pipeline.ocr.diagnostics import ocr_overlay_png
from isometric_pipeline.ocr.dimensions import parse_dimension_text
from isometric_pipeline.ocr.preprocess import crop_region, deskew_image
from isometric_pipeline.ocr.validate import validate_text_candidates
from isometric_pipeline.ocr.vocabulary import (
    OcrVocabulary,
    propose_normalized_text,
    vocabulary_alternatives,
)
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.artifact import RegionsMetadata
from isometric_pipeline.topology.artifact import TopologyMetadata

StageStatus = Literal["succeeded", "partial"]

_OCR_KINDS = frozenset({"text", "dimension"})


@dataclass(frozen=True)
class TranscribeRegionsResult:
    status: StageStatus
    metadata: TextCandidatesMetadata
    text_candidates_json: bytes
    overlay_png: bytes
    warnings: list[str]
    metrics: dict[str, float | int | bool]
    content_hash: str


def transcribe_regions(
    page_png: bytes,
    regions: RegionsMetadata,
    *,
    regions_json_uri: str,
    text_candidates_json_uri: str,
    region_crops: dict[str, bytes] | None = None,
    topology: TopologyMetadata | None = None,
    topology_json_uri: str | None = None,
    ocr_engine: OcrEngine | None = None,
    profile_version: str = DEFAULT_PIPING_PROFILE_VERSION,
) -> TranscribeRegionsResult:
    profile = load_piping_profile(profile_version)
    ocr_profile = profile.ocr
    rgb = decode_page_rgb(page_png)
    height, width = rgb.shape[:2]

    vocabulary = OcrVocabulary.from_profile(
        list(ocr_profile.vocabulary_terms),
        dict(ocr_profile.abbreviations),
    )
    engine = ocr_engine or default_ocr_engine(
        ocr_profile.model_id,
        ocr_profile.model_revision,
    )
    preprocessing = {
        "cropPaddingPx": ocr_profile.crop_padding_px,
        "deskewEnabled": ocr_profile.deskew_enabled,
    }
    model_info = OcrModelInfo(
        name=ocr_profile.model_id,
        revision=ocr_profile.model_revision,
        preprocessing=preprocessing,
    )

    warnings: list[str] = []
    candidates: list[TextCandidate] = []
    review_items: list[OcrReviewItem] = []
    region_ids = {r.id for r in regions.regions}

    for region in regions.regions:
        if region.kind not in _OCR_KINDS:
            continue
        candidate_id = f"txt_{region.id}"
        bbox = PageBBox(
            x=region.bbox.x,
            y=region.bbox.y,
            width=region.bbox.width,
            height=region.bbox.height,
        )
        topo_ref = nearby_topology(
            bbox, topology, max_distance_px=ocr_profile.context_radius_px
        )
        rotation_deg = 0.0
        if region_crops and region.id in region_crops:
            crop_rgb = _decode_crop_rgb(region_crops[region.id])
            if ocr_profile.deskew_enabled and crop_rgb.size > 0:
                crop_rgb, rotation_deg = deskew_image(crop_rgb)
        else:
            preprocessed = crop_region(
                rgb,
                region.bbox,
                padding_px=ocr_profile.crop_padding_px,
                deskew=ocr_profile.deskew_enabled,
            )
            crop_rgb = preprocessed.rgb
            rotation_deg = preprocessed.rotation_deg

        status: Literal["proposed", "unreadable", "unknown"] = "proposed"
        raw_text: str | None = None
        normalized: str | None = None
        ocr_confidence: float | None = None
        alternatives: list[TextAlternative] = []

        try:
            recognition = engine.recognize(crop_rgb, region_id=region.id)
            raw_text = recognition.raw_text.strip() if recognition.raw_text else ""
            ocr_confidence = recognition.confidence
            for alt_text, score in recognition.alternatives:
                if alt_text:
                    alternatives.append(
                        TextAlternative(text=alt_text, score=score, source="ocr")
                    )
            if raw_text and not any(a.text == raw_text for a in alternatives):
                alternatives.append(
                    TextAlternative(
                        text=raw_text,
                        score=recognition.confidence,
                        source="ocr",
                    )
                )
        except Exception:
            status = "unreadable"
            review_items.append(
                OcrReviewItem(
                    id=f"rev_{uuid.uuid4().hex[:12]}",
                    code="ocr.unreadable",
                    message="OCR engine failed for region crop",
                    text_candidate_id=candidate_id,
                    region_id=region.id,
                    bbox=bbox,
                )
            )

        if status != "unreadable":
            if not raw_text:
                status = "unreadable"
                review_items.append(
                    OcrReviewItem(
                        id=f"rev_{uuid.uuid4().hex[:12]}",
                        code="ocr.unreadable",
                        message="No transcription returned",
                        text_candidate_id=candidate_id,
                        region_id=region.id,
                        bbox=bbox,
                    )
                )
            elif (
                ocr_confidence is not None
                and ocr_confidence < ocr_profile.min_confidence
            ):
                review_items.append(
                    OcrReviewItem(
                        id=f"rev_{uuid.uuid4().hex[:12]}",
                        code="ocr.low_confidence",
                        message=f"OCR confidence {ocr_confidence:.2f} below threshold",
                        text_candidate_id=candidate_id,
                        region_id=region.id,
                        bbox=bbox,
                    )
                )

        if raw_text and status != "unreadable":
            normalized = propose_normalized_text(raw_text, vocabulary)
            for alt_text, score in vocabulary_alternatives(raw_text, vocabulary):
                alternatives.append(
                    TextAlternative(text=alt_text, score=score, source="vocabulary")
                )

        alternatives = rerank_alternatives(
            alternatives,
            nearby_node_count=len(topo_ref.node_ids),
        )

        ocr_alternatives = [a for a in alternatives if a.source == "ocr"]
        if len(ocr_alternatives) >= 2:
            ocr_alternatives = sorted(
                ocr_alternatives, key=lambda a: a.score, reverse=True
            )
            top = ocr_alternatives[0].score
            second = ocr_alternatives[1].score
            if top - second < ocr_profile.conflict_margin:
                review_items.append(
                    OcrReviewItem(
                        id=f"rev_{uuid.uuid4().hex[:12]}",
                        code="ocr.conflicting_readings",
                        message="Competing OCR readings are close in score",
                        text_candidate_id=candidate_id,
                        region_id=region.id,
                        bbox=bbox,
                    )
                )

        parsed = parse_dimension_text(raw_text) if region.kind == "dimension" else None
        if parsed and parsed.status == "ambiguous":
            review_items.append(
                OcrReviewItem(
                    id=f"rev_{uuid.uuid4().hex[:12]}",
                    code="ocr.dimension_ambiguous",
                    message="Dimension punctuation could not be resolved",
                    text_candidate_id=candidate_id,
                    region_id=region.id,
                    bbox=bbox,
                )
            )

        candidates.append(
            TextCandidate(
                id=candidate_id,
                region_id=region.id,
                region_kind=region.kind,
                bbox=bbox,
                crop_uri=region.crop_uri,
                rotation_deg=rotation_deg,
                raw_text=raw_text if status != "unreadable" else None,
                normalized_text=normalized,
                alternatives=alternatives,
                parsed_dimension=parsed,
                status=status,
                nearby_topology=topo_ref,
                ocr_confidence=ocr_confidence,
            )
        )

    metadata = TextCandidatesMetadata(
        schema_version=SCHEMA_VERSION,
        producer_version=PRODUCER_VERSION,
        profile_version=profile_version,
        page_width_px=width,
        page_height_px=height,
        regions_metadata_uri=regions_json_uri,
        topology_metadata_uri=topology_json_uri,
        model=model_info,
        candidates=candidates,
        review_items=review_items,
        warnings=warnings,
    )

    validation_errors = validate_text_candidates(metadata, region_ids=region_ids)
    if validation_errors:
        raise ValueError(
            "text candidates validation failed: " + "; ".join(validation_errors[:5])
        )

    text_json = json_bytes(metadata.to_wire())
    overlay = ocr_overlay_png(rgb, metadata)
    content_hash = hashlib.sha256(text_json).hexdigest()[:16]

    status_out: StageStatus = "succeeded"
    if review_items or any(c.status == "unreadable" for c in candidates):
        status_out = "partial"

    metrics: dict[str, float | int | bool] = {
        "candidate_count": len(candidates),
        "review_item_count": len(review_items),
        "unreadable_count": sum(1 for c in candidates if c.status == "unreadable"),
    }

    return TranscribeRegionsResult(
        status=status_out,
        metadata=metadata,
        text_candidates_json=text_json,
        overlay_png=overlay,
        warnings=warnings,
        metrics=metrics,
        content_hash=content_hash,
    )


def _decode_crop_rgb(png: bytes) -> np.ndarray:
    import io

    from PIL import Image

    with Image.open(io.BytesIO(png)) as image:
        return np.array(image.convert("RGB"))
