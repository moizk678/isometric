"""Working segments from snapped primitives."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from isometric_pipeline.primitives.artifact import (
    PrimitiveCandidate,
    PrimitivesMetadata,
)
from isometric_pipeline.profiles.loader import TopologyProfile
from isometric_pipeline.snapping.artifact import (
    SnappedPrimitivesMetadata,
)


@dataclass
class WorkingSegment:
    segment_id: str
    primitive_id: str
    layer_id: str
    component_id: str
    centerline_edge_id: str
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    merged_primitive_ids: list[str] = field(default_factory=list)
    merged_component_ids: list[str] = field(default_factory=list)

    def length(self) -> float:
        return math.hypot(self.end_x - self.start_x, self.end_y - self.start_y)

    def angle_deg(self) -> float:
        return math.degrees(
            math.atan2(self.end_y - self.start_y, self.end_x - self.start_x)
        )

    def endpoints(self) -> tuple[tuple[float, float], tuple[float, float]]:
        return (self.start_x, self.start_y), (self.end_x, self.end_y)


def _primitive_map(primitives: PrimitivesMetadata) -> dict[str, PrimitiveCandidate]:
    return {prim.id: prim for prim in primitives.primitives}


def segments_from_snapped(
    snapped: SnappedPrimitivesMetadata,
    primitives: PrimitivesMetadata,
) -> list[WorkingSegment]:
    prim_by_id = _primitive_map(primitives)
    segments: list[WorkingSegment] = []
    for cand in snapped.candidates:
        if cand.status == "skipped":
            continue
        prim = prim_by_id.get(cand.primitive_id)
        if prim is None or prim.status == "rejected":
            continue
        segments.append(
            WorkingSegment(
                segment_id=cand.primitive_id,
                primitive_id=cand.primitive_id,
                layer_id=cand.layer_id,
                component_id=prim.component_id,
                centerline_edge_id=prim.centerline_edge_id,
                start_x=cand.post_snap.start.x,
                start_y=cand.post_snap.start.y,
                end_x=cand.post_snap.end.x,
                end_y=cand.post_snap.end.y,
                merged_primitive_ids=[cand.primitive_id],
                merged_component_ids=[prim.component_id],
            )
        )
    return segments


def segment_direction_delta_deg(a: WorkingSegment, b: WorkingSegment) -> float:
    da = a.angle_deg()
    db = b.angle_deg()
    delta = abs(da - db) % 180.0
    return min(delta, 180.0 - delta)


def collinear_compatible(
    a: WorkingSegment,
    b: WorkingSegment,
    profile: TopologyProfile,
) -> bool:
    if a.layer_id != b.layer_id:
        return False
    return segment_direction_delta_deg(a, b) <= profile.collinear_angle_tolerance_deg


def point_distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)
