"""Endpoint clustering into node candidates."""

from __future__ import annotations

import math
from dataclasses import dataclass

from isometric_pipeline.profiles.loader import TopologyProfile
from isometric_pipeline.topology.segments import WorkingSegment, point_distance


@dataclass
class EndpointRef:
    segment_id: str
    end_index: int  # 0 = start, 1 = end
    x: float
    y: float
    layer_id: str


@dataclass
class EndpointCluster:
    cluster_id: int
    members: list[EndpointRef]

    def centroid(self) -> tuple[float, float]:
        xs = [m.x for m in self.members]
        ys = [m.y for m in self.members]
        return sum(xs) / len(xs), sum(ys) / len(ys)

    def layer_ids(self) -> list[str]:
        return list(dict.fromkeys(m.layer_id for m in self.members))


def cluster_endpoints(
    segments: list[WorkingSegment],
    profile: TopologyProfile,
) -> list[EndpointCluster]:
    refs: list[EndpointRef] = []
    for seg in segments:
        refs.append(
            EndpointRef(seg.segment_id, 0, seg.start_x, seg.start_y, seg.layer_id)
        )
        refs.append(EndpointRef(seg.segment_id, 1, seg.end_x, seg.end_y, seg.layer_id))
    clusters: list[EndpointCluster] = []
    assigned = [-1] * len(refs)
    cluster_index = 0
    tol = profile.endpoint_cluster_tolerance_px
    for i, ref in enumerate(refs):
        if assigned[i] >= 0:
            continue
        members = [ref]
        assigned[i] = cluster_index
        for j in range(i + 1, len(refs)):
            if assigned[j] >= 0:
                continue
            other = refs[j]
            if point_distance(ref.x, ref.y, other.x, other.y) <= tol:
                assigned[j] = cluster_index
                members.append(other)
        clusters.append(EndpointCluster(cluster_id=cluster_index, members=members))
        cluster_index += 1
    return clusters


def segment_endpoint_angle_at_node(
    seg: WorkingSegment,
    node_x: float,
    node_y: float,
) -> float:
    d_start = point_distance(node_x, node_y, seg.start_x, seg.start_y)
    d_end = point_distance(node_x, node_y, seg.end_x, seg.end_y)
    if d_start <= d_end:
        return math.degrees(
            math.atan2(seg.end_y - seg.start_y, seg.end_x - seg.start_x)
        )
    return math.degrees(math.atan2(seg.start_y - seg.end_y, seg.start_x - seg.end_x))
