"""EXIF orientation frame and source/display transforms."""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import ExifTags, Image, ImageOps

from isometric_pipeline.geometry.transforms import Matrix, apply_mat3

_ORIENTATION_MAPS: dict[int, tuple[int, int, str, int, int, str]] = {
    1: (1, 0, "0", 0, 1, "0"),
    2: (-1, 0, "W", 0, 1, "0"),
    3: (-1, 0, "W", 0, -1, "H"),
    4: (1, 0, "0", 0, -1, "H"),
    5: (0, 1, "0", 1, 0, "0"),
    6: (0, -1, "H", 1, 0, "0"),
    7: (0, -1, "H", -1, 0, "W"),
    8: (0, 1, "0", -1, 0, "W"),
}


@dataclass(frozen=True)
class SourceFrame:
    orientation: int
    source_width_px: int
    source_height_px: int
    display_width_px: int
    display_height_px: int
    source_to_display: Matrix
    display_to_source: Matrix


def orientation_matrices(
    orientation: int, source_width_px: int, source_height_px: int
) -> tuple[Matrix, Matrix]:
    """Return row-major (sourceToDisplay, displayToSource) for an EXIF orientation."""
    a, b, c_sym, d, e, f_sym = _ORIENTATION_MAPS.get(orientation, _ORIENTATION_MAPS[1])
    sizes = {"0": 0, "W": source_width_px, "H": source_height_px}
    c, f = sizes[c_sym], sizes[f_sym]
    forward = [a, b, c, d, e, f, 0, 0, 1]
    inverse = [
        a,
        d,
        -(a * c + d * f),
        b,
        e,
        -(b * c + e * f),
        0,
        0,
        1,
    ]
    return [float(v) for v in forward], [float(v) for v in inverse]


def read_source_frame(data: bytes) -> SourceFrame:
    with Image.open(io.BytesIO(data)) as image:
        source_width, source_height = image.size
        raw_orientation = image.getexif().get(ExifTags.Base.Orientation, 1)
        displayed = ImageOps.exif_transpose(image)
        assert displayed is not None
        display_width, display_height = displayed.size
    orientation = (
        raw_orientation
        if isinstance(raw_orientation, int) and raw_orientation in _ORIENTATION_MAPS
        else 1
    )
    source_to_display, display_to_source = orientation_matrices(
        orientation, source_width, source_height
    )
    mapped = _display_size_for(source_to_display, source_width, source_height)
    if mapped != (display_width, display_height):
        raise ValueError(
            f"EXIF orientation {orientation} maps {source_width}x{source_height} to "
            f"{mapped[0]}x{mapped[1]}, but exif_transpose produced "
            f"{display_width}x{display_height}"
        )
    return SourceFrame(
        orientation=orientation,
        source_width_px=source_width,
        source_height_px=source_height,
        display_width_px=display_width,
        display_height_px=display_height,
        source_to_display=source_to_display,
        display_to_source=display_to_source,
    )


def _display_size_for(
    source_to_display: Matrix, width: int, height: int
) -> tuple[int, int]:
    corners = [
        apply_mat3(source_to_display, x, y) for x, y in ((0, 0), (width, height))
    ]
    return (
        round(abs(corners[1][0] - corners[0][0])),
        round(abs(corners[1][1] - corners[0][1])),
    )
