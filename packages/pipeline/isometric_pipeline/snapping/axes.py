"""Isometric axis inference from primitive angles."""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from isometric_pipeline.primitives.artifact import PrimitiveCandidate
from isometric_pipeline.profiles.loader import SnappingProfile
from isometric_pipeline.snapping.artifact import (
    AxisInferenceMethod,
    AxisKind,
    AxisRecord,
)


@dataclass(frozen=True)
class AxisModel:
    rotation_deg: float
    axes: list[AxisRecord]
    model_confidence: float
    inference_method: AxisInferenceMethod
    total_vote_weight: float


def undirected_angle_deg(dx: float, dy: float) -> float:
    ang = math.degrees(math.atan2(dy, dx))
    ang = ang % 180.0
    if ang < 0:
        ang += 180.0
    return ang


def angle_distance_deg(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def triad_angles_deg(rotation_deg: float) -> tuple[float, float, float]:
    """Vertical plus two iso directions, 60° apart in undirected space."""
    v = (rotation_deg + 90.0) % 180.0
    a = (rotation_deg + 30.0) % 180.0
    b = (rotation_deg + 150.0) % 180.0
    return v, a, b


def nearest_axis_angle(
    segment_angle: float, rotation_deg: float
) -> tuple[float, float]:
    """Return (nearest_axis_angle, angular_distance)."""
    candidates = triad_angles_deg(rotation_deg)
    best_angle = candidates[0]
    best_dist = angle_distance_deg(segment_angle, candidates[0])
    for cand in candidates[1:]:
        dist = angle_distance_deg(segment_angle, cand)
        if dist < best_dist:
            best_dist = dist
            best_angle = cand
    return best_angle, best_dist


def _segment_length(prim: PrimitiveCandidate) -> float:
    return float(math.hypot(prim.end.x - prim.start.x, prim.end.y - prim.start.y))


def _collect_votes(
    primitives: list[PrimitiveCandidate], min_length: float
) -> list[tuple[float, float]]:
    votes: list[tuple[float, float]] = []
    for prim in primitives:
        if prim.kind != "line" or prim.status not in ("accepted", "uncertain"):
            continue
        length = _segment_length(prim)
        if length < min_length:
            continue
        ang = undirected_angle_deg(prim.end.x - prim.start.x, prim.end.y - prim.start.y)
        votes.append((ang, length))
    return votes


def _score_rotation(rotation_deg: float, votes: list[tuple[float, float]]) -> float:
    score = 0.0
    for ang, weight in votes:
        _, dist = nearest_axis_angle(ang, rotation_deg)
        if dist <= 12.0:
            score += weight * max(0.0, 1.0 - dist / 12.0)
    return score


def _axis_weights(
    rotation_deg: float, votes: list[tuple[float, float]]
) -> tuple[float, float, float]:
    angles = triad_angles_deg(rotation_deg)
    weights = [0.0, 0.0, 0.0]
    for ang, w in votes:
        for i, axis_ang in enumerate(angles):
            dist = angle_distance_deg(ang, axis_ang)
            if dist <= 15.0:
                weights[i] += w * max(0.0, 1.0 - dist / 15.0)
    return weights[0], weights[1], weights[2]


def grid_rotation_hint_deg(grid_mask: np.ndarray) -> float | None:
    """Estimate dominant grid rotation from mask line orientations."""
    if grid_mask.size == 0 or int(np.count_nonzero(grid_mask)) < 50:
        return None
    edges = cv2.Canny(grid_mask, 50, 150)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=40,
        minLineLength=30,
        maxLineGap=8,
    )
    if lines is None or len(lines) == 0:
        return None
    angles: list[float] = []
    weights: list[float] = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 20:
            continue
        ang = undirected_angle_deg(float(x2 - x1), float(y2 - y1))
        angles.append(ang)
        weights.append(length)
    if not angles:
        return None
    best_rot = 0.0
    best_score = -1.0
    for rot_i in range(0, 180):
        rot = float(rot_i)
        score = 0.0
        for ang, w in zip(angles, weights, strict=True):
            _, dist = nearest_axis_angle(ang, rot)
            if dist <= 10.0:
                score += w * max(0.0, 1.0 - dist / 10.0)
        if score > best_score:
            best_score = score
            best_rot = rot
    return best_rot if best_score > 0 else None


def infer_axis_model(
    primitives: list[PrimitiveCandidate],
    profile: SnappingProfile,
    *,
    grid_confidence: float | None = None,
    grid_mask: np.ndarray | None = None,
) -> AxisModel:
    votes = _collect_votes(primitives, profile.min_primitive_length_px)
    total_weight = sum(w for _, w in votes)

    if total_weight < profile.min_primitive_length_px:
        return AxisModel(
            rotation_deg=0.0,
            axes=[],
            model_confidence=0.0,
            inference_method="insufficient_evidence",
            total_vote_weight=total_weight,
        )

    best_rot = 0.0
    best_score = -1.0
    for rot_i in range(0, 360):
        rot = float(rot_i) * 0.5
        score = _score_rotation(rot, votes)
        if score > best_score:
            best_score = score
            best_rot = rot

    method: AxisInferenceMethod = "primitive_histogram"
    grid_rot: float | None = None
    if (
        grid_mask is not None
        and grid_confidence is not None
        and grid_confidence >= profile.grid_confidence_min
    ):
        grid_rot = grid_rotation_hint_deg(grid_mask)
        if grid_rot is not None:
            primitive_score = best_score
            grid_score = _score_rotation(grid_rot, votes)
            if grid_score >= primitive_score * 0.85:
                best_rot = grid_rot
                best_score = grid_score
                method = "grid_assisted"

    model_confidence = min(1.0, best_score / max(total_weight, 1.0))
    w_v, w_a, w_b = _axis_weights(best_rot, votes)
    angles = triad_angles_deg(best_rot)
    kinds: list[AxisKind] = ["vertical", "iso_a", "iso_b"]
    axis_records: list[AxisRecord] = []
    for kind, ang, weight in zip(kinds, angles, (w_v, w_a, w_b), strict=True):
        conf = min(1.0, weight / max(total_weight, 1.0))
        axis_records.append(
            AxisRecord(
                id=f"axis_{kind}",
                kind=kind,
                angle_deg=ang,
                weight=weight,
                confidence=conf,
            )
        )

    return AxisModel(
        rotation_deg=best_rot,
        axes=axis_records,
        model_confidence=model_confidence,
        inference_method=method,
        total_vote_weight=total_weight,
    )


def axis_angle_by_id(axis_model: AxisModel, axis_id: str) -> float | None:
    for axis in axis_model.axes:
        if axis.id == axis_id:
            return axis.angle_deg
    return None


def nearest_axis_id(
    segment_angle: float, axis_model: AxisModel
) -> tuple[str | None, float, float]:
    if not axis_model.axes:
        return None, segment_angle, 180.0
    best_id: str | None = None
    best_ang = axis_model.axes[0].angle_deg
    best_dist = angle_distance_deg(segment_angle, best_ang)
    best_id = axis_model.axes[0].id
    for axis in axis_model.axes[1:]:
        dist = angle_distance_deg(segment_angle, axis.angle_deg)
        if dist < best_dist:
            best_dist = dist
            best_ang = axis.angle_deg
            best_id = axis.id
    return best_id, best_ang, best_dist
