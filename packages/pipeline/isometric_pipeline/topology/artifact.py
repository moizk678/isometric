"""Typed artifacts for the infer_topology stage."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1.0"
PRODUCER_VERSION = "infer_topology@1.0.0"

CoordinateSpace = Literal["page"]
NodeKind = Literal["endpoint", "elbow", "tee", "crossing", "unknown"]
NodeStatus = Literal["proposed", "confirmed_structure"]


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


class EvidenceScores(_ArtifactModel):
    distance: float = 0.0
    angle: float = 0.0
    color: float = 0.0
    continuity: float = 0.0
    symbol_protection: float = 0.0


class NodeCandidate(_ArtifactModel):
    id: str
    position: PagePoint
    kind: NodeKind
    status: NodeStatus
    layer_ids: list[str] = Field(default_factory=list)
    source_evidence: str
    hypothesis_group_id: str | None = None


class EdgeCandidate(_ArtifactModel):
    id: str
    start_node_id: str
    end_node_id: str
    layer_id: str
    start: PagePoint
    end: PagePoint
    source_primitive_ids: list[str] = Field(default_factory=list)
    component_ids: list[str] = Field(default_factory=list)
    scores: EvidenceScores = Field(default_factory=EvidenceScores)


class HypothesisAlternative(_ArtifactModel):
    id: str
    label: str
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    score: float


class IntersectionHypothesis(_ArtifactModel):
    id: str
    position: PagePoint
    segment_ids: list[str] = Field(default_factory=list)
    alternatives: list[HypothesisAlternative] = Field(default_factory=list)
    recommended_alternative_id: str | None = None


class TopologyReviewItem(_ArtifactModel):
    id: str
    code: str
    message: str
    hypothesis_group_id: str | None = None
    bbox: PageBBox | None = None
    related_node_ids: list[str] = Field(default_factory=list)
    related_edge_ids: list[str] = Field(default_factory=list)


class TopologyMetadata(_ArtifactModel):
    schema_version: str = SCHEMA_VERSION
    producer_version: str = PRODUCER_VERSION
    profile_version: str
    page_width_px: int
    page_height_px: int
    coordinate_space: CoordinateSpace = "page"
    snapped_primitives_metadata_uri: str
    primitives_metadata_uri: str
    regions_metadata_uri: str | None = None
    masks_metadata_uri: str | None = None
    nodes: list[NodeCandidate] = Field(default_factory=list)
    edges: list[EdgeCandidate] = Field(default_factory=list)
    hypotheses: list[IntersectionHypothesis] = Field(default_factory=list)
    review_items: list[TopologyReviewItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")
