"""Emit trace SVG bytes."""

from __future__ import annotations

import hashlib
import json
from xml.sax.saxutils import escape

from isometric_pipeline.trace.artifact import TRACE_VERSION
from isometric_pipeline.trace.polylines import TracePath


def _xml_attr(value: str) -> str:
    return escape(value, {'"': '&quot;', "'": '&apos;'})

def render_trace_svg(
    *,
    width_px: int,
    height_px: int,
    page_hash: str,
    layer_paths: list[tuple[str, list[TracePath]]],
    stroke_width_px: float = 2.0,
) -> bytes:
    metadata = {
        "exportKind": "trace",
        "traceVersion": TRACE_VERSION,
        "pageHash": page_hash,
        "layerCount": len(layer_paths),
        "pathCount": sum(len(paths) for _, paths in layer_paths),
    }
    meta_json = json.dumps(metadata, separators=(",", ":"), sort_keys=True)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width_px} {height_px}" '
        f'width="{width_px}" height="{height_px}">',
        f"<metadata>{escape(meta_json)}</metadata>",
    ]
    for layer_id, paths in layer_paths:
        lines.append(f'<g id="trace-layer-{_xml_attr(layer_id)}">')
        for index, path in enumerate(paths):
            attrs = [f'id="trace-path-{_xml_attr(layer_id)}-{index:05d}"']
            attrs.append(f'd="{path.d}"')
            if path.stroke is not None:
                attrs.append(f'stroke="{path.stroke}"')
                attrs.append('fill="none"')
                attrs.append(f'stroke-width="{stroke_width_px:.3f}"')
                attrs.append('stroke-linecap="round"')
                attrs.append('stroke-linejoin="round"')
            elif path.fill is not None:
                attrs.append(f'fill="{path.fill}"')
                attrs.append('stroke="none"')
            lines.append(f"<path {' '.join(attrs)}/>")
        lines.append("</g>")
    lines.append("</svg>")
    body = "\n".join(lines) + "\n"
    return body.encode("utf-8")


def trace_svg_sha256(svg: bytes) -> str:
    return hashlib.sha256(svg).hexdigest()
