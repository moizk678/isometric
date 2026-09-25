"""Tests for extract_centerlines and fit_primitives stages."""

from __future__ import annotations

import io
import math
import unittest
import uuid
from pathlib import Path

import cv2
import numpy as np
from isometric_pipeline.centerlines.stage import extract_centerlines
from isometric_pipeline.masks.artifact import (
    GridDiagnostics,
    MaskArtifactRef,
    MasksMetadata,
)
from isometric_pipeline.masks.stage import separate_masks
from isometric_pipeline.masks.util import encode_mask_png
from isometric_pipeline.primitives.stage import fit_primitives
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.stage import detect_regions
from PIL import Image

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "centerlines-and-primitives"
MASK_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "masks-and-regions"
DOC_ID = "00000000-0000-4000-8000-000000000100"


def _ensure_fixtures() -> None:
    if not (FIXTURES / "horizontal-stroke.png").is_file():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "centerlines_generate", FIXTURES / "generate.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.generate_all()


def _decode_mask(png: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(png)) as image:
        return np.array(image.convert("L"))


def _page_from_mask(mask: np.ndarray) -> bytes:
    rgb = np.full((mask.shape[0], mask.shape[1], 3), 255, dtype=np.uint8)
    rgb[mask > 0] = (20, 20, 20)
    buf = io.BytesIO()
    Image.fromarray(rgb, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


def _masks_metadata(doc: str, width: int, height: int) -> MasksMetadata:
    prefix = f"documents/{doc}/masks"
    return MasksMetadata(
        page_width_px=width,
        page_height_px=height,
        page_hash="test",
        grid_mask=MaskArtifactRef(
            uri=f"{prefix}/grid.png", width_px=width, height_px=height
        ),
        retained_ink_mask=MaskArtifactRef(
            uri=f"{prefix}/retained-ink.png", width_px=width, height_px=height
        ),
        black_ink_mask=MaskArtifactRef(
            uri=f"{prefix}/black-ink.png", width_px=width, height_px=height
        ),
        unclassified_ink_mask=MaskArtifactRef(
            uri=f"{prefix}/unclassified-ink.png", width_px=width, height_px=height
        ),
        geometry_ink_mask=MaskArtifactRef(
            uri=f"{prefix}/geometry-ink.png", width_px=width, height_px=height
        ),
        protection_mask=MaskArtifactRef(
            uri=f"{prefix}/protection.png", width_px=width, height_px=height
        ),
        color_layers=[],
        diagnostics=GridDiagnostics(
            grid_confidence=0.0,
            paper_lightness=250.0,
            grid_pixel_count=0,
            retained_ink_pixel_count=0,
        ),
        parameters={},
        warnings=[],
    )


def _run_geometry_pipeline(mask_name: str):
    mask = _decode_mask((FIXTURES / mask_name).read_bytes())
    page = _page_from_mask(mask)
    doc = str(uuid.UUID(DOC_ID))
    h, w = mask.shape
    geometry_png = encode_mask_png(mask)
    meta = _masks_metadata(doc, w, h)
    extracted = extract_centerlines(
        page,
        geometry_png,
        {},
        meta,
        None,
        document_id=doc,
        masks_json_uri=f"documents/{doc}/masks.json",
        regions_json_uri=None,
        centerlines_json_uri=f"documents/{doc}/centerlines.json",
    )
    fitted = fit_primitives(
        page,
        extracted.metadata,
        {"geometry": geometry_png},
        centerlines_json_uri=f"documents/{doc}/centerlines.json",
        masks_json_uri=f"documents/{doc}/masks.json",
        regions_json_uri=None,
        primitives_json_uri=f"documents/{doc}/primitives.json",
    )
    return extracted, fitted


class CenterlinesAndPrimitivesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _ensure_fixtures()

    def test_geometry_layer_excludes_color_pixels(self) -> None:
        from isometric_pipeline.masks.artifact import ColorLayerRecord

        h, w = 120, 120
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.line(mask, (10, 60), (110, 60), 255, 5)
        color = np.zeros((h, w), dtype=np.uint8)
        cv2.line(color, (10, 60), (110, 60), 255, 5)
        page = _page_from_mask(mask)
        doc = str(uuid.UUID(DOC_ID))
        geometry_png = encode_mask_png(mask)
        color_png = encode_mask_png(color)
        meta = _masks_metadata(doc, w, h).model_copy(
            update={
                "color_layers": [
                    ColorLayerRecord(
                        layer_id="layer_red",
                        mask_uri=f"documents/{doc}/masks/color/layer_red.png",
                        normalized_rgb=(255, 0, 0),
                        pixel_count=int(np.count_nonzero(color)),
                    )
                ]
            }
        )
        extracted = extract_centerlines(
            page,
            geometry_png,
            {"layer_red": color_png},
            meta,
            None,
            document_id=doc,
            masks_json_uri=f"documents/{doc}/masks.json",
            regions_json_uri=None,
            centerlines_json_uri=f"documents/{doc}/centerlines.json",
        )
        geometry_layer = next(
            layer for layer in extracted.metadata.layers if layer.layer_id == "geometry"
        )
        color_layer = next(
            layer
            for layer in extracted.metadata.layers
            if layer.layer_id == "layer_red"
        )
        self.assertGreater(color_layer.edge_count, 0)
        self.assertEqual(geometry_layer.edge_count, 0)

    def test_profile_loads_from_yaml(self) -> None:
        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
        self.assertEqual(profile.version, DEFAULT_PIPING_PROFILE_VERSION)
        self.assertGreater(profile.geometry.min_component_pixels, 0)

    def test_horizontal_stroke_fits_line(self) -> None:
        extracted, fitted = _run_geometry_pipeline("horizontal-stroke.png")
        self.assertGreater(len(extracted.metadata.edges), 0)
        accepted = [p for p in fitted.metadata.primitives if p.status == "accepted"]
        self.assertEqual(len(accepted), 1)
        prim = accepted[0]
        angle = abs(
            math.degrees(
                math.atan2(prim.end.y - prim.start.y, prim.end.x - prim.start.x)
            )
        )
        self.assertLess(angle, 5.0)
        self.assertLess(prim.residual_rms_px, 3.0)

    def test_sloped_stroke_accepted(self) -> None:
        _, fitted = _run_geometry_pipeline("sloped-stroke.png")
        accepted = [p for p in fitted.metadata.primitives if p.status == "accepted"]
        self.assertGreaterEqual(len(accepted), 1)

    def test_thick_stroke_produces_centerline(self) -> None:
        extracted, _ = _run_geometry_pipeline("thick-stroke.png")
        self.assertGreater(len(extracted.metadata.components), 0)
        self.assertGreater(len(extracted.metadata.edges), 0)

    def test_broken_stroke_does_not_merge(self) -> None:
        extracted, fitted = _run_geometry_pipeline("broken-stroke.png")
        self.assertGreaterEqual(len(extracted.metadata.components), 2)
        accepted = [p for p in fitted.metadata.primitives if p.status == "accepted"]
        self.assertGreaterEqual(len(accepted), 2)

    def test_noisy_stroke_bounded_residual(self) -> None:
        _, fitted = _run_geometry_pipeline("noisy-stroke.png")
        accepted = [p for p in fitted.metadata.primitives if p.status == "accepted"]
        self.assertGreaterEqual(len(accepted), 1)
        self.assertLess(accepted[0].residual_rms_px, 4.0)

    def test_bent_stroke_splits_into_legs(self) -> None:
        _, fitted = _run_geometry_pipeline("bent-stroke.png")
        accepted = [p for p in fitted.metadata.primitives if p.status == "accepted"]
        self.assertGreaterEqual(len(accepted), 2)
        lengths = sorted(
            float(math.hypot(p.end.x - p.start.x, p.end.y - p.start.y))
            for p in accepted
        )
        self.assertLess(max(lengths), 220.0)

    def test_rejected_components_listed(self) -> None:
        mask = np.zeros((80, 80), dtype=np.uint8)
        cv2.rectangle(mask, (39, 39), (42, 42), 255, -1)
        page = _page_from_mask(mask)
        doc = str(uuid.UUID(DOC_ID))
        geometry_png = encode_mask_png(mask)
        meta = _masks_metadata(doc, 80, 80)
        extracted = extract_centerlines(
            page,
            geometry_png,
            {},
            meta,
            None,
            document_id=doc,
            masks_json_uri=f"documents/{doc}/masks.json",
            regions_json_uri=None,
            centerlines_json_uri=f"documents/{doc}/centerlines.json",
        )
        self.assertGreaterEqual(len(extracted.metadata.rejected_components), 1)

    def test_full_chain_text_blocks_avoids_protected_primitives(self) -> None:
        page = (MASK_FIXTURES / "text-blocks.png").read_bytes()
        doc = str(uuid.UUID(DOC_ID))
        masks = separate_masks(
            page,
            document_id=doc,
            page_uri=f"documents/{doc}/page.png",
            masks_json_uri=f"documents/{doc}/masks.json",
        )
        regions = detect_regions(
            page,
            masks.metadata,
            masks.masks["retained_ink"],
            masks.masks["black_ink"],
            document_id=doc,
            masks_json_uri=f"documents/{doc}/masks.json",
        )
        extracted = extract_centerlines(
            page,
            regions.geometry_ink_png,
            masks.color_layer_masks,
            regions.updated_masks_metadata,
            regions.regions_metadata,
            document_id=doc,
            masks_json_uri=f"documents/{doc}/masks.json",
            regions_json_uri=f"documents/{doc}/regions.json",
            centerlines_json_uri=f"documents/{doc}/centerlines.json",
        )
        fitted = fit_primitives(
            page,
            extracted.metadata,
            {"geometry": regions.geometry_ink_png},
            centerlines_json_uri=f"documents/{doc}/centerlines.json",
            masks_json_uri=f"documents/{doc}/masks.json",
            regions_json_uri=f"documents/{doc}/regions.json",
            primitives_json_uri=f"documents/{doc}/primitives.json",
        )
        protection = _decode_mask(regions.protection_png)
        for prim in fitted.metadata.primitives:
            if prim.status != "accepted":
                continue
            mx = (prim.start.x + prim.end.x) / 2.0
            my = (prim.start.y + prim.end.y) / 2.0
            ix, iy = int(mx), int(my)
            if 0 <= iy < protection.shape[0] and 0 <= ix < protection.shape[1]:
                self.assertEqual(int(protection[iy, ix]), 0)


if __name__ == "__main__":
    unittest.main()
