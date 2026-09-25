"""Visual diagnostics for symbol candidates."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image

from isometric_pipeline.symbol_candidates.artifact import SymbolCandidatesMetadata


def symbol_overlay_png(rgb: np.ndarray, metadata: SymbolCandidatesMetadata) -> bytes:
    bgr = cv2.cvtColor(rgb.copy(), cv2.COLOR_RGB2BGR)
    for candidate in metadata.candidates:
        bb = candidate.bbox
        x0 = int(bb.x)
        y0 = int(bb.y)
        x1 = int(bb.x + bb.width)
        y1 = int(bb.y + bb.height)
        if candidate.status == "unreadable":
            color = (0, 0, 220)
        elif candidate.status == "unknown":
            color = (0, 165, 255)
        else:
            color = (0, 180, 0)
        cv2.rectangle(bgr, (x0, y0), (x1, y1), color, 2)
        label = candidate.status
        if candidate.alternatives:
            label = candidate.alternatives[0].symbol_id
        cv2.putText(
            bgr,
            label,
            (x0, max(y0 - 4, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            color,
            1,
            cv2.LINE_AA,
        )
        ax = int(candidate.anchor.x)
        ay = int(candidate.anchor.y)
        cv2.circle(bgr, (ax, ay), 3, (200, 0, 200), -1)
    rgb_out = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb_out, mode="RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
