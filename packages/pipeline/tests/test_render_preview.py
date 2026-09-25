import base64
import copy
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

import isometric_pipeline.render.preview as preview_module
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

_EMPTY_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" width="20"'
    b' height="20"></svg>'
)


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

    def test_file_and_remote_hrefs_are_refused_in_base_and_overlay(self):
        for href in (
            'href="/etc/secret.png"',
            'href="file:///etc/secret.png"',
            'href="https://evil.example/x.png"',
            'xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="secret.png"',
            'href="data:image/svg+xml;base64,PHN2Zy8+"',
        ):
            image = f'<image {href} width="20" height="20"/>'.encode()
            document = _EMPTY_SVG.replace(b"</svg>", image + b"</svg>")
            for name, kwargs in (
                ("base", {"svg": document}),
                ("overlay", {"svg": _SAMPLE_SVG, "overlay_svg": document}),
            ):
                with self.subTest(href=href, document=name):
                    with self.assertRaises(RenderError) as ctx:
                        rasterize_preview(**kwargs)
                    self.assertEqual(
                        ctx.exception.codes, (RenderIssueCode.SVG_EXTERNAL_REFERENCE,)
                    )

    def test_local_and_raster_data_hrefs_are_allowed(self):
        png = BytesIO()
        Image.new("RGB", (1, 1), (255, 0, 0)).save(png, format="PNG")
        data = base64.b64encode(png.getvalue()).decode()
        overlay = _EMPTY_SVG.replace(
            b"</svg>",
            f'<image href="data:image/png;base64,{data}" width="20" height="20"/>'
            "</svg>".encode(),
        )
        preview = rasterize_preview(_SAMPLE_SVG, overlay_svg=overlay)
        with Image.open(BytesIO(preview.png)) as image:
            self.assertEqual(image.convert("RGB").getpixel((1, 1)), (255, 0, 0))

    def test_doctype_is_refused(self):
        svg = b'<!DOCTYPE svg [<!ENTITY p "/etc/secret.png">]>' + _SAMPLE_SVG
        with self.assertRaises(RenderError) as ctx:
            rasterize_preview(svg)
        self.assertEqual(ctx.exception.codes, (RenderIssueCode.SVG_XML_INVALID,))

    def test_missing_bundled_font_fails_instead_of_dropping_text(self):
        missing = Path(__file__).with_name("no-such-font.ttf")
        with mock.patch.object(preview_module, "_BUNDLED_FONT", missing):
            with self.assertRaises(RenderError) as ctx:
                rasterize_preview(_SAMPLE_SVG)
        self.assertEqual(ctx.exception.codes, (RenderIssueCode.RASTERIZE_FAILED,))
        self.assertIn("font", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
