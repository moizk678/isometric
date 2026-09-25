"""Visual diagnostics for association candidates."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image

from isometric_pipeline.associate_markup.artifact import (
    AssociationCandidatesMetadata,
    PagePoint,
)


def association_overlay_png(
    rgb: np.ndarray, metadata: AssociationCandidatesMetadata
) -> bytes:
    bgr = cv2.cvtColor(rgb.copy(), cv2.COLOR_RGB2BGR)
    for geo in metadata.dimension_geometry:
        w = geo.witness_line
        cv2.line(
            bgr,
            (int(w.start.x), int(w.start.y)),
            (int(w.end.x), int(w.end.y)),
            (255, 120, 0),
            2,
        )
        for tip in geo.arrowhead_points:
            cv2.circle(bgr, (int(tip.x), int(tip.y)), 4, (0, 200, 255), -1)

    for dim in metadata.dimension_candidates:
        cv2.line(
            bgr,
            (int(dim.witness_start.x), int(dim.witness_start.y)),
            (int(dim.witness_end.x), int(dim.witness_end.y)),
            (0, 220, 0) if dim.status == "proposed" else (0, 140, 140),
            1,
        )
        cv2.putText(
            bgr,
            dim.display_text[:24],
            (int(dim.witness_start.x), int(dim.witness_start.y) - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (0, 180, 0),
            1,
            cv2.LINE_AA,
        )

    for ann in metadata.annotation_targets:
        if len(ann.leader_polyline) >= 2:
            pts = np.array(
                [(int(p.x), int(p.y)) for p in ann.leader_polyline], dtype=np.int32
            )
            cv2.polylines(bgr, [pts], False, (200, 0, 200), 1)
        if ann.alternatives:
            anchor = (
                ann.leader_polyline[0] if ann.leader_polyline else PagePoint(x=0, y=0)
            )
            label = ann.alternatives[0].ref_id[:20]
            cv2.putText(
                bgr,
                label,
                (int(anchor.x), max(12, int(anchor.y) - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (180, 0, 180),
                1,
                cv2.LINE_AA,
            )

    rgb_out = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb_out, mode="RGB")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
