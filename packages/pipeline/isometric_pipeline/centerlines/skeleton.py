"""Mask cleanup and skeletonization."""

from __future__ import annotations

import cv2
import numpy as np

from isometric_pipeline.profiles.loader import GeometryProfile


def clean_mask(mask: np.ndarray, profile: GeometryProfile) -> np.ndarray:
    binary = (mask > 0).astype(np.uint8) * 255
    k_open = max(1, profile.morph_open_kernel_px)
    k_close = max(1, profile.morph_close_kernel_px)
    element_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_open, k_open))
    element_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_close, k_close))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, element_open)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, element_close)
    return closed


def skeletonize(mask: np.ndarray) -> np.ndarray:
    """Thin ink to a 1-pixel centerline.

    A cross-shaped morphological skeleton leaves a 2-pixel diagonal as a braid,
    and the centerline graph then splits that braid into 1-pixel edges.
    Guo-Hall thinning reduces those ribbons to a single path.
    """
    img = (mask > 0).astype(np.uint8)
    if not np.any(img):
        return np.zeros(mask.shape, dtype=np.uint8)
    while True:
        changed = False
        for phase in (0, 1):
            padded = np.pad(img, 1, mode="constant")
            p2 = padded[:-2, 1:-1]
            p3 = padded[:-2, 2:]
            p4 = padded[1:-1, 2:]
            p5 = padded[2:, 2:]
            p6 = padded[2:, 1:-1]
            p7 = padded[2:, :-2]
            p8 = padded[1:-1, :-2]
            p9 = padded[:-2, :-2]
            connected = (
                ((1 - p2) & (p3 | p4))
                + ((1 - p4) & (p5 | p6))
                + ((1 - p6) & (p7 | p8))
                + ((1 - p8) & (p9 | p2))
            )
            north = (p9 | p2) + (p3 | p4) + (p5 | p6) + (p7 | p8)
            south = (p2 | p3) + (p4 | p5) + (p6 | p7) + (p8 | p9)
            neighbor_count = np.minimum(north, south)
            if phase == 0:
                marker = (p6 | p7 | (1 - p9)) & p8
            else:
                marker = (p2 | p3 | (1 - p5)) & p4
            remove = (
                (img == 1)
                & (connected == 1)
                & (neighbor_count >= 2)
                & (neighbor_count <= 3)
                & (marker == 0)
            )
            if np.any(remove):
                changed = True
                img[remove] = 0
        if not changed:
            break
    return img * 255


def prune_spurs(skeleton: np.ndarray, max_spur_length: int) -> np.ndarray:
    if max_spur_length <= 0 or not np.any(skeleton):
        return skeleton
    skel = (skeleton > 0).astype(np.uint8)
    height, width = skel.shape
    for _ in range(max_spur_length):
        endpoints = _endpoint_pixels(skel)
        if endpoints.size == 0:
            break
        removed = False
        for y, x in endpoints:
            if _neighbor_count(skel, y, x) != 1:
                continue
            skel[y, x] = 0
            removed = True
        if not removed:
            break
    return skel * 255


def _neighbor_count(skel: np.ndarray, y: int, x: int) -> int:
    height, width = skel.shape
    count = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            ny, nx = y + dy, x + dx
            if 0 <= ny < height and 0 <= nx < width and skel[ny, nx]:
                count += 1
    return count


def _endpoint_pixels(skel: np.ndarray) -> np.ndarray:
    ys, xs = np.where(skel > 0)
    points: list[tuple[int, int]] = []
    for y, x in zip(ys.tolist(), xs.tolist(), strict=True):
        if _neighbor_count(skel, y, x) == 1:
            points.append((y, x))
    if not points:
        return np.zeros((0, 2), dtype=np.int32)
    return np.array(points, dtype=np.int32)
