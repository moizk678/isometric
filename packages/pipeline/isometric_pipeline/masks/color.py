"""Color layer clustering on retained ink."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

BLACK_CHROMA_MAX = 22.0
MIN_LAYER_PIXELS = 40
KMEANS_ATTEMPTS = 3
KMEANS_SEED = 42


@dataclass(frozen=True)
class ColorSeparation:
    color_layers: list[tuple[str, np.ndarray, tuple[int, int, int]]]
    black_ink_mask: np.ndarray
    unclassified_ink_mask: np.ndarray


def separate_color_layers(
    rgb: np.ndarray,
    retained_ink_mask: np.ndarray,
) -> ColorSeparation:
    height, width = retained_ink_mask.shape
    empty = np.zeros((height, width), dtype=np.uint8)
    ink = retained_ink_mask > 0
    if not np.any(ink):
        return ColorSeparation([], empty, empty)

    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    a = lab[:, :, 1].astype(np.float32) - 128.0
    b = lab[:, :, 2].astype(np.float32) - 128.0
    chroma = np.sqrt(a * a + b * b)
    black = ink & (chroma < BLACK_CHROMA_MAX)
    black_mask = (black.astype(np.uint8)) * 255

    colored = ink & ~black
    colored_count = int(np.count_nonzero(colored))
    layers: list[tuple[str, np.ndarray, tuple[int, int, int]]] = []
    assigned = np.zeros((height, width), dtype=bool)

    if colored_count >= MIN_LAYER_PIXELS:
        coords = np.column_stack(np.where(colored))
        samples = lab[colored].astype(np.float32)
        k = min(4, max(2, colored_count // MIN_LAYER_PIXELS))
        if k >= 2 and samples.shape[0] >= k:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
            cv2.setRNGSeed(KMEANS_SEED)
            _, labels, centers = cv2.kmeans(
                samples,
                k,
                None,
                criteria,
                KMEANS_ATTEMPTS,
                cv2.KMEANS_PP_CENTERS,
            )
            candidates: list[
                tuple[tuple[float, float, float], np.ndarray, tuple[int, int, int]]
            ] = []
            for index in range(k):
                layer_pixels = labels.reshape(-1) == index
                if int(np.count_nonzero(layer_pixels)) < MIN_LAYER_PIXELS:
                    continue
                mask = np.zeros((height, width), dtype=np.uint8)
                ys = coords[layer_pixels, 0]
                xs = coords[layer_pixels, 1]
                mask[ys, xs] = 255
                center = centers[index]
                rgb_center = _lab_center_to_rgb(center)
                sort_key = (
                    float(center[0]),
                    float(center[1]),
                    float(center[2]),
                )
                candidates.append((sort_key, mask, rgb_center))
                assigned[ys, xs] = True
            candidates.sort(key=lambda item: item[0])
            for rank, (_, mask, rgb_center) in enumerate(candidates, start=1):
                layers.append((f"color_{rank}", mask, rgb_center))

    unclassified = ink & ~black & ~assigned
    unclassified_mask = (unclassified.astype(np.uint8)) * 255
    return ColorSeparation(layers, black_mask, unclassified_mask)


def _lab_center_to_rgb(center: np.ndarray) -> tuple[int, int, int]:
    patch = np.array([[center]], dtype=np.uint8)
    rgb = cv2.cvtColor(patch, cv2.COLOR_LAB2RGB)[0, 0]
    return int(rgb[0]), int(rgb[1]), int(rgb[2])
