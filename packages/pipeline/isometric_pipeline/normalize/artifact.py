"""Typed artifacts for the normalize_page stage."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1.0"
PRODUCER_VERSION = "normalize_page@1.0.0"

WARNING_PAGE_BOUNDARY_LOW = "page_boundary_low_confidence"

CoordinateSpace = Literal["source", "display", "page"]


class _ArtifactModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class RasterArtifactRef(_ArtifactModel):
    uri: str
    coordinate_space: CoordinateSpace
    width_px: int
    height_px: int
    media_type: str


class NormalizeDiagnostics(_ArtifactModel):
    blur_score: float
    contrast: float
    shadow_heavy: bool
    boundary_confidence: float
    rectified: bool


class NormalizePageMetadata(_ArtifactModel):
    schema_version: str = SCHEMA_VERSION
    producer_version: str = PRODUCER_VERSION
    source_width_px: int
    source_height_px: int
    display_width_px: int
    display_height_px: int
    page_width_px: int
    page_height_px: int
    orientation: int
    source_to_display: list[float]
    display_to_source: list[float]
    display_to_page: list[float]
    page_to_display: list[float]
    source_to_page: list[float]
    page_to_source: list[float]
    display_artifact: RasterArtifactRef
    page_artifact: RasterArtifactRef
    display_hash: str
    page_hash: str
    diagnostics: NormalizeDiagnostics
    warnings: list[str]

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")
