"""Tests for separate_masks and detect_regions stages."""

from __future__ import annotations

import io
import unittest
import uuid
from pathlib import Path

import numpy as np
from isometric_pipeline.masks.artifact import WARNING_GRID_LOW_CONFIDENCE
from isometric_pipeline.masks.stage import separate_masks
from isometric_pipeline.masks.util import decode_page_rgb
from isometric_pipeline.regions.stage import detect_regions
from PIL import Image

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "masks-and-regions"
DOC_ID = "00000000-0000-4000-8000-000000000099"


def _ensure_fixtures() -> None:
    if not (FIXTURES / "faint-grid.png").is_file():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "masks_generate", FIXTURES / "generate.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.generate_all()


def _decode_mask(png: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(png)) as image:
        return np.array(image.convert("L"))


def _run_separate(name: str):
    data = (FIXTURES / name).read_bytes()
    doc = str(uuid.UUID(DOC_ID))
    return separate_masks(
        data,
        document_id=doc,
        page_uri=f"documents/{doc}/page.png",
        masks_json_uri=f"documents/{doc}/masks.json",
    )


class MasksAndRegionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _ensure_fixtures()

    def test_mask_dimensions_match_page(self) -> None:
        page = (FIXTURES / "faint-grid.png").read_bytes()
        rgb = decode_page_rgb(page)
        h, w = rgb.shape[:2]
        result = _run_separate("faint-grid.png")
        for key in result.masks:
            mask = _decode_mask(result.masks[key])
            self.assertEqual(mask.shape, (h, w))

    def test_faint_grid_suppresses_grid_not_routes(self) -> None:
        result = _run_separate("faint-grid.png")
        grid = _decode_mask(result.masks["grid"])
        retained = _decode_mask(result.masks["retained_ink"])
        route_overlap = np.count_nonzero(grid & retained)
        self.assertGreater(int(np.count_nonzero(grid)), 50)
        self.assertLess(route_overlap, 30)

    def test_dark_grid_low_confidence_fallback(self) -> None:
        result = _run_separate("dark-grid.png")
        self.assertIn(WARNING_GRID_LOW_CONFIDENCE, result.warnings)
        grid = _decode_mask(result.masks["grid"])
        retained = _decode_mask(result.masks["retained_ink"])
        self.assertLess(int(np.count_nonzero(grid)), 20)
        self.assertGreater(int(np.count_nonzero(retained)), 100)

    def test_colored_routes_produce_layers(self) -> None:
        result = _run_separate("colored-routes.png")
        self.assertGreaterEqual(len(result.metadata.color_layers), 2)
        black = _decode_mask(result.masks["black_ink"])
        self.assertGreater(int(np.count_nonzero(black)), 10)

    def test_colored_routes_color_layers_are_deterministic(self) -> None:
        first = _run_separate("colored-routes.png")
        second = _run_separate("colored-routes.png")
        self.assertEqual(first.color_layer_masks, second.color_layer_masks)
        self.assertEqual(
            [layer.layer_id for layer in first.metadata.color_layers],
            [layer.layer_id for layer in second.metadata.color_layers],
        )

    def test_detect_regions_protection_disjoint_from_geometry(self) -> None:
        page = (FIXTURES / "text-blocks.png").read_bytes()
        doc = str(uuid.UUID(DOC_ID))
        masks = _run_separate("text-blocks.png")
        regions = detect_regions(
            page,
            masks.metadata,
            masks.masks["retained_ink"],
            masks.masks["black_ink"],
            document_id=doc,
            masks_json_uri=f"documents/{doc}/masks.json",
        )
        protection = _decode_mask(regions.protection_png)
        geometry = _decode_mask(regions.geometry_ink_png)
        overlap = np.count_nonzero(protection & geometry)
        self.assertLessEqual(overlap, 4)
        self.assertGreater(len(regions.regions_metadata.regions), 0)
        for region in regions.regions_metadata.regions:
            self.assertIn(region.id, regions.crop_pngs)

    def test_pipeline_chain(self) -> None:
        page = (FIXTURES / "colored-routes.png").read_bytes()
        doc = str(uuid.UUID(DOC_ID))
        masks = _run_separate("colored-routes.png")
        regions = detect_regions(
            page,
            masks.metadata,
            masks.masks["retained_ink"],
            masks.masks["black_ink"],
            document_id=doc,
            masks_json_uri=f"documents/{doc}/masks.json",
        )
        self.assertTrue(regions.regions_json.startswith(b"{"))
        self.assertTrue(regions.overlay_png.startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
