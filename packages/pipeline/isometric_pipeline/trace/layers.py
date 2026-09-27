"""Build per-color ink layers for vector tracing."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from isometric_pipeline.centerlines.util import decode_mask_png
from isometric_pipeline.masks.artifact import MasksMetadata


@dataclass(frozen=True)
class TraceInkLayer:
    layer_id: str
    mask: np.ndarray
    stroke_rgb: tuple[int, int, int]


def build_trace_layers(
    *,
    geometry_ink_png: bytes,
    masks_metadata: MasksMetadata,
    color_layer_masks: dict[str, bytes],
    black_ink_png: bytes,
    unclassified_ink_png: bytes,
    include_unclassified: bool,
) -> tuple[list[TraceInkLayer], np.ndarray]:
    height = masks_metadata.page_height_px
    width = masks_metadata.page_width_px
    geometry = decode_mask_png(geometry_ink_png, height, width)
    geometry_bin = geometry > 0

    layers: list[TraceInkLayer] = []
    consumed = np.zeros((height, width), dtype=bool)

    for record in masks_metadata.color_layers:
        raw = color_layer_masks.get(record.layer_id)
        if raw is None:
            continue
        layer_mask = decode_mask_png(raw, height, width)
        ink = (layer_mask > 0) & geometry_bin
        if not np.any(ink):
            continue
        out = np.zeros((height, width), dtype=np.uint8)
        out[ink] = 255
        layers.append(
            TraceInkLayer(
                layer_id=record.layer_id,
                mask=out,
                stroke_rgb=record.normalized_rgb,
            )
        )
        consumed |= ink

    black = decode_mask_png(black_ink_png, height, width)
    black_ink = (black > 0) & geometry_bin & ~consumed
    if np.any(black_ink):
        out = np.zeros((height, width), dtype=np.uint8)
        out[black_ink] = 255
        layers.append(TraceInkLayer(layer_id="black", mask=out, stroke_rgb=(0, 0, 0)))
        consumed |= black_ink

    if include_unclassified:
        unclassified = decode_mask_png(unclassified_ink_png, height, width)
        rest = (unclassified > 0) & geometry_bin & ~consumed
        if np.any(rest):
            out = np.zeros((height, width), dtype=np.uint8)
            out[rest] = 255
            layers.append(
                TraceInkLayer(layer_id="unclassified", mask=out, stroke_rgb=(40, 40, 40))
            )
            consumed |= rest

    leftover = geometry_bin & ~consumed
    if np.any(leftover):
        out = np.zeros((height, width), dtype=np.uint8)
        out[leftover] = 255
        layers.append(
            TraceInkLayer(layer_id="geometry", mask=out, stroke_rgb=(0, 0, 0))
        )

    return layers, geometry
