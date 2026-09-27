"""Tests for trace SVG export."""

from __future__ import annotations

import numpy as np

from isometric_pipeline.masks.stage import separate_masks
from isometric_pipeline.profiles.loader import DEFAULT_PIPING_PROFILE_VERSION, load_piping_profile
from isometric_pipeline.regions.stage import detect_regions
from isometric_pipeline.trace import trace_ink, validate_trace_svg


def _synthetic_page(width: int, height: int) -> bytes:
    from isometric_pipeline.masks.util import encode_mask_png

    rgb = np.full((height, width, 3), 245, dtype=np.uint8)
    rgb[40:42, 20:180] = (0, 0, 200)
    rgb[20:160, 100:102] = (0, 0, 200)
    from PIL import Image
    import io

    buf = io.BytesIO()
    Image.fromarray(rgb, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


def test_trace_svg_from_cross_ink() -> None:
    doc = "trace-test-doc"
    page = _synthetic_page(200, 200)
    separated = separate_masks(
        page,
        document_id=doc,
        page_uri=f"documents/{doc}/page.png",
        masks_json_uri=f"documents/{doc}/masks.json",
    )
    regions = detect_regions(
        page,
        separated.metadata,
        separated.masks["retained_ink"],
        separated.masks["black_ink"],
        document_id=doc,
        masks_json_uri=f"documents/{doc}/masks.json",
    )
    profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
    result = trace_ink(
        geometry_ink_png=regions.geometry_ink_png,
        masks_metadata=regions.updated_masks_metadata,
        color_layer_masks=separated.color_layer_masks,
        black_ink_png=separated.masks["black_ink"],
        unclassified_ink_png=separated.masks["unclassified_ink"],
        profile=profile,
    )
    assert result.svg.startswith(b"<?xml")
    assert b"trace-layer-" in result.svg
    assert result.metrics["trace_paths"] >= 2
    validate_trace_svg(
        result.svg,
        width_px=regions.updated_masks_metadata.page_width_px,
        height_px=regions.updated_masks_metadata.page_height_px,
    )
