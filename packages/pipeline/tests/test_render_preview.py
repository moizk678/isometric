import copy
import unittest
from io import BytesIO

from isometric_pipeline.render.errors import RenderError, RenderIssueCode
from isometric_pipeline.render.preview import rasterize_preview
from PIL import Image

_SAMPLE_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" width="20" height="20">
  <rect width="20" height="20" fill="#ffffff"/>
  <rect x="5" y="5" width="10" height="10" fill="#000000"/>
</svg>"""

_OVERLAY_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" width="20" height="20">
  <circle cx="10" cy="10" r="4" fill="#ff0000"/>
</svg>"""


class RasterizePreviewTest(unittest.TestCase):
    def test_png_dimensions_scale_with_zoom(self):
        base = rasterize_preview(_SAMPLE_SVG, scale=1.0)
        scaled = rasterize_preview(_SAMPLE_SVG, scale=2.5)
        with Image.open(BytesIO(base.png)) as image:
            self.assertEqual(image.size, (20, 20))
        with Image.open(BytesIO(scaled.png)) as image:
            self.assertEqual(image.size, (50, 50))

    def test_identical_sha256_within_one_process(self):
        first = rasterize_preview(_SAMPLE_SVG)
        second = rasterize_preview(_SAMPLE_SVG)
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(first.png, second.png)

    def test_garbage_svg_raises_rasterize_failed(self):
        with self.assertRaises(RenderError) as ctx:
            rasterize_preview(b"not an svg document")
        self.assertEqual(ctx.exception.codes, (RenderIssueCode.RASTERIZE_FAILED,))

    def test_overlay_does_not_mutate_export_bytes(self):
        export_svg = copy.deepcopy(_SAMPLE_SVG)
        before = bytes(export_svg)
        without_overlay = rasterize_preview(export_svg)
        with_overlay = rasterize_preview(
            export_svg, overlay_svg=copy.deepcopy(_OVERLAY_SVG)
        )
        self.assertEqual(export_svg, before)
        self.assertNotEqual(without_overlay.sha256, with_overlay.sha256)


if __name__ == "__main__":
    unittest.main()
