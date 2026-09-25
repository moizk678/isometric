"""Typed artifacts for the classify_symbol_regions stage."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1.0"
PRODUCER_VERSION = "classify_symbol_regions@1.0.0"

CoordinateSpace = Literal["page"]
SymbolCandidateStatus = Literal["proposed", "unknown", "unreadable"]


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


class PagePoint(_ArtifactModel):
    x: float
    y: float


class SymbolLabelAlternative(_ArtifactModel):
    symbol_id: str
    shape_score: float
    text_score: float
    topology_score: float


class ProposedPortAttachment(_ArtifactModel):
    port_name: str
    node_id: str | None = None


class NearbyTopologyRef(_ArtifactModel):
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    evidence: str = ""


class SymbolCandidate(_ArtifactModel):
    id: str
    region_id: str
    region_kind: str
    bbox: PageBBox
    crop_uri: str
    anchor: PagePoint
    rotation_deg: float
    status: SymbolCandidateStatus
    alternatives: list[SymbolLabelAlternative] = Field(default_factory=list)
    proposed_port_attachments: list[ProposedPortAttachment] = Field(
        default_factory=list
    )
    nearby_text_candidate_ids: list[str] = Field(default_factory=list)
    nearby_topology: NearbyTopologyRef = Field(default_factory=NearbyTopologyRef)


class SymbolReviewItem(_ArtifactModel):
    id: str
    code: str
    message: str
    symbol_candidate_id: str | None = None
    region_id: str | None = None
    bbox: PageBBox | None = None


class ClassifierInfo(_ArtifactModel):
    backend: str
    version: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class SymbolCandidatesMetadata(_ArtifactModel):
    schema_version: str = SCHEMA_VERSION
    producer_version: str = PRODUCER_VERSION
    profile_version: str
    page_width_px: int
    page_height_px: int
    coordinate_space: CoordinateSpace = "page"
    regions_metadata_uri: str
    topology_metadata_uri: str | None = None
    text_candidates_metadata_uri: str | None = None
    symbol_library_version: str
    classifier: ClassifierInfo
    candidates: list[SymbolCandidate] = Field(default_factory=list)
    review_items: list[SymbolReviewItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")
