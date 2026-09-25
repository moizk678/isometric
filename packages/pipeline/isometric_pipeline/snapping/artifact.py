"""Typed artifacts for the snap_primitives stage."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

AXES_SCHEMA_VERSION = "1.0"
AXES_PRODUCER_VERSION = "snap_primitives@1.0.0"
SNAPPED_SCHEMA_VERSION = "1.0"
SNAPPED_PRODUCER_VERSION = "snap_primitives@1.0.0"

CoordinateSpace = Literal["page"]
AxisKind = Literal["vertical", "iso_a", "iso_b"]
AxisInferenceMethod = Literal[
    "primitive_histogram", "grid_assisted", "insufficient_evidence"
]
SnapStatus = Literal["snapped", "preserved", "skipped"]
DecisionReason = Literal[
    "snapped_to_axis",
    "weak_axis_model",
    "off_axis",
    "endpoint_displacement",
    "residual_too_high",
    "dimension_region",
    "low_evidence",
    "preserved_uncertain",
]


class _ArtifactModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class PagePoint(_ArtifactModel):
    x: float
    y: float


class SegmentGeom(_ArtifactModel):
    start: PagePoint
    end: PagePoint


class EndpointAdjustment(_ArtifactModel):
    original: PagePoint
    adjusted: PagePoint
    displacement_px: float


class AxisRecord(_ArtifactModel):
    id: str
    kind: AxisKind
    angle_deg: float
    weight: float
    confidence: float


class AxesMetadata(_ArtifactModel):
    schema_version: str = AXES_SCHEMA_VERSION
    producer_version: str = AXES_PRODUCER_VERSION
    profile_version: str
    page_width_px: int
    page_height_px: int
    coordinate_space: CoordinateSpace = "page"
    primitives_metadata_uri: str
    masks_metadata_uri: str | None = None
    inference_method: AxisInferenceMethod
    rotation_deg: float
    axes: list[AxisRecord] = Field(default_factory=list)
    model_confidence: float
    grid_confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")


class SnappedPrimitiveCandidate(_ArtifactModel):
    primitive_id: str
    layer_id: str
    status: SnapStatus
    pre_snap: SegmentGeom
    post_snap: SegmentGeom
    axis_id: str | None = None
    angle_delta_deg: float
    max_endpoint_displacement_px: float
    residual_rms_px: float
    decision_reason: DecisionReason
    reason: str
    evidence: str
    endpoint_adjustments: list[EndpointAdjustment] = Field(default_factory=list)


class SnappedPrimitivesMetadata(_ArtifactModel):
    schema_version: str = SNAPPED_SCHEMA_VERSION
    producer_version: str = SNAPPED_PRODUCER_VERSION
    profile_version: str
    page_width_px: int
    page_height_px: int
    coordinate_space: CoordinateSpace = "page"
    primitives_metadata_uri: str
    axes_metadata_uri: str
    regions_metadata_uri: str | None = None
    candidates: list[SnappedPrimitiveCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")
