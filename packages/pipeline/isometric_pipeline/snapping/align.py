"""Post-snap endpoint alignment without topology."""

from __future__ import annotations

import math

from isometric_pipeline.profiles.loader import SnappingProfile
from isometric_pipeline.snapping.artifact import (
    EndpointAdjustment,
    PagePoint,
    SegmentGeom,
    SnappedPrimitiveCandidate,
)
from isometric_pipeline.snapping.snap import endpoint_displacement_px


def _union_find_parent(parent: list[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def _union(parent: list[int], a: int, b: int) -> None:
    ra, rb = _union_find_parent(parent, a), _union_find_parent(parent, b)
    if ra != rb:
        parent[rb] = ra


def align_snapped_endpoints(
    candidates: list[SnappedPrimitiveCandidate],
    profile: SnappingProfile,
) -> list[SnappedPrimitiveCandidate]:
    tol = profile.endpoint_align_tolerance_px
    if tol <= 0:
        return candidates

    snapped = [c for c in candidates if c.status == "snapped"]
    if len(snapped) < 2:
        return candidates

    endpoints: list[tuple[int, str, PagePoint]] = []
    for idx, cand in enumerate(snapped):
        endpoints.append((idx, "start", cand.post_snap.start))
        endpoints.append((idx, "end", cand.post_snap.end))

    n = len(endpoints)
    parent = list(range(n))
    tol_sq = tol * tol
    for i in range(n):
        pi = endpoints[i][2]
        for j in range(i + 1, n):
            pj = endpoints[j][2]
            dx = pi.x - pj.x
            dy = pi.y - pj.y
            if dx * dx + dy * dy <= tol_sq:
                _union(parent, i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        root = _union_find_parent(parent, i)
        clusters.setdefault(root, []).append(i)

    centroid_by_root: dict[int, PagePoint] = {}
    for root, members in clusters.items():
        if len(members) < 2:
            continue
        cx = sum(endpoints[m][2].x for m in members) / len(members)
        cy = sum(endpoints[m][2].y for m in members) / len(members)
        centroid_by_root[root] = PagePoint(x=cx, y=cy)

    if not centroid_by_root:
        return candidates

    updated: dict[str, SnappedPrimitiveCandidate] = {c.primitive_id: c for c in candidates}

    for root, members in clusters.items():
        target = centroid_by_root.get(root)
        if target is None:
            continue
        for point_idx in members:
            cand_idx, end_name, original = endpoints[point_idx]
            cand = snapped[cand_idx]
            disp = math.hypot(target.x - original.x, target.y - original.y)
            if disp < 1e-3:
                continue
            adj = EndpointAdjustment(
                original=PagePoint(x=original.x, y=original.y),
                adjusted=PagePoint(x=target.x, y=target.y),
                displacement_px=disp,
            )
            current = updated[cand.primitive_id]
            start = current.post_snap.start
            end = current.post_snap.end
            adjustments = list(current.endpoint_adjustments)
            adjustments.append(adj)
            if end_name == "start":
                start = PagePoint(x=target.x, y=target.y)
            else:
                end = PagePoint(x=target.x, y=target.y)
            post = SegmentGeom(start=start, end=end)
            new_max = endpoint_displacement_px(current.pre_snap, post)
            updated[cand.primitive_id] = current.model_copy(
                update={
                    "post_snap": post,
                    "endpoint_adjustments": adjustments,
                    "max_endpoint_displacement_px": new_max,
                }
            )

    return [updated.get(c.primitive_id, c) for c in candidates]
