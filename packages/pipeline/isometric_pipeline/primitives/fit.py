"""Line fitting from centerline edges."""

from __future__ import annotations

import math

import cv2
import numpy as np

from isometric_pipeline.centerlines.artifact import CenterlineEdge
from isometric_pipeline.primitives.artifact import PageBBox, PagePoint
from isometric_pipeline.profiles.loader import GeometryProfile


def edge_bbox(samples: list[tuple[float, float]]) -> PageBBox:
    xs = [p[0] for p in samples]
    ys = [p[1] for p in samples]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return PageBBox(x=x0, y=y0, width=max(1.0, x1 - x0), height=max(1.0, y1 - y0))


def is_straight_enough(
    samples: list[tuple[float, float]], profile: GeometryProfile
) -> bool:
    if len(samples) < 2:
        return False
    start = np.array(samples[0], dtype=np.float64)
    end = np.array(samples[-1], dtype=np.float64)
    chord = end - start
    length = float(np.linalg.norm(chord))
    if length < 1e-6:
        return False
    max_dev = 0.0
    for x, y in samples:
        pt = np.array([x, y], dtype=np.float64)
        cross = abs(chord[0] * (start[1] - pt[1]) - chord[1] * (start[0] - pt[0]))
        dev = cross / length
        max_dev = max(max_dev, dev)
    if max_dev > profile.max_chord_deviation_px:
        _, _, rms, r_squared = fit_line(samples)
        return (
            rms <= profile.max_line_fit_residual_px * 2.0
            and r_squared >= profile.min_r_squared * 0.85
        )
    return True


def fit_line(
    samples: list[tuple[float, float]],
) -> tuple[PagePoint, PagePoint, float, float]:
    pts = np.array(samples, dtype=np.float32)
    if pts.shape[0] < 2:
        raise ValueError("need at least two samples")
    vx, vy, x0, y0 = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01)
    direction = np.array([float(vx.item()), float(vy.item())], dtype=np.float64)
    direction = direction / (np.linalg.norm(direction) + 1e-9)
    origin = np.array([float(x0.item()), float(y0.item())], dtype=np.float64)
    projections = [
        float(np.dot(np.array(p, dtype=np.float64) - origin, direction))
        for p in samples
    ]
    t_min, t_max = min(projections), max(projections)
    start = origin + direction * t_min
    end = origin + direction * t_max
    residuals = []
    for x, y in samples:
        pt = np.array([x, y], dtype=np.float64)
        proj = origin + direction * float(np.dot(pt - origin, direction))
        residuals.append(float(np.linalg.norm(pt - proj)))
    rms = float(math.sqrt(sum(r * r for r in residuals) / len(residuals)))
    mean = np.mean(pts, axis=0)
    ss_tot = float(np.sum((pts - mean) ** 2))
    ss_res = float(np.sum([(r) ** 2 for r in residuals]))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-9 else 1.0
    return (
        PagePoint(x=float(start[0]), y=float(start[1])),
        PagePoint(x=float(end[0]), y=float(end[1])),
        rms,
        r_squared,
    )


def estimate_stroke_width(
    mask: np.ndarray,
    edge: CenterlineEdge,
    profile: GeometryProfile,
) -> float:
    if not np.any(mask) or len(edge.samples) < 2:
        return 1.0
    dist = cv2.distanceTransform((mask > 0).astype(np.uint8), cv2.DIST_L2, 3)
    widths: list[float] = []
    for x, y in edge.samples[:: max(1, len(edge.samples) // 10)]:
        ix, iy = int(round(x)), int(round(y))
        if 0 <= iy < mask.shape[0] and 0 <= ix < mask.shape[1]:
            widths.append(float(dist[iy, ix]) * 2.0)
    if not widths:
        return 1.0
    percentile = min(100.0, max(0.0, profile.stroke_width_percentile))
    return float(np.percentile(widths, percentile))
