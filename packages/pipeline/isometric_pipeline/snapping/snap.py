"""Per-primitive snapping to inferred isometric axes."""

from __future__ import annotations

import math

from isometric_pipeline.primitives.artifact import PrimitiveCandidate
from isometric_pipeline.profiles.loader import SnappingProfile
from isometric_pipeline.regions.artifact import RegionCandidate
from isometric_pipeline.snapping.artifact import (
    DecisionReason,
    PagePoint,
    SegmentGeom,
    SnappedPrimitiveCandidate,
    SnapStatus,
)
from isometric_pipeline.snapping.axes import (
    AxisModel,
    nearest_axis_id,
    undirected_angle_deg,
)


def _segment_geom(prim: PrimitiveCandidate) -> SegmentGeom:
    return SegmentGeom(
        start=PagePoint(x=float(prim.start.x), y=float(prim.start.y)),
        end=PagePoint(x=float(prim.end.x), y=float(prim.end.y)),
    )


def _residual_rms(samples: list[tuple[float, float]], seg: SegmentGeom) -> float:
    if not samples:
        return 0.0
    x0, y0 = seg.start.x, seg.start.y
    x1, y1 = seg.end.x, seg.end.y
    dx, dy = x1 - x0, y1 - y0
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-6:
        return 0.0
    errs: list[float] = []
    for sx, sy in samples:
        t = ((sx - x0) * dx + (sy - y0) * dy) / length_sq
        t = max(0.0, min(1.0, t))
        px = x0 + t * dx
        py = y0 + t * dy
        errs.append(math.hypot(sx - px, sy - py))
    return float(math.sqrt(sum(e * e for e in errs) / len(errs)))


def _shortest_angle_delta_rad(segment_rad: float, axis_angle_deg: float) -> float:
    axis_rad = math.radians(axis_angle_deg)
    delta = axis_rad - segment_rad
    while delta > math.pi:
        delta -= 2.0 * math.pi
    while delta < -math.pi:
        delta += 2.0 * math.pi
    alt = delta + math.pi if delta < 0 else delta - math.pi
    if abs(alt) < abs(delta):
        delta = alt
    return delta


def _snap_segment_to_angle(seg: SegmentGeom, axis_angle_deg: float) -> SegmentGeom:
    dx = seg.end.x - seg.start.x
    dy = seg.end.y - seg.start.y
    segment_rad = math.atan2(dy, dx)
    delta = _shortest_angle_delta_rad(segment_rad, axis_angle_deg)
    mx = (seg.start.x + seg.end.x) / 2.0
    my = (seg.start.y + seg.end.y) / 2.0
    cos_d = math.cos(delta)
    sin_d = math.sin(delta)

    def _rotate(px: float, py: float) -> PagePoint:
        sx, sy = px - mx, py - my
        return PagePoint(
            x=mx + sx * cos_d - sy * sin_d,
            y=my + sx * sin_d + sy * cos_d,
        )

    return SegmentGeom(
        start=_rotate(seg.start.x, seg.start.y),
        end=_rotate(seg.end.x, seg.end.y),
    )


def endpoint_displacement_px(pre: SegmentGeom, post: SegmentGeom) -> float:
    d0 = math.hypot(post.start.x - pre.start.x, post.start.y - pre.start.y)
    d1 = math.hypot(post.end.x - pre.end.x, post.end.y - pre.end.y)
    return max(d0, d1)


def _max_endpoint_displacement(pre: SegmentGeom, post: SegmentGeom) -> float:
    return endpoint_displacement_px(pre, post)


def _overlaps_dimension_region(
    prim: PrimitiveCandidate,
    regions: list[RegionCandidate],
    fraction: float,
) -> bool:
    x0 = min(prim.start.x, prim.end.x)
    x1 = max(prim.start.x, prim.end.x)
    y0 = min(prim.start.y, prim.end.y)
    y1 = max(prim.start.y, prim.end.y)
    prim_area = max(1.0, (x1 - x0) * (y1 - y0))
    mx = (prim.start.x + prim.end.x) / 2.0
    my = (prim.start.y + prim.end.y) / 2.0
    for region in regions:
        if region.kind != "dimension":
            continue
        bx, by = region.bbox.x, region.bbox.y
        bw, bh = region.bbox.width, region.bbox.height
        ix0 = max(x0, bx)
        iy0 = max(y0, by)
        ix1 = min(x1, bx + bw)
        iy1 = min(y1, by + bh)
        if ix1 <= ix0 or iy1 <= iy0:
            if bx <= mx <= bx + bw and by <= my <= by + bh:
                return True
            continue
        overlap = (ix1 - ix0) * (iy1 - iy0)
        if overlap / prim_area >= fraction:
            return True
    return False


