"""Visual diagnostics for primitive fitting."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image

from isometric_pipeline.primitives.artifact import (
    PrimitiveCandidate,
    UnresolvedEvidence,
)


def primitives_overlay_png(
    rgb: np.ndarray,
    primitives: list[PrimitiveCandidate],
    unresolved: list[UnresolvedEvidence],
) -> bytes:
    bgr = cv2.cvtColor(rgb.copy(), cv2.COLOR_RGB2BGR)
    for item in unresolved:
        if len(item.samples) < 2:
            continue
        pts = np.array(
            [(int(x), int(y)) for x, y in item.samples],
            dtype=np.int32,
        ).reshape(-1, 1, 2)
        cv2.polylines(bgr, [pts], False, (255, 0, 255), 2)
    for prim in primitives:
        color = (0, 200, 0) if prim.status == "accepted" else (0, 180, 255)
        if prim.status == "rejected":
            color = (80, 80, 80)
        p0 = (int(prim.start.x), int(prim.start.y))
        p1 = (int(prim.end.x), int(prim.end.y))
        cv2.line(bgr, p0, p1, color, 2)
    rgb_out = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb_out, mode="RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
