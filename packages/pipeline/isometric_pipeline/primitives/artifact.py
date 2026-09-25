"""Typed artifacts for the fit_primitives stage."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1.0"
PRODUCER_VERSION = "fit_primitives@1.0.0"

CoordinateSpace = Literal["page"]
PrimitiveKind = Literal["line"]
PrimitiveStatus = Literal["accepted", "uncertain", "rejected"]


class _ArtifactModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class PagePoint(_ArtifactModel):
    x: float
    y: float


class PageBBox(_ArtifactModel):
    x: float
    y: float
    width: float
    height: float


class PrimitiveCandidate(_ArtifactModel):
    id: str
    layer_id: str
    kind: PrimitiveKind
    start: PagePoint
    end: PagePoint
    samples: list[tuple[float, float]]
    residual_rms_px: float
    stroke_width_px: float
    fit_metric: float
    confidence: float
    status: PrimitiveStatus
    centerline_edge_id: str
    component_id: str
    mask_uri: str
    evidence: str


class UnresolvedEvidence(_ArtifactModel):
    id: str
    layer_id: str
    component_id: str
    centerline_edge_id: str
    samples: list[tuple[float, float]]
    bbox: PageBBox
    evidence: str


class PrimitiveRejection(_ArtifactModel):
    id: str
    centerline_edge_id: str
    component_id: str
    reason: str
    diagnostic_index: int


class PrimitivesMetadata(_ArtifactModel):
    schema_version: str = SCHEMA_VERSION
    producer_version: str = PRODUCER_VERSION
    profile_version: str
    page_width_px: int
    page_height_px: int
    coordinate_space: CoordinateSpace = "page"
    centerlines_metadata_uri: str
    masks_metadata_uri: str
    regions_metadata_uri: str | None = None
    primitives: list[PrimitiveCandidate] = Field(default_factory=list)
    unresolved: list[UnresolvedEvidence] = Field(default_factory=list)
    rejections: list[PrimitiveRejection] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")
