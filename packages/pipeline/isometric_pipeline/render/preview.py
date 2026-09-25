"""PNG preview rasterization with a pinned resvg-py and a bundled font."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from xml.parsers import expat

import resvg_py

from .errors import RenderError, RenderIssue, RenderIssueCode
from .types import PreviewResult
from .versions import (
    RASTERIZER,
    RESVG_BACKGROUND_KWARG,
    RESVG_FONT_FILES_KWARG,
    RESVG_SKIP_SYSTEM_FONTS_KWARG,
    RESVG_SVG_STRING_KWARG,
    RESVG_ZOOM_KWARG,
)

_BUNDLED_FONT = (
    Path(__file__).resolve().parents[3]
    / "symbol-library"
    / "fonts"
    / "LiberationSans-Regular.ttf"
)
_PREVIEW_BACKGROUND = "#ffffff"
_SVG_CLOSE_RE = re.compile(r"</svg\s*>", re.IGNORECASE)
# resvg reads any file path given as an image href, and an SVG data: image
# carries hrefs of its own, so only local and raster data: hrefs may pass.
_ALLOWED_HREF_RE = re.compile(
    r"\s*(?:#|data:image/(?:png|jpeg|gif|webp)[;,])", re.IGNORECASE
)


def rasterize_preview(
    svg: bytes, *, scale: float = 1.0, overlay_svg: bytes | None = None
) -> PreviewResult:
    """Rasterize ``svg``; ``overlay_svg`` is drawn only into the preview."""
    if not math.isfinite(scale) or scale <= 0.0:
        raise RenderError(
            [
                RenderIssue(
                    code=RenderIssueCode.RASTERIZE_FAILED,
                    path="preview.scale",
                    object_id=None,
                    message=f"scale must be finite and positive, got {scale!r}",
                )
            ]
        )

    preview_svg = _preview_svg_string(svg, overlay_svg)
    png = _rasterize_svg_string(preview_svg, scale)
    return PreviewResult(
        png=png,
        sha256=hashlib.sha256(png).hexdigest(),
        rasterizer=RASTERIZER,
        font=_bundled_font_descriptor(),
    )


def _preview_svg_string(svg: bytes, overlay_svg: bytes | None) -> str:
    base = _bytes_to_svg_string(svg)
    _check_self_contained(svg, "preview")
    if overlay_svg is None:
        return base
    overlay = _bytes_to_svg_string(overlay_svg)
    _check_self_contained(overlay_svg, "preview.overlay_svg")
    opening, base_inner = _split_svg_document(base)
    _, overlay_inner = _split_svg_document(overlay)
    return f"{opening}{base_inner}{overlay_inner}</svg>"


def _bytes_to_svg_string(svg: bytes) -> str:
    try:
        return svg.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _rasterize_error(f"SVG is not valid UTF-8: {exc}") from None


class _Refused(Exception):
    def __init__(self, code: RenderIssueCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _check_self_contained(svg: bytes, path: str) -> None:
    """Refuse DTDs and hrefs that would make resvg read outside the document."""

    def refuse(*_args: object) -> None:
        raise _Refused(
            RenderIssueCode.SVG_XML_INVALID,
            "DOCTYPE and processing instructions are not allowed",
        )

    def start(_name: str, attributes: list[str]) -> None:
        for name, value in zip(attributes[::2], attributes[1::2], strict=True):
            if (name == "href" or name.endswith(":href")) and not (
                _ALLOWED_HREF_RE.match(value)
            ):
                raise _Refused(
                    RenderIssueCode.SVG_EXTERNAL_REFERENCE,
                    f"{name}={value[:60]!r} is not a local or data: href",
                )

    parser = expat.ParserCreate()
    parser.ordered_attributes = True
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    parser.StartDoctypeDeclHandler = refuse
    parser.ProcessingInstructionHandler = refuse
    parser.StartElementHandler = start
    try:
        parser.Parse(svg, True)
    except _Refused as exc:
        raise RenderError(
            [RenderIssue(code=exc.code, path=path, object_id=None, message=str(exc))]
        ) from None
    except expat.ExpatError as exc:
        raise _rasterize_error(f"SVG is not well-formed XML: {exc}") from None


def _split_svg_document(svg: str) -> tuple[str, str]:
    stripped = svg.strip()
    lower = stripped.lower()
    start = lower.find("<svg")
    if start < 0:
        raise _rasterize_error("SVG document is missing a root <svg> element")
    open_end = stripped.find(">", start)
    if open_end < 0:
        raise _rasterize_error("SVG root element is not closed")
    close_match = _SVG_CLOSE_RE.search(stripped, open_end + 1)
    if close_match is None:
        raise _rasterize_error("SVG document is missing a closing </svg> tag")
    opening = stripped[start : open_end + 1]
    inner = stripped[open_end + 1 : close_match.start()]
    return opening, inner


def _rasterize_svg_string(svg_string: str, scale: float) -> bytes:
    # With system fonts skipped, a missing bundled font would silently drop
    # every glyph from the preview.
    if not _BUNDLED_FONT.is_file():
        raise _rasterize_error(f"bundled preview font is missing: {_BUNDLED_FONT}")
    kwargs: dict[str, object] = {
        RESVG_SVG_STRING_KWARG: svg_string,
        RESVG_ZOOM_KWARG: scale,
        RESVG_BACKGROUND_KWARG: _PREVIEW_BACKGROUND,
        RESVG_SKIP_SYSTEM_FONTS_KWARG: True,
        RESVG_FONT_FILES_KWARG: [str(_BUNDLED_FONT)],
    }
    try:
        return resvg_py.svg_to_bytes(**kwargs)
    except Exception as exc:
        raise _rasterize_error(str(exc)) from None


def _bundled_font_descriptor() -> str:
    digest = hashlib.sha256(_BUNDLED_FONT.read_bytes()).hexdigest()
    return f"{_BUNDLED_FONT.name}@sha256:{digest}"


def _rasterize_error(message: str) -> RenderError:
    return RenderError(
        [
            RenderIssue(
                code=RenderIssueCode.RASTERIZE_FAILED,
                path="preview",
                object_id=None,
                message=message,
            )
        ]
    )
