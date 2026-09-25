"""Centerline graph extraction from skeleton masks."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from isometric_pipeline.centerlines.artifact import (
    CenterlineComponent,
    CenterlineEdge,
    CenterlineNode,
    NodeKind,
    PageBBox,
    PagePoint,
    RejectedComponent,
)
from isometric_pipeline.profiles.loader import GeometryProfile


@dataclass(frozen=True)
class LayerGraphResult:
    components: list[CenterlineComponent]
    rejected: list[RejectedComponent]
    nodes: list[CenterlineNode]
    edges: list[CenterlineEdge]


def extract_layer_graph(
    mask: np.ndarray,
    skeleton: np.ndarray,
    *,
    layer_id: str,
    profile: GeometryProfile,
    crops_prefix: str,
    id_prefix: str,
) -> LayerGraphResult:
    components: list[CenterlineComponent] = []
    rejected: list[RejectedComponent] = []
    nodes: list[CenterlineNode] = []
    edges: list[CenterlineEdge] = []

    binary = (mask > 0).astype(np.uint8)
    skel = (skeleton > 0).astype(np.uint8)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    comp_index = 0
    node_index = 0
    edge_index = 0

    for label in range(1, num_labels):
        pixel_count = int(stats[label, cv2.CC_STAT_AREA])
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        w = int(stats[label, cv2.CC_STAT_WIDTH])
        h = int(stats[label, cv2.CC_STAT_HEIGHT])
        bbox = PageBBox(x=float(x), y=float(y), width=float(w), height=float(h))
        comp_id = f"{id_prefix}_cmp_{comp_index:04d}"
        comp_index += 1

        if pixel_count < profile.min_component_pixels:
            rejected.append(
                RejectedComponent(
                    id=comp_id,
                    layer_id=layer_id,
                    status="rejected_tiny",
                    pixel_count=pixel_count,
                    bbox=bbox,
                    reason="below_min_component_pixels",
                    source_crop_uri=f"{crops_prefix}/{comp_id}.png",
                )
            )
            continue

        comp_mask = labels == label
        comp_skel = skel & comp_mask.astype(np.uint8)
        if not np.any(comp_skel):
            rejected.append(
                RejectedComponent(
                    id=comp_id,
                    layer_id=layer_id,
                    status="rejected_spur",
                    pixel_count=pixel_count,
                    bbox=bbox,
                    reason="empty_skeleton",
                    source_crop_uri=f"{crops_prefix}/{comp_id}.png",
                )
            )
            continue

        components.append(
            CenterlineComponent(
                id=comp_id,
                layer_id=layer_id,
                status="accepted",
                pixel_count=pixel_count,
                bbox=bbox,
                source_crop_uri=f"{crops_prefix}/{comp_id}.png",
            )
        )

        junctions = _junction_pixels(comp_skel)
        polylines = _trace_polylines(comp_skel, junctions)
        node_ids_by_key: dict[tuple[int, int], str] = {}

        for poly in polylines:
            if len(poly) < 2:
                continue
            start_y, start_x = poly[0]
            end_y, end_x = poly[-1]
            start_kind: NodeKind = (
                "branch" if (start_y, start_x) in junctions else "endpoint"
            )
            end_kind: NodeKind = "branch" if (end_y, end_x) in junctions else "endpoint"
            start_id, node_index = _ensure_node(
                nodes,
                node_ids_by_key,
                id_prefix,
                comp_id,
                start_y,
                start_x,
                start_kind,
                node_index,
            )
            end_id, node_index = _ensure_node(
                nodes,
                node_ids_by_key,
                id_prefix,
                comp_id,
                end_y,
                end_x,
                end_kind,
                node_index,
            )
            edge_id = f"{id_prefix}_edge_{edge_index:04d}"
            edge_index += 1
            samples = [(float(px), float(py)) for py, px in poly]
            edges.append(
                CenterlineEdge(
                    id=edge_id,
                    component_id=comp_id,
                    layer_id=layer_id,
                    samples=samples,
                    start_node_id=start_id,
                    end_node_id=end_id,
                )
            )

    return LayerGraphResult(
        components=components,
        rejected=rejected,
        nodes=nodes,
        edges=edges,
    )


def _junction_pixels(skel: np.ndarray) -> set[tuple[int, int]]:
    ys, xs = np.where(skel > 0)
    junctions: set[tuple[int, int]] = set()
    for y, x in zip(ys.tolist(), xs.tolist(), strict=True):
        if _degree(skel, y, x) >= 3:
            junctions.add((y, x))
    return junctions


def _degree(skel: np.ndarray, y: int, x: int) -> int:
    count = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            ny, nx = y + dy, x + dx
            if 0 <= ny < skel.shape[0] and 0 <= nx < skel.shape[1] and skel[ny, nx]:
                count += 1
    return count


def _trace_polylines(
    skel: np.ndarray, junctions: set[tuple[int, int]]
) -> list[list[tuple[int, int]]]:
    height, width = skel.shape
    visited_edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    polylines: list[list[tuple[int, int]]] = []

    def neighbors(y: int, x: int) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width and skel[ny, nx]:
                    out.append((ny, nx))
        return out

    seeds: list[tuple[int, int]] = []
    for j in junctions:
        seeds.append(j)
    ys, xs = np.where(skel > 0)
    for y, x in zip(ys.tolist(), xs.tolist(), strict=True):
        if _degree(skel, y, x) == 1:
            seeds.append((y, x))

    for seed in seeds:
        for nxt in neighbors(seed[0], seed[1]):
            edge_key = _ordered_edge(seed, nxt)
            if edge_key in visited_edges:
                continue
            poly = [seed]
            prev = seed
            current = nxt
            while True:
                visited_edges.add(_ordered_edge(prev, current))
                poly.append(current)
                if current in junctions and current != seed:
                    break
                nbrs = [p for p in neighbors(current[0], current[1]) if p != prev]
                if not nbrs:
                    break
                if len(nbrs) > 1:
                    break
                prev, current = current, nbrs[0]
                if _ordered_edge(prev, current) in visited_edges:
                    break
            if len(poly) >= 2:
                polylines.append(poly)

    if not polylines and np.any(skel):
        ys, xs = np.where(skel > 0)
        poly = [(int(y), int(x)) for y, x in zip(ys.tolist(), xs.tolist(), strict=True)]
        if len(poly) >= 2:
            polylines.append(poly)

    return polylines


def _ordered_edge(
    a: tuple[int, int], b: tuple[int, int]
) -> tuple[tuple[int, int], tuple[int, int]]:
    return (a, b) if a <= b else (b, a)


def _ensure_node(
    nodes: list[CenterlineNode],
    node_ids_by_key: dict[tuple[int, int], str],
    id_prefix: str,
    comp_id: str,
    py: int,
    px: int,
    kind: NodeKind,
    node_index: int,
) -> tuple[str, int]:
    key = (py, px)
    existing = node_ids_by_key.get(key)
    if existing is not None:
        return existing, node_index
    node_id = f"{id_prefix}_node_{node_index:04d}"
    node_index += 1
    node_ids_by_key[key] = node_id
    nodes.append(
        CenterlineNode(
            id=node_id,
            component_id=comp_id,
            position=PagePoint(x=float(px), y=float(py)),
            kind=kind,
        )
    )
    return node_id, node_index
