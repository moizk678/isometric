"""Visual diagnostics for topology inference."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image

from isometric_pipeline.topology.artifact import (
    IntersectionHypothesis,
    NodeCandidate,
    TopologyMetadata,
)

_KIND_COLORS_BGR = {
    "endpoint": (180, 180, 180),
    "elbow": (0, 200, 255),
    "tee": (0, 220, 0),
    "crossing": (0, 140, 255),
    "unknown": (200, 100, 255),
}


def topology_overlay_png(
    rgb: np.ndarray,
    metadata: TopologyMetadata,
) -> bytes:
    bgr = cv2.cvtColor(rgb.copy(), cv2.COLOR_RGB2BGR)
    for edge in metadata.edges:
        p0 = (int(edge.start.x), int(edge.start.y))
        p1 = (int(edge.end.x), int(edge.end.y))
        cv2.line(bgr, p0, p1, (120, 120, 120), 2, cv2.LINE_AA)

    for node in metadata.nodes:
        color = _KIND_COLORS_BGR.get(node.kind, (200, 200, 200))
        center = (int(node.position.x), int(node.position.y))
        cv2.circle(bgr, center, 6, color, -1, cv2.LINE_AA)

    for hypothesis in metadata.hypotheses:
        if not isinstance(hypothesis, IntersectionHypothesis):
            continue
        pt = (
            int(hypothesis.position.x),
            int(hypothesis.position.y),
        )
        cv2.drawMarker(
            bgr,
            pt,
            (255, 0, 255),
            markerType=cv2.MARKER_CROSS,
            markerSize=14,
            thickness=2,
        )

    rgb_out = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb_out, mode="RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
