"""Row-major 3x3 homography utilities (scene contract)."""

from __future__ import annotations

import math
from collections.abc import Sequence

Matrix = list[float]

IDENTITY_MAT3: Matrix = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
ROUND_TRIP_TOLERANCE_PX = 0.5


def apply_mat3(matrix: Sequence[float], x: float, y: float) -> tuple[float, float]:
    w = matrix[6] * x + matrix[7] * y + matrix[8]
    if w == 0:
        raise ValueError("homography maps point to infinity")
    return (
        (matrix[0] * x + matrix[1] * y + matrix[2]) / w,
        (matrix[3] * x + matrix[4] * y + matrix[5]) / w,
    )


def multiply_mat3(a: Sequence[float], b: Sequence[float]) -> Matrix:
    return [
        sum(a[row * 3 + k] * b[k * 3 + col] for k in range(3))
        for row in range(3)
        for col in range(3)
    ]


compose_mat3 = multiply_mat3


def _determinant(m: Sequence[float]) -> float:
    return (
        m[0] * (m[4] * m[8] - m[5] * m[7])
        - m[1] * (m[3] * m[8] - m[5] * m[6])
        + m[2] * (m[3] * m[7] - m[4] * m[6])
    )


def invert_mat3(m: Sequence[float]) -> Matrix:
    det = _determinant(m)
    if not math.isfinite(det) or abs(det) < 1e-12:
        raise ValueError("matrix is not invertible")
    inv_det = 1.0 / det
    return [
        (m[4] * m[8] - m[5] * m[7]) * inv_det,
        (m[2] * m[7] - m[1] * m[8]) * inv_det,
        (m[1] * m[5] - m[2] * m[4]) * inv_det,
        (m[5] * m[6] - m[3] * m[8]) * inv_det,
        (m[0] * m[8] - m[2] * m[6]) * inv_det,
        (m[2] * m[3] - m[0] * m[5]) * inv_det,
        (m[3] * m[7] - m[4] * m[6]) * inv_det,
        (m[1] * m[6] - m[0] * m[7]) * inv_det,
        (m[0] * m[4] - m[1] * m[3]) * inv_det,
    ]


def round_trip_within_tolerance(
    forward: Sequence[float],
    inverse: Sequence[float],
    x: float,
    y: float,
    *,
    tolerance_px: float = ROUND_TRIP_TOLERANCE_PX,
) -> bool:
    dx, dy = apply_mat3(forward, x, y)
    rx, ry = apply_mat3(inverse, dx, dy)
    return abs(rx - x) <= tolerance_px and abs(ry - y) <= tolerance_px
