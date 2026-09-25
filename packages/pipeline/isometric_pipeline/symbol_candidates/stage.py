"""Classify symbol and arrow regions into engineering symbol candidates."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Literal

import numpy as np

from isometric_pipeline.masks.util import decode_page_rgb
from isometric_pipeline.normalize.page import json_bytes
from isometric_pipeline.ocr.artifact import TextCandidatesMetadata
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.artifact import RegionsMetadata
from isometric_pipeline.render.symbols import load_symbol_library
from isometric_pipeline.symbol_candidates.adapter import (
    SymbolClassifier,
    UnavailableSymbolClassifier,
    default_symbol_classifier,
)
from isometric_pipeline.symbol_candidates.artifact import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    ClassifierInfo,
    PageBBox,
    SymbolCandidate,
    SymbolCandidatesMetadata,
    SymbolLabelAlternative,
    SymbolReviewItem,
)
from isometric_pipeline.symbol_candidates.context import (
    anchor_point,
    nearby_text_candidates,
    nearby_topology,
    structural_junction_only,
)
from isometric_pipeline.symbol_candidates.diagnostics import symbol_overlay_png
from isometric_pipeline.symbol_candidates.ports import (
    combined_score,
    propose_port_attachments,
)
from isometric_pipeline.symbol_candidates.validate import validate_symbol_candidates
from isometric_pipeline.topology.artifact import TopologyMetadata

StageStatus = Literal["succeeded", "partial"]

_SYMBOL_KINDS = frozenset({"symbol", "arrow"})


@dataclass(frozen=True)
class ClassifySymbolRegionsResult:
    status: StageStatus
    metadata: SymbolCandidatesMetadata
    symbol_candidates_json: bytes
    overlay_png: bytes
    warnings: list[str]
    metrics: dict[str, float | int | bool]
    content_hash: str


def classify_symbol_regions(
    page_png: bytes,
    regions: RegionsMetadata,
    *,
    regions_json_uri: str,
    symbol_candidates_json_uri: str,
    region_crops: dict[str, bytes] | None = None,
    topology: TopologyMetadata | None = None,
    topology_json_uri: str | None = None,
    text_candidates: TextCandidatesMetadata | None = None,
    text_candidates_json_uri: str | None = None,
    classifier: SymbolClassifier | None = None,
    profile_version: str = DEFAULT_PIPING_PROFILE_VERSION,
) -> ClassifySymbolRegionsResult:
    profile = load_piping_profile(profile_version)
    sym_profile = profile.symbols
    library = load_symbol_library(sym_profile.library_version)
    rgb = decode_page_rgb(page_png)
    height, width = rgb.shape[:2]

    engine: SymbolClassifier
    classifier_unavailable = False
    if classifier is not None:
        engine = classifier
    else:
        try:
            engine = default_symbol_classifier(sym_profile.classifier_backend)
        except Exception:
            engine = UnavailableSymbolClassifier()
            classifier_unavailable = True

    classifier_info = ClassifierInfo(
        backend=sym_profile.classifier_backend,
        version="classify_symbol_regions@1.0.0",
        parameters={
            "minShapeScore": sym_profile.min_shape_score,
            "minCombinedMargin": sym_profile.min_combined_margin,
            "portAttachTolerancePx": sym_profile.port_attach_tolerance_px,
        },
    )

    warnings: list[str] = []
    if classifier_unavailable:
        warnings.append("symbol_classifier_unavailable")

    candidates: list[SymbolCandidate] = []
    review_items: list[SymbolReviewItem] = []
    region_ids = {r.id for r in regions.regions}

    for region in regions.regions:
        if region.kind not in _SYMBOL_KINDS:
            continue
        candidate_id = f"sym_{region.id}"
        bbox = PageBBox(
            x=region.bbox.x,
            y=region.bbox.y,
            width=region.bbox.width,
            height=region.bbox.height,
        )
        anchor = anchor_point(bbox)
        topo_ref = nearby_topology(
            bbox,
            topology,
            radius_px=sym_profile.port_attach_tolerance_px * 2,
        )
        texts = nearby_text_candidates(
            bbox,
            text_candidates,
            radius_px=sym_profile.nearby_text_radius_px,
        )
        text_ids = [t.id for t in texts]

        is_structural, structural_node = structural_junction_only(
            bbox,
            topology,
            tolerance_px=sym_profile.port_attach_tolerance_px,
        )
        if is_structural and sym_profile.suppress_on_structural_junction:
            review_items.append(
                SymbolReviewItem(
                    id=f"rev_{uuid.uuid4().hex[:12]}",
                    code="symbol.structural_junction_only",
                    message=(
                        f"Symbol region overlaps structural junction {structural_node}; "
                        "fitting symbol suppressed"
                    ),
                    symbol_candidate_id=candidate_id,
                    region_id=region.id,
                    bbox=bbox,
                )
            )

        crop_rgb = _crop_rgb(rgb, region, region_crops)
        status: Literal["proposed", "unknown", "unreadable"] = "proposed"
        rotation_deg = 0.0
        alternatives: list[SymbolLabelAlternative] = []
        port_attachments: list = []

        center = (anchor.x, anchor.y)
        try:
            if crop_rgb.size == 0:
                raise ValueError("empty crop")
            scored = engine.score(
                crop_rgb,
                region_id=region.id,
                region_kind=region.kind,
                topology=topology,
                text_candidates=text_candidates,
                library=library,
                profile=sym_profile,
                bbox_center=center,
            )
            rotation_deg = scored.rotation_deg
            for row in scored.alternatives:
                if row.symbol_id not in sym_profile.allowed_symbol_ids:
                    continue
                alternatives.append(
                    SymbolLabelAlternative(
                        symbol_id=row.symbol_id,
                        shape_score=row.shape_score,
                        text_score=row.text_score,
                        topology_score=row.topology_score,
                    )
                )
        except Exception:
            status = "unreadable"
            review_items.append(
                SymbolReviewItem(
                    id=f"rev_{uuid.uuid4().hex[:12]}",
                    code="symbol.classifier_unavailable",
                    message="Symbol classifier failed for region crop",
                    symbol_candidate_id=candidate_id,
                    region_id=region.id,
                    bbox=bbox,
                )
            )

        if status != "unreadable":
            if not alternatives:
                status = "unknown"
                alternatives = [
                    SymbolLabelAlternative(
                        symbol_id="unknown",
                        shape_score=0.0,
                        text_score=0.0,
                        topology_score=0.0,
                    )
                ]
            else:
                alternatives.sort(key=combined_score, reverse=True)
                top = alternatives[0]
                second = alternatives[1] if len(alternatives) > 1 else None
                if top.shape_score < sym_profile.min_shape_score:
                    status = "unknown"
                    review_items.append(
                        SymbolReviewItem(
                            id=f"rev_{uuid.uuid4().hex[:12]}",
                            code="symbol.ocr_insufficient_evidence",
                            message="Shape evidence too weak; OCR cannot force symbol type",
                            symbol_candidate_id=candidate_id,
                            region_id=region.id,
                            bbox=bbox,
                        )
                    )
                elif second is not None:
                    margin = combined_score(top) - combined_score(second)
                    if margin < sym_profile.min_combined_margin:
                        review_items.append(
                            SymbolReviewItem(
                                id=f"rev_{uuid.uuid4().hex[:12]}",
                                code="symbol.low_margin",
                                message="Top symbol alternatives are close in combined score",
                                symbol_candidate_id=candidate_id,
                                region_id=region.id,
                                bbox=bbox,
                            )
                        )
                if is_structural and sym_profile.suppress_on_structural_junction:
                    fitting_ids = frozenset({"tee_fitting", "elbow_fitting"})
                    alternatives = [
                        SymbolLabelAlternative(
                            symbol_id="unknown"
                            if a.symbol_id in fitting_ids
                            else a.symbol_id,
                            shape_score=a.shape_score,
                            text_score=a.text_score,
                            topology_score=a.topology_score,
                        )
                        for a in alternatives
                    ]
                    alternatives.sort(key=combined_score, reverse=True)
                    if alternatives[0].symbol_id == "unknown":
                        status = "unknown"

                top_id = alternatives[0].symbol_id
                port_attachments, port_reviews = propose_port_attachments(
                    top_id,
                    library,
                    topology,
                    anchor,
                    rotation_deg,
                    sym_profile,
                )
                for pr in port_reviews:
                    pr.symbol_candidate_id = candidate_id
                    pr.region_id = region.id
                    pr.bbox = bbox
                review_items.extend(port_reviews)

        candidates.append(
            SymbolCandidate(
                id=candidate_id,
                region_id=region.id,
                region_kind=region.kind,
                bbox=bbox,
                crop_uri=region.crop_uri,
                anchor=anchor,
                rotation_deg=rotation_deg,
                status=status,
                alternatives=alternatives,
                proposed_port_attachments=port_attachments,
                nearby_text_candidate_ids=text_ids,
                nearby_topology=topo_ref,
            )
        )

    metadata = SymbolCandidatesMetadata(
        schema_version=SCHEMA_VERSION,
        producer_version=PRODUCER_VERSION,
        profile_version=profile_version,
        page_width_px=width,
        page_height_px=height,
        regions_metadata_uri=regions_json_uri,
        topology_metadata_uri=topology_json_uri,
        text_candidates_metadata_uri=text_candidates_json_uri,
        symbol_library_version=sym_profile.library_version,
        classifier=classifier_info,
        candidates=candidates,
        review_items=review_items,
        warnings=warnings,
    )

    validation_errors = validate_symbol_candidates(
        metadata, region_ids=region_ids, library=library
    )
    if validation_errors:
        raise ValueError(
            "symbol candidates validation failed: " + "; ".join(validation_errors[:5])
        )

    symbol_json = json_bytes(metadata.to_wire())
    overlay = symbol_overlay_png(rgb, metadata)
    content_hash = hashlib.sha256(symbol_json).hexdigest()[:16]

    status_out: StageStatus = "succeeded"
    if (
        classifier_unavailable
        or review_items
        or any(c.status in ("unreadable", "unknown") for c in candidates)
    ):
        status_out = "partial"

    metrics: dict[str, float | int | bool] = {
        "candidate_count": len(candidates),
        "review_item_count": len(review_items),
        "unknown_count": sum(1 for c in candidates if c.status == "unknown"),
    }

    return ClassifySymbolRegionsResult(
        status=status_out,
        metadata=metadata,
        symbol_candidates_json=symbol_json,
        overlay_png=overlay,
        warnings=warnings,
        metrics=metrics,
        content_hash=content_hash,
    )


def _crop_rgb(
    page_rgb: np.ndarray,
    region,
    region_crops: dict[str, bytes] | None,
) -> np.ndarray:
    if region_crops and region.id in region_crops:
        return _decode_crop_rgb(region_crops[region.id])
    x0 = max(0, int(region.bbox.x))
    y0 = max(0, int(region.bbox.y))
    x1 = min(page_rgb.shape[1], int(region.bbox.x + region.bbox.width))
    y1 = min(page_rgb.shape[0], int(region.bbox.y + region.bbox.height))
    if x1 <= x0 or y1 <= y0:
        return np.zeros((0, 0, 3), dtype=np.uint8)
    return page_rgb[y0:y1, x0:x1].copy()


def _decode_crop_rgb(png: bytes) -> np.ndarray:
    import io

    from PIL import Image

    with Image.open(io.BytesIO(png)) as image:
        return np.array(image.convert("RGB"))
