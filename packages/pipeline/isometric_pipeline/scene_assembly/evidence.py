"""Build scene Evidence from page-space geometry."""

from __future__ import annotations

from collections.abc import Sequence

from isometric_pipeline.geometry.transforms import apply_mat3
from isometric_pipeline.scene.models import Evidence, ObservationValue, SourcePoint


def bbox_to_source_polygon(
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    page_to_source: Sequence[float],
) -> list[SourcePoint]:
    corners = (
        (x, y),
        (x + width, y),
        (x + width, y + height),
        (x, y + height),
    )
    return [
        SourcePoint(x=sx, y=sy)
        for px, py in corners
        for sx, sy in [apply_mat3(page_to_source, px, py)]
    ]


def page_point_to_source(
    x: float, y: float, page_to_source: Sequence[float]
) -> SourcePoint:
    sx, sy = apply_mat3(page_to_source, x, y)
    return SourcePoint(x=sx, y=sy)


def point_evidence_polygon(
    x: float,
    y: float,
    *,
    page_to_source: Sequence[float],
    radius: float = 4.0,
) -> list[SourcePoint]:
    return bbox_to_source_polygon(
        x=x - radius,
        y=y - radius,
        width=radius * 2,
        height=radius * 2,
        page_to_source=page_to_source,
    )


def machine_evidence(
    *,
    stage: str,
    artifact_id: str,
    source_polygon: list[SourcePoint],
    observations: dict[str, ObservationValue] | None = None,
) -> Evidence:
    return Evidence(
        stage=stage,
        artifact_id=artifact_id,
        source_polygon=source_polygon,
        observations=observations or {"confidence": 0.75},
    )
