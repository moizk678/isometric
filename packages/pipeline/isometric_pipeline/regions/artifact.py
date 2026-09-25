"""Typed artifacts for the detect_regions stage."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1.0"
PRODUCER_VERSION = "detect_regions@1.0.0"

RegionKind = Literal["text", "symbol", "arrow", "dimension"]
CoordinateSpace = Literal["page"]


class _ArtifactModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class PageBBox(_ArtifactModel):
    x: float
    y: float
    width: float
    height: float


class RegionCandidate(_ArtifactModel):
    id: str
    kind: RegionKind
    bbox: PageBBox
    score: float
    crop_uri: str
    evidence: str


class RegionsMetadata(_ArtifactModel):
    schema_version: str = SCHEMA_VERSION
    producer_version: str = PRODUCER_VERSION
    page_width_px: int
    page_height_px: int
    coordinate_space: CoordinateSpace = "page"
    masks_metadata_uri: str
    regions: list[RegionCandidate] = Field(default_factory=list)
    protection_mask_uri: str
    geometry_ink_mask_uri: str
    warnings: list[str]

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")
