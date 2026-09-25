"""PNG preview rasterization with a pinned resvg-py and a bundled font."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

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
    if overlay_svg is None:
        return base
    overlay = _bytes_to_svg_string(overlay_svg)
    opening, base_inner = _split_svg_document(base)
    _, overlay_inner = _split_svg_document(overlay)
    return f"{opening}{base_inner}{overlay_inner}</svg>"


def _bytes_to_svg_string(svg: bytes) -> str:
    try:
        return svg.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _rasterize_error(f"SVG is not valid UTF-8: {exc}") from None


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
    kwargs: dict[str, object] = {
        RESVG_SVG_STRING_KWARG: svg_string,
        RESVG_ZOOM_KWARG: scale,
        RESVG_BACKGROUND_KWARG: _PREVIEW_BACKGROUND,
        RESVG_SKIP_SYSTEM_FONTS_KWARG: True,
    }
    if _BUNDLED_FONT.is_file():
        kwargs[RESVG_FONT_FILES_KWARG] = [str(_BUNDLED_FONT)]
    try:
        return resvg_py.svg_to_bytes(**kwargs)
    except Exception as exc:
        raise _rasterize_error(str(exc)) from None


def _bundled_font_descriptor() -> str:
    if not _BUNDLED_FONT.is_file():
        return ""
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