def _preserved(
    prim: PrimitiveCandidate,
    pre: SegmentGeom,
    reason: DecisionReason,
    detail: str,
    angle_delta: float = 0.0,
    attempted_displacement_px: float = 0.0,
) -> SnappedPrimitiveCandidate:
    status: SnapStatus = "preserved"
    return SnappedPrimitiveCandidate(
        primitive_id=prim.id,
        layer_id=prim.layer_id,
        status=status,
        pre_snap=pre,
        post_snap=pre,
        axis_id=None,
        angle_delta_deg=angle_delta,
        max_endpoint_displacement_px=attempted_displacement_px,
        residual_rms_px=prim.residual_rms_px,
        decision_reason=reason,
        reason=detail,
        evidence=prim.evidence,
    )


def snap_primitive(
    prim: PrimitiveCandidate,
    axis_model: AxisModel,
    profile: SnappingProfile,
    regions: list[RegionCandidate],
) -> SnappedPrimitiveCandidate:
    pre = _segment_geom(prim)
    seg_angle = undirected_angle_deg(
        prim.end.x - prim.start.x, prim.end.y - prim.start.y
    )
    length = math.hypot(prim.end.x - prim.start.x, prim.end.y - prim.start.y)

    if prim.status == "uncertain":
        return _preserved(
            prim,
            pre,
            "preserved_uncertain",
            "primitive marked uncertain",
            angle_delta=0.0,
        )

    if axis_model.model_confidence < profile.min_axis_model_confidence:
        return _preserved(
            prim,
            pre,
            "weak_axis_model",
            "axis model confidence below profile threshold",
        )

    if length < profile.min_primitive_length_px:
        return _preserved(
            prim,
            pre,
            "low_evidence",
            "segment shorter than min_primitive_length_px",
        )

    if profile.skip_dimension_region_overlap and _overlaps_dimension_region(
        prim, regions, profile.dimension_overlap_fraction
    ):
        return _preserved(
            prim,
            pre,
            "dimension_region",
            "segment overlaps dimension region",
        )

    axis_id, axis_angle, angle_delta = nearest_axis_id(seg_angle, axis_model)
    if axis_id is None:
        return _preserved(prim, pre, "weak_axis_model", "no axes in model")

    if angle_delta > profile.max_snap_angle_deg:
        return _preserved(
            prim,
            pre,
            "off_axis",
            f"angle delta {angle_delta:.2f}° exceeds max_snap_angle_deg",
            angle_delta=angle_delta,
        )

    post = _snap_segment_to_angle(pre, axis_angle)
    displacement = _max_endpoint_displacement(pre, post)
    if displacement > profile.max_endpoint_displacement_px:
        return _preserved(
            prim,
            pre,
            "endpoint_displacement",
            f"endpoint displacement {displacement:.2f}px too large",
            angle_delta=angle_delta,
            attempted_displacement_px=displacement,
        )

    residual = _residual_rms(prim.samples, post)
    if residual > profile.max_residual_after_snap_px:
        return _preserved(
            prim,
            pre,
            "residual_too_high",
            f"post-snap residual {residual:.2f}px too high",
            angle_delta=angle_delta,
        )

    return SnappedPrimitiveCandidate(
        primitive_id=prim.id,
        layer_id=prim.layer_id,
        status="snapped",
        pre_snap=pre,
        post_snap=post,
        axis_id=axis_id,
        angle_delta_deg=angle_delta,
        max_endpoint_displacement_px=displacement,
        residual_rms_px=residual,
        decision_reason="snapped_to_axis",
        reason=f"snap to {axis_id} at {axis_angle:.1f}°",
        evidence=prim.evidence,
    )


def snap_all_primitives(
    primitives: list[PrimitiveCandidate],
    axis_model: AxisModel,
    profile: SnappingProfile,
    regions: list[RegionCandidate],
) -> list[SnappedPrimitiveCandidate]:
    eligible = sorted(
        [p for p in primitives if p.status in ("accepted", "uncertain")],
        key=lambda p: p.id,
    )
    return [
        snap_primitive(prim, axis_model, profile, regions) for prim in eligible
    ]
