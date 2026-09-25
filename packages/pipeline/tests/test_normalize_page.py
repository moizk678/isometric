"""Tests for the normalize_page stage."""

from __future__ import annotations

import io
import unittest
from pathlib import Path

import cv2
import numpy as np
from isometric_pipeline.geometry.transforms import (
    ROUND_TRIP_TOLERANCE_PX,
    round_trip_within_tolerance,
)
from isometric_pipeline.ingest.exif_frame import read_source_frame
from isometric_pipeline.normalize.artifact import WARNING_PAGE_BOUNDARY_LOW
from isometric_pipeline.normalize.page import (
    NormalizeLimits,
    NormalizePageError,
    normalize_page,
)
from PIL import ExifTags, Image, ImageOps

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "page-normalization"


def encode_jpeg(size: tuple[int, int], orientation: int | None = None) -> bytes:
    image = Image.new("RGB", size, color="white")
    buf = io.BytesIO()
    if orientation is None:
        image.save(buf, format="JPEG")
    else:
        exif = Image.Exif()
        exif[ExifTags.Base.Orientation] = orientation
        image.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


class NormalizePageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (FIXTURES / "flat-scan.png").is_file():
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "page_normalization_generate", FIXTURES / "generate.py"
            )
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.generate_all()

    def test_corrupt_bytes_fail_deterministically(self) -> None:
        with self.assertRaises(NormalizePageError) as ctx:
            normalize_page(b"not-an-image")
        self.assertEqual(ctx.exception.code, "unsupported_media_type")

    def test_truncated_png_fails(self) -> None:
        png = FIXTURES / "flat-scan.png"
        data = png.read_bytes()[:40]
        with self.assertRaises(NormalizePageError) as ctx:
            normalize_page(data)
        self.assertEqual(ctx.exception.code, "invalid_image")

    def test_byte_limit(self) -> None:
        data = (FIXTURES / "flat-scan.png").read_bytes()
        with self.assertRaises(NormalizePageError) as ctx:
            normalize_page(data, limits=NormalizeLimits(max_bytes=10))
        self.assertEqual(ctx.exception.code, "payload_too_large")

    def test_no_boundary_emits_warning_and_preserves_content(self) -> None:
        data = (FIXTURES / "no-boundary.png").read_bytes()
        result = normalize_page(data)
        self.assertEqual(result.status, "partial")
        self.assertIn(WARNING_PAGE_BOUNDARY_LOW, result.warnings)
        self.assertFalse(result.metadata.diagnostics.rectified)
        with Image.open(io.BytesIO(result.display_png)) as display:
            with Image.open(io.BytesIO(data)) as source:
                displayed = ImageOps.exif_transpose(source)
                assert displayed is not None
                self.assertEqual(display.size, displayed.size)

    def test_exif_jpeg_orientations(self) -> None:
        for orientation in range(1, 9):
            with self.subTest(orientation=orientation):
                data = encode_jpeg((50, 30), orientation=orientation)
                frame = read_source_frame(data)
                result = normalize_page(data)
                self.assertEqual(
                    (
                        result.metadata.display_width_px,
                        result.metadata.display_height_px,
                    ),
                    (frame.display_width_px, frame.display_height_px),
                )
                self.assertEqual(result.metadata.orientation, orientation)

    def test_skewed_page_rectifies_with_round_trip(self) -> None:
        data = (FIXTURES / "skewed-page.png").read_bytes()
        result = normalize_page(data)
        self.assertTrue(result.metadata.diagnostics.rectified)
        self.assertGreater(result.metadata.diagnostics.boundary_confidence, 0.2)
        meta = result.metadata
        self.assertEqual(len(meta.display_to_page), 9)
        self.assertEqual(len(meta.page_to_display), 9)
        probes = [(12.0, 18.0), (200.0, 150.0), (380.0, 280.0)]
        for x, y in probes:
            with self.subTest(x=x, y=y):
                self.assertTrue(
                    round_trip_within_tolerance(
                        meta.source_to_display,
                        meta.display_to_source,
                        x,
                        y,
                        tolerance_px=ROUND_TRIP_TOLERANCE_PX,
                    )
                )
                self.assertTrue(
                    round_trip_within_tolerance(
                        meta.source_to_page,
                        meta.page_to_source,
                        x,
                        y,
                        tolerance_px=ROUND_TRIP_TOLERANCE_PX,
                    )
                )

    def test_flat_scan_fallback_without_cropping(self) -> None:
        data = (FIXTURES / "flat-scan.png").read_bytes()
        result = normalize_page(data)
        self.assertIn(result.status, ("partial", "succeeded"))
        with Image.open(io.BytesIO(result.page_png)) as page:
            with Image.open(io.BytesIO(result.display_png)) as display:
                if result.metadata.diagnostics.rectified:
                    self.assertGreater(page.size[0], display.size[0] // 2)
                    self.assertGreater(page.size[1], display.size[1] // 2)
                else:
                    self.assertEqual(page.size, display.size)

    def test_display_png_matches_exif_transpose(self) -> None:
        data = (FIXTURES / "exif-orientation-6.jpg").read_bytes()
        result = normalize_page(data)
        with Image.open(io.BytesIO(result.display_png)) as display:
            with Image.open(io.BytesIO(data)) as source:
                expected = ImageOps.exif_transpose(source)
                assert expected is not None
                self.assertEqual(display.size, expected.size)

    def test_overlay_png_is_valid(self) -> None:
        data = (FIXTURES / "skewed-page.png").read_bytes()
        result = normalize_page(data)
        self.assertTrue(result.overlay_png.startswith(b"\x89PNG"))
        overlay = cv2.imdecode(
            np.frombuffer(result.overlay_png, dtype=np.uint8), cv2.IMREAD_COLOR
        )
        self.assertIsNotNone(overlay)


if __name__ == "__main__":
    unittest.main()
