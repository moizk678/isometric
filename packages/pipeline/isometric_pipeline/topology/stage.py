"""Topology inference stage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

import numpy as np

from isometric_pipeline.centerlines.util import decode_mask_png
from isometric_pipeline.masks.artifact import MasksMetadata
from isometric_pipeline.masks.util import decode_page_rgb
from isometric_pipeline.normalize.page import json_bytes
from isometric_pipeline.primitives.artifact import PrimitivesMetadata
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.artifact import RegionsMetadata
from isometric_pipeline.snapping.artifact import SnappedPrimitivesMetadata
from isometric_pipeline.topology.artifact import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    TopologyMetadata,
)
from isometric_pipeline.topology.build import build_topology
from isometric_pipeline.topology.diagnostics import topology_overlay_png
from isometric_pipeline.topology.segments import segments_from_snapped
from isometric_pipeline.topology.validate import validate_topology

StageStatus = Literal["succeeded", "partial"]


@dataclass(frozen=True)
class InferTopologyResult:
    status: StageStatus
    metadata: TopologyMetadata
    topology_json: bytes
    overlay_png: bytes
    warnings: list[str]
    metrics: dict[str, float | int | bool]
    content_hash: str


def infer_topology(
    page_png: bytes,
    snapped: SnappedPrimitivesMetadata,
    primitives: PrimitivesMetadata,
    *,
    snapped_primitives_json_uri: str,
    primitives_json_uri: str,
    topology_json_uri: str,
    masks: MasksMetadata | None = None,
    masks_json_uri: str | None = None,
    regions: RegionsMetadata | None = None,
    regions_json_uri: str | None = None,
    layer_masks: dict[str, bytes] | None = None,
    profile_version: str = DEFAULT_PIPING_PROFILE_VERSION,
) -> InferTopologyResult:
    profile = load_piping_profile(profile_version)
    topo_profile = profile.topology
    rgb = decode_page_rgb(page_png)
    height, width = rgb.shape[:2]

    ink_mask: np.ndarray | None = None
    if layer_masks:
        geometry_png = layer_masks.get("geometry")
        if geometry_png is not None:
            ink_mask = decode_mask_png(geometry_png, height, width)
        else:
            for png in layer_masks.values():
                ink_mask = decode_mask_png(png, height, width)
                break

    warnings: list[str] = []
    if not layer_masks:
        warnings.append("topology_no_layer_masks")

    segments = segments_from_snapped(snapped, primitives)
    region_list = regions.regions if regions is not None else []
    built = build_topology(segments, topo_profile, ink_mask, region_list)

    metadata = TopologyMetadata(
        schema_version=SCHEMA_VERSION,
        producer_version=PRODUCER_VERSION,
        profile_version=profile_version,
        page_width_px=width,
        page_height_px=height,
        snapped_primitives_metadata_uri=snapped_primitives_json_uri,
        primitives_metadata_uri=primitives_json_uri,
        regions_metadata_uri=regions_json_uri,
        masks_metadata_uri=masks_json_uri,
        nodes=built.nodes,
        edges=built.edges,
        hypotheses=built.hypotheses,
        review_items=built.review_items,
        warnings=warnings,
    )

    validation_errors = validate_topology(metadata)
    if validation_errors:
        raise ValueError(
            "topology validation failed: " + "; ".join(validation_errors[:5])
        )

    topology_json = json_bytes(metadata.to_wire())
    overlay = topology_overlay_png(rgb, metadata)
    content_hash = hashlib.sha256(topology_json).hexdigest()[:16]

    status: StageStatus = "succeeded"
    if built.hypotheses or built.review_items:
        status = "partial"

    metrics: dict[str, float | int | bool] = {
        "node_count": len(metadata.nodes),
        "edge_count": len(metadata.edges),
        "hypothesis_count": len(metadata.hypotheses),
        "review_item_count": len(metadata.review_items),
        "segment_count": len(built.segments),
    }

    return InferTopologyResult(
        status=status,
        metadata=metadata,
        topology_json=topology_json,
        overlay_png=overlay,
        warnings=warnings,
        metrics=metrics,
        content_hash=content_hash,
    )
