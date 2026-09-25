"""Typed artifacts for the transcribe_regions stage."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1.0"
PRODUCER_VERSION = "transcribe_regions@1.0.0"

CoordinateSpace = Literal["page"]
TextCandidateStatus = Literal["proposed", "unreadable", "unknown"]
AlternativeSource = Literal["ocr", "vocabulary"]
DimensionParseStatus = Literal["parsed", "ambiguous", "illegible", "none"]


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


class TextAlternative(_ArtifactModel):
    text: str
    score: float
    source: AlternativeSource


class ParsedDimensionHint(_ArtifactModel):
    value: float | None = None
    unit: str | None = None
    display_text: str
    confidence: float
    status: DimensionParseStatus


class NearbyTopologyRef(_ArtifactModel):
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    evidence: str = ""


class OcrModelInfo(_ArtifactModel):
    name: str
    revision: str | None = None
    preprocessing: dict[str, Any] = Field(default_factory=dict)


class TextCandidate(_ArtifactModel):
    id: str
    region_id: str
    region_kind: str
    bbox: PageBBox
    crop_uri: str
    rotation_deg: float
    raw_text: str | None = None
    normalized_text: str | None = None
    alternatives: list[TextAlternative] = Field(default_factory=list)
    parsed_dimension: ParsedDimensionHint | None = None
    status: TextCandidateStatus
    nearby_topology: NearbyTopologyRef = Field(default_factory=NearbyTopologyRef)
    ocr_confidence: float | None = None


class OcrReviewItem(_ArtifactModel):
    id: str
    code: str
    message: str
    text_candidate_id: str | None = None
    region_id: str | None = None
    bbox: PageBBox | None = None


class TextCandidatesMetadata(_ArtifactModel):
    schema_version: str = SCHEMA_VERSION
    producer_version: str = PRODUCER_VERSION
    profile_version: str
    page_width_px: int
    page_height_px: int
    coordinate_space: CoordinateSpace = "page"
    regions_metadata_uri: str
    topology_metadata_uri: str | None = None
    model: OcrModelInfo
    candidates: list[TextCandidate] = Field(default_factory=list)
    review_items: list[OcrReviewItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")
