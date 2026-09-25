"""Visual diagnostics for centerline extraction."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image

from isometric_pipeline.centerlines.artifact import CenterlineEdge, CenterlineNode


def centerlines_overlay_png(
    rgb: np.ndarray,
    mask: np.ndarray,
    skeleton: np.ndarray,
    nodes: list[CenterlineNode],
    edges: list[CenterlineEdge],
) -> bytes:
    overlay = rgb.copy().astype(np.float32)
    ink = mask > 0
    skel = skeleton > 0
    overlay[ink] = overlay[ink] * 0.5 + np.array([60, 60, 60], dtype=np.float32) * 0.5
    overlay[skel] = (
        overlay[skel] * 0.3 + np.array([0, 220, 255], dtype=np.float32) * 0.7
    )
    bgr = cv2.cvtColor(overlay.astype(np.uint8), cv2.COLOR_RGB2BGR)
    for edge in edges:
        if len(edge.samples) < 2:
            continue
        pts = np.array(
            [(int(x), int(y)) for x, y in edge.samples],
            dtype=np.int32,
        ).reshape(-1, 1, 2)
        cv2.polylines(bgr, [pts], False, (255, 120, 0), 1)
    for node in nodes:
        cx, cy = int(node.position.x), int(node.position.y)
        color = (0, 255, 0) if node.kind == "endpoint" else (0, 0, 255)
        cv2.circle(bgr, (cx, cy), 3, color, -1)
    rgb_out = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb_out, mode="RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
