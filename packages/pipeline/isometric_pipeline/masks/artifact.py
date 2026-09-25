"""Typed artifacts for the separate_masks stage."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1.0"
PRODUCER_VERSION = "separate_masks@1.0.0"

WARNING_GRID_LOW_CONFIDENCE = "grid_separation_low_confidence"

CoordinateSpace = Literal["page"]


class _ArtifactModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class MaskArtifactRef(_ArtifactModel):
    uri: str
    coordinate_space: CoordinateSpace = "page"
    width_px: int
    height_px: int
    media_type: str = "image/png"


class ColorLayerRecord(_ArtifactModel):
    layer_id: str
    mask_uri: str
    normalized_rgb: tuple[int, int, int]
    pixel_count: int


class GridDiagnostics(_ArtifactModel):
    grid_confidence: float
    paper_lightness: float
    grid_pixel_count: int
    retained_ink_pixel_count: int


class MasksMetadata(_ArtifactModel):
    schema_version: str = SCHEMA_VERSION
    producer_version: str = PRODUCER_VERSION
    page_width_px: int
    page_height_px: int
    page_hash: str
    coordinate_space: CoordinateSpace = "page"
    grid_mask: MaskArtifactRef
    retained_ink_mask: MaskArtifactRef
    black_ink_mask: MaskArtifactRef
    unclassified_ink_mask: MaskArtifactRef
    geometry_ink_mask: MaskArtifactRef
    protection_mask: MaskArtifactRef
    color_layers: list[ColorLayerRecord] = Field(default_factory=list)
    diagnostics: GridDiagnostics
    parameters: dict[str, float | int | bool]
    warnings: list[str]

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")
