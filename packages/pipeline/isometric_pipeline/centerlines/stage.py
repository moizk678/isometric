"""Centerline extraction stage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

import numpy as np

from isometric_pipeline.centerlines.artifact import (
    PRODUCER_VERSION,
    SCHEMA_VERSION,
    CenterlineLayerRecord,
    CenterlinesMetadata,
)
from isometric_pipeline.centerlines.diagnostics import centerlines_overlay_png
from isometric_pipeline.centerlines.graph import extract_layer_graph
from isometric_pipeline.centerlines.skeleton import clean_mask, prune_spurs, skeletonize
from isometric_pipeline.centerlines.util import (
    apply_protection_mask,
    crop_from_bbox,
    decode_mask_png,
)
from isometric_pipeline.masks.artifact import MasksMetadata
from isometric_pipeline.masks.util import decode_page_rgb
from isometric_pipeline.normalize.page import json_bytes
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.artifact import RegionsMetadata

StageStatus = Literal["succeeded", "partial"]
GEOMETRY_LAYER_ID = "geometry"


@dataclass(frozen=True)
class ExtractCenterlinesResult:
    status: StageStatus
    metadata: CenterlinesMetadata
    centerlines_json: bytes
    crop_pngs: dict[str, bytes]
    overlay_png: bytes
    warnings: list[str]
    metrics: dict[str, float | int | bool]
    content_hash: str


def extract_centerlines(
    page_png: bytes,
    geometry_ink_png: bytes,
    color_layer_masks: dict[str, bytes],
    masks_metadata: MasksMetadata,
    regions_metadata: RegionsMetadata | None,
    *,
    document_id: str,
    masks_json_uri: str,
    regions_json_uri: str | None,
    centerlines_json_uri: str,
    protection_png: bytes | None = None,
    profile_version: str = DEFAULT_PIPING_PROFILE_VERSION,
) -> ExtractCenterlinesResult:
    profile = load_piping_profile(profile_version)
    geo = profile.geometry
    rgb = decode_page_rgb(page_png)
    height, width = rgb.shape[:2]
    # Region boxes can cover the page. Subtract only protection-component pixels.
    protection = (
        decode_mask_png(protection_png, height, width)
        if protection_png is not None
        else None
    )
    geometry_mask = decode_mask_png(geometry_ink_png, height, width)
    geometry_mask = apply_protection_mask(geometry_mask, protection)

    color_union = np.zeros((height, width), dtype=np.uint8)
    layer_masks: list[tuple[str, str, np.ndarray]] = []
    for layer in masks_metadata.color_layers:
        if layer.layer_id not in color_layer_masks:
            continue
        layer_mask = decode_mask_png(color_layer_masks[layer.layer_id], height, width)
        layer_mask = apply_protection_mask(layer_mask, protection)
        color_union = np.maximum(color_union, layer_mask)
        layer_masks.append((layer.layer_id, layer.mask_uri, layer_mask))

    geometry_only = geometry_mask.copy()
    geometry_only[color_union > 0] = 0
    layer_masks.insert(
        0,
        (
            GEOMETRY_LAYER_ID,
            masks_metadata.geometry_ink_mask.uri,
            geometry_only,
        ),
    )

    components: list = []
    rejected: list = []
    nodes: list = []
    edges: list = []
    layer_records: list[CenterlineLayerRecord] = []
    crop_pngs: dict[str, bytes] = {}
    warnings: list[str] = []

    overlay_mask = np.zeros((height, width), dtype=np.uint8)
    overlay_skel = np.zeros((height, width), dtype=np.uint8)

    crops_prefix = f"documents/{document_id}/crops"
    for layer_id, mask_uri, raw_mask in layer_masks:
        if not np.any(raw_mask):
            layer_records.append(
                CenterlineLayerRecord(
                    layer_id=layer_id,
                    mask_uri=mask_uri,
                    component_count=0,
                    edge_count=0,
                )
            )
            continue
        cleaned = clean_mask(raw_mask, geo)
        skel = skeletonize(cleaned)
        skel = prune_spurs(skel, geo.max_spur_length_px)
        for _ in range(geo.skeleton_prune_iterations):
            skel = prune_spurs(skel, 1)
        overlay_mask = np.maximum(overlay_mask, cleaned)
        overlay_skel = np.maximum(overlay_skel, skel)

        graph = extract_layer_graph(
            cleaned,
            skel,
            layer_id=layer_id,
            profile=geo,
            crops_prefix=crops_prefix,
            id_prefix=layer_id.replace("/", "_"),
        )
        components.extend(graph.components)
        rejected.extend(graph.rejected)
        nodes.extend(graph.nodes)
        edges.extend(graph.edges)
        layer_records.append(
            CenterlineLayerRecord(
                layer_id=layer_id,
                mask_uri=mask_uri,
                component_count=len(graph.components),
                edge_count=len(graph.edges),
            )
        )
        for item in list(graph.components) + list(graph.rejected):
            crop_pngs[item.id] = crop_from_bbox(rgb, item.bbox)

    metadata = CenterlinesMetadata(
        schema_version=SCHEMA_VERSION,
        producer_version=PRODUCER_VERSION,
        profile_version=profile_version,
        page_width_px=width,
        page_height_px=height,
        masks_metadata_uri=masks_json_uri,
        regions_metadata_uri=regions_json_uri,
        layers=layer_records,
        components=components,
        rejected_components=rejected,
        nodes=nodes,
        edges=edges,
        warnings=warnings,
    )
    centerlines_json = json_bytes(metadata.to_wire())
    overlay_png = centerlines_overlay_png(rgb, overlay_mask, overlay_skel, nodes, edges)
    content_hash = hashlib.sha256(centerlines_json + overlay_png).hexdigest()

    metrics = {
        "component_count": len(components),
        "rejected_component_count": len(rejected),
        "edge_count": len(edges),
        "node_count": len(nodes),
    }
    status: StageStatus = "partial" if warnings else "succeeded"
    return ExtractCenterlinesResult(
        status=status,
        metadata=metadata,
        centerlines_json=centerlines_json,
        crop_pngs=crop_pngs,
        overlay_png=overlay_png,
        warnings=warnings,
        metrics=metrics,
        content_hash=content_hash,
    )
