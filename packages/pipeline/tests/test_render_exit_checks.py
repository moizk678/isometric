"""Run 02 exit checks over every valid scene fixture."""

from __future__ import annotations

import hashlib
import io
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

import isometric_pipeline.render.svg as svg_module
from isometric_pipeline.render import (
    STYLE_PROFILE_VERSION,
    SYMBOL_LIBRARY_VERSION,
    RenderError,
    RenderIssueCode,
    get_style_profile,
    load_symbol_library,
    rasterize_preview,
    render_svg,
    validate_svg,
)
from isometric_pipeline.render.allowlist import (
    ALLOWED_ELEMENTS,
    PREVIEW_ONLY_GROUP_IDS,
    SVG_NAMESPACE,
)
from isometric_pipeline.render.golden import GOLDEN_DIR, png_difference
from isometric_pipeline.scene import DrawingScene, load_scene
from PIL import Image
from render_fixtures import (
    RENDER_FIXTURE_EXPECTATIONS,
    VALID_DIR,
    assert_expectations_cover_valid_fixtures,
    valid_fixture_stems,
)

NS = f"{{{SVG_NAMESPACE}}}"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
WHITE = (255, 255, 255)

# Both crossings draw 2 px pipe strokes straight through the sample point, so
# that pixel is ink in either fixture. The diagonal neighbours of the sample
# pixel lie off both strokes and fully inside the radius-3 connection dot.
DOT_ONLY_OFFSETS = ((-2, -2), (1, -2), (-2, 1), (1, 1))

LIBRARY = load_symbol_library(SYMBOL_LIBRARY_VERSION)
STYLE = get_style_profile(STYLE_PROFILE_VERSION)


def load_fixture(stem: str) -> DrawingScene:
    text = (VALID_DIR / f"{stem}.json").read_text(encoding="utf-8")
    return load_scene(text, catalog=LIBRARY)


def render(scene: DrawingScene) -> bytes:
    return render_svg(scene, SYMBOL_LIBRARY_VERSION, STYLE_PROFILE_VERSION).svg


def local(tag: str) -> str:
    return tag.removeprefix(NS)


def live_object_ids(scene: DrawingScene) -> list[str]:
    return sorted(
        obj.id for obj in scene.objects if obj.interpretation.state != "rejected"
    )


def preview_image(svg: bytes) -> Image.Image:
    with Image.open(io.BytesIO(rasterize_preview(svg).png)) as image:
        return image.convert("RGB")


class ExitCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assert_expectations_cover_valid_fixtures()
        cls.stems = valid_fixture_stems()
        cls.scenes = {stem: load_fixture(stem) for stem in cls.stems}
        cls.svgs = {stem: render(scene) for stem, scene in cls.scenes.items()}

    def test_every_fixture_renders_validates_and_rasterizes(self) -> None:
        self.assertTrue(self.stems)
        for stem in self.stems:
            with self.subTest(fixture=stem):
                scene, svg = self.scenes[stem], self.svgs[stem]
                validate_svg(svg, scene, STYLE)
                self.assertEqual(local(ET.fromstring(svg).tag), "svg")
                preview = rasterize_preview(svg, scale=1.0)
                self.assertTrue(preview.png.startswith(PNG_SIGNATURE))
                with Image.open(io.BytesIO(preview.png)) as image:
                    self.assertEqual(
                        image.size, (scene.page.width_px, scene.page.height_px)
                    )

    def test_disconnected_crossing_looks_disconnected(self) -> None:
        for stem, expectation in sorted(RENDER_FIXTURE_EXPECTATIONS.items()):
            if expectation.sample_point is None:
                continue
            with self.subTest(fixture=stem):
                image = preview_image(self.svgs[stem])
                x, y = (int(v) for v in expectation.sample_point)
                self.assertNotEqual(image.getpixel((x, y)), WHITE)
                for dx, dy in DOT_ONLY_OFFSETS:
                    pixel = image.getpixel((x + dx, y + dy))
                    if expectation.expect_ink_at_sample:
                        self.assertNotEqual(pixel, WHITE, (x + dx, y + dy))
                    else:
                        self.assertEqual(pixel, WHITE, (x + dx, y + dy))

    def test_crossing_fixtures_have_opposite_expectations(self) -> None:
        connected = RENDER_FIXTURE_EXPECTATIONS["crossing-connected"]
        unconnected = RENDER_FIXTURE_EXPECTATIONS["crossing-unconnected"]
        self.assertIs(connected.expect_ink_at_sample, True)
        self.assertIs(unconnected.expect_ink_at_sample, False)
        self.assertEqual(connected.sample_point, unconnected.sample_point)

    def test_renders_are_deterministic_and_match_golden_svg(self) -> None:
        for stem in self.stems:
            with self.subTest(fixture=stem):
                first = render_svg(
                    self.scenes[stem], SYMBOL_LIBRARY_VERSION, STYLE_PROFILE_VERSION
                )
                second = render_svg(
                    load_fixture(stem), SYMBOL_LIBRARY_VERSION, STYLE_PROFILE_VERSION
                )
                self.assertEqual(first.sha256, second.sha256)
                self.assertEqual(first.sha256, hashlib.sha256(first.svg).hexdigest())
                golden = (GOLDEN_DIR / f"{stem}.svg").read_bytes()
                self.assertEqual(first.svg, golden)

    def test_preview_matches_golden_png_within_tolerance(self) -> None:
        for stem in self.stems:
            with self.subTest(fixture=stem):
                png = rasterize_preview(self.svgs[stem], scale=1.0).png
                golden = (GOLDEN_DIR / f"{stem}.png").read_bytes()
                self.assertIsNone(png_difference(golden, png))

    def test_text_metacharacters_are_escaped_and_round_trip(self) -> None:
        stem = "text-metacharacters"
        svg = self.svgs[stem]
        root = ET.fromstring(svg)
        tags = {local(element.tag) for element in root.iter()}
        self.assertLessEqual(tags, ALLOWED_ELEMENTS)
        self.assertNotIn(b"<script", svg)
        values: list[str] = []
        for element in root.iter():
            if element.text:
                values.append(element.text)
            values.extend(element.attrib.values())
        texts = RENDER_FIXTURE_EXPECTATIONS[stem].round_trip_texts
        self.assertTrue(texts)
        for text in texts:
            self.assertIn(text, values)
        text_elements = [e for e in root.iter() if local(e.tag) == "text"]
        self.assertTrue(text_elements)
        for element in text_elements:
            self.assertEqual(list(element), [])

    def test_each_object_is_separately_addressable(self) -> None:
        for stem in self.stems:
            with self.subTest(fixture=stem):
                root = ET.fromstring(self.svgs[stem])
                found = sorted(
                    element.get("data-object-id")
                    for element in root.iter()
                    if element.get("data-object-id") is not None
                )
                self.assertEqual(found, live_object_ids(self.scenes[stem]))
                markers = [e for e in root.iter() if local(e.tag) == "marker"]
                marker_paths = sum(
                    1 for m in markers for e in m.iter() if local(e.tag) == "path"
                )
                all_paths = sum(1 for e in root.iter() if local(e.tag) == "path")
                self.assertEqual(all_paths, marker_paths)

    def test_use_counts_match_expectations(self) -> None:
        self.assertEqual(
            RENDER_FIXTURE_EXPECTATIONS["structural-junctions"].expected_use_count, 0
        )
        self.assertEqual(
            RENDER_FIXTURE_EXPECTATIONS["explicit-tee-fitting"].expected_use_count, 1
        )
        for stem in self.stems:
            with self.subTest(fixture=stem):
                root = ET.fromstring(self.svgs[stem])
                uses = [e for e in root.iter() if local(e.tag) == "use"]
                self.assertEqual(
                    len(uses), RENDER_FIXTURE_EXPECTATIONS[stem].expected_use_count
                )

    def test_export_has_no_preview_only_groups(self) -> None:
        for stem in self.stems:
            with self.subTest(fixture=stem):
                for group_id in PREVIEW_ONLY_GROUP_IDS:
                    self.assertNotIn(group_id.encode(), self.svgs[stem])

    def test_render_raises_instead_of_returning_invalid_svg(self) -> None:
        forged = '<line x1="0" y1="0" x2="1" y2="1" transform="matrix(1 0 0 1 0 0)"/>'
        with mock.patch.object(svg_module, "_callouts", return_value=[forged]):
            with self.assertRaises(RenderError) as ctx:
                render(self.scenes["callout"])
        self.assertIn(
            RenderIssueCode.SVG_ATTRIBUTE_FORBIDDEN,
            {issue.code for issue in ctx.exception.issues},
        )


if __name__ == "__main__":
    unittest.main()
