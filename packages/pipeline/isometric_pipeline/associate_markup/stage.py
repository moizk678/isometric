"""Associate dimensions, callouts, and annotation targets."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

import numpy as np

from isometric_pipeline.associate_markup.annotations import build_annotation_targets
from isometric_pipeline.associate_markup.artifact import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    AssociationCandidatesMetadata,
    AssociationReviewItem,
)
from isometric_pipeline.associate_markup.diagnostics import association_overlay_png
from isometric_pipeline.associate_markup.dimensions import build_dimension_candidates
from isometric_pipeline.associate_markup.geometry import detect_markup_geometry
from isometric_pipeline.associate_markup.relationships import build_relationships
from isometric_pipeline.associate_markup.review import review_item_id
from isometric_pipeline.associate_markup.validate import validate_association_candidates
from isometric_pipeline.masks.util import decode_page_rgb
from isometric_pipeline.normalize.page import json_bytes
from isometric_pipeline.ocr.artifact import TextCandidatesMetadata
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.artifact import RegionsMetadata
from isometric_pipeline.symbol_candidates.artifact import SymbolCandidatesMetadata
from isometric_pipeline.topology.artifact import TopologyMetadata

StageStatus = Literal["succeeded", "partial"]


@dataclass(frozen=True)
class AssociateMarkupResult:
    status: StageStatus
    metadata: AssociationCandidatesMetadata
    association_candidates_json: bytes
    overlay_png: bytes
    warnings: list[str]
    metrics: dict[str, float | int | bool]
    content_hash: str


def associate_markup(
    page_png: bytes,
    regions: RegionsMetadata,
    *,
    regions_json_uri: str,
    association_candidates_json_uri: str,
    geometry_ink_png: bytes | None = None,
    masks_metadata_uri: str | None = None,
    topology: TopologyMetadata | None = None,
    topology_json_uri: str | None = None,
    text_candidates: TextCandidatesMetadata | None = None,
    text_candidates_json_uri: str | None = None,
    symbol_candidates: SymbolCandidatesMetadata | None = None,
    symbol_candidates_json_uri: str | None = None,
    profile_version: str = DEFAULT_PIPING_PROFILE_VERSION,
) -> AssociateMarkupResult:
    profile = load_piping_profile(profile_version)
    assoc_profile = profile.associations
    rgb = decode_page_rgb(page_png)
    height, width = rgb.shape[:2]

    warnings: list[str] = []
    review_items: list[AssociationReviewItem] = []

    if text_candidates is None:
        warnings.append("text_candidates_missing")
        review_items.append(
            AssociationReviewItem(
                id=review_item_id("association.upstream_missing", "text"),
                code="association.upstream_missing",
                message="Text candidates artifact missing",
            )
        )
        text_list: list = []
    else:
        text_list = list(text_candidates.candidates)

    if symbol_candidates is None:
        warnings.append("symbol_candidates_missing")
        sym_list: list = []
    else:
        sym_list = list(symbol_candidates.candidates)

    if topology is None:
        warnings.append("topology_missing")

    geometry_ink: np.ndarray | None = None
    dimension_geometry = []
    if geometry_ink_png is not None:
        from isometric_pipeline.centerlines.util import decode_mask_png

        geometry_ink = decode_mask_png(geometry_ink_png, height, width)
        dimension_geometry = detect_markup_geometry(
            geometry_ink,
            regions=list(regions.regions),
            topology=topology,
            profile=assoc_profile,
        )
    else:
        warnings.append("geometry_ink_missing")

    dim_candidates, dim_reviews = build_dimension_candidates(
        text_list,
        dimension_geometry,
        topology,
        assoc_profile,
    )
    ann_candidates, ann_reviews = build_annotation_targets(
        text_list,
        list(regions.regions),
        sym_list,
        topology,
        geometry_ink,
        assoc_profile,
    )
    relationships = build_relationships(dim_candidates, ann_candidates, assoc_profile)
    review_items.extend(dim_reviews)
    review_items.extend(ann_reviews)

    metadata = AssociationCandidatesMetadata(
        schema_version=SCHEMA_VERSION,
        producer_version=PRODUCER_VERSION,
        profile_version=profile_version,
        page_width_px=width,
        page_height_px=height,
        regions_metadata_uri=regions_json_uri,
        masks_metadata_uri=masks_metadata_uri,
        topology_metadata_uri=topology_json_uri,
        text_candidates_metadata_uri=text_candidates_json_uri,
        symbol_candidates_metadata_uri=symbol_candidates_json_uri,
        dimension_geometry=dimension_geometry,
        dimension_candidates=dim_candidates,
        annotation_targets=ann_candidates,
        relationships=relationships,
        review_items=review_items,
        warnings=warnings,
    )

    text_ids = {t.id for t in text_list}
    region_ids = {r.id for r in regions.regions}
    edge_ids = {e.id for e in topology.edges} if topology else set()
    node_ids = {n.id for n in topology.nodes} if topology else set()
    sym_ids = {s.id for s in sym_list}

    validation_errors = validate_association_candidates(
        metadata,
        text_candidate_ids=text_ids,
        region_ids=region_ids,
        topology_edge_ids=edge_ids,
        topology_node_ids=node_ids,
        symbol_candidate_ids=sym_ids,
    )
    if validation_errors:
        raise ValueError(
            "association candidates validation failed: "
            + "; ".join(validation_errors[:8])
        )

    association_json = json_bytes(metadata.to_wire())
    overlay = association_overlay_png(rgb, metadata)
    content_hash = hashlib.sha256(association_json).hexdigest()[:16]

    status_out: StageStatus = "succeeded"
    if (
        warnings
        or review_items
        or any(d.status == "unresolved" for d in dim_candidates)
        or any(a.status == "unresolved" for a in ann_candidates)
        or any(r.interpretation == "unresolved" for r in relationships)
    ):
        status_out = "partial"

    metrics: dict[str, float | int | bool] = {
        "dimension_candidate_count": len(dim_candidates),
        "annotation_candidate_count": len(ann_candidates),
        "relationship_count": len(relationships),
        "review_item_count": len(review_items),
    }

    return AssociateMarkupResult(
        status=status_out,
        metadata=metadata,
        association_candidates_json=association_json,
        overlay_png=overlay,
        warnings=warnings,
        metrics=metrics,
        content_hash=content_hash,
    )
