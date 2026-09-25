"""Typed artifacts for the associate_markup stage."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from isometric_pipeline.ocr.artifact import ParsedDimensionHint

SCHEMA_VERSION = "1.0"
PRODUCER_VERSION = "associate_markup@1.0.0"

CoordinateSpace = Literal["page"]
CandidateStatus = Literal["proposed", "unresolved"]
InterpretationState = Literal["proposed", "unresolved", "rejected"]
RelationshipType = Literal["measures", "annotates", "callout_targets"]
TargetRefKind = Literal["topology_edge", "topology_node", "symbol_candidate"]


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


class LineSegment(_ArtifactModel):
    start: PagePoint
    end: PagePoint


class DimensionGeometryCandidate(_ArtifactModel):
    id: str
    witness_line: LineSegment
    extension_lines: list[LineSegment] = Field(default_factory=list)
    arrowhead_points: list[PagePoint] = Field(default_factory=list)
    arrow_region_ids: list[str] = Field(default_factory=list)
    evidence: str = ""


class TargetRef(_ArtifactModel):
    ref_kind: TargetRefKind
    ref_id: str
    score: float


class DimensionCandidate(_ArtifactModel):
    id: str
    text_candidate_id: str
    region_id: str
    display_text: str
    parsed_dimension: ParsedDimensionHint | None = None
    witness_start: PagePoint
    witness_end: PagePoint
    geometry_candidate_id: str | None = None
    target_refs: list[TargetRef] = Field(default_factory=list)
    status: CandidateStatus = "proposed"


class AnnotationAlternative(_ArtifactModel):
    ref_kind: TargetRefKind
    ref_id: str
    score: float
    evidence: str = ""


class AnnotationTargetCandidate(_ArtifactModel):
    id: str
    text_candidate_id: str
    region_id: str
    leader_polyline: list[PagePoint] = Field(default_factory=list)
    arrow_region_id: str | None = None
    alternatives: list[AnnotationAlternative] = Field(default_factory=list)
    status: CandidateStatus = "proposed"


class RelationshipCandidate(_ArtifactModel):
    id: str
    type: RelationshipType
    from_candidate_id: str
    to_ref_kind: TargetRefKind
    to_ref_id: str
    interpretation: InterpretationState
    evidence: str


class AssociationReviewItem(_ArtifactModel):
    id: str
    code: str
    message: str
    dimension_candidate_id: str | None = None
    annotation_candidate_id: str | None = None
    text_candidate_id: str | None = None
    bbox: PageBBox | None = None


class AssociationCandidatesMetadata(_ArtifactModel):
    schema_version: str = SCHEMA_VERSION
    producer_version: str = PRODUCER_VERSION
    profile_version: str
    page_width_px: int
    page_height_px: int
    coordinate_space: CoordinateSpace = "page"
    regions_metadata_uri: str
    masks_metadata_uri: str | None = None
    topology_metadata_uri: str | None = None
    text_candidates_metadata_uri: str | None = None
    symbol_candidates_metadata_uri: str | None = None
    dimension_geometry: list[DimensionGeometryCandidate] = Field(default_factory=list)
    dimension_candidates: list[DimensionCandidate] = Field(default_factory=list)
    annotation_targets: list[AnnotationTargetCandidate] = Field(default_factory=list)
    relationships: list[RelationshipCandidate] = Field(default_factory=list)
    review_items: list[AssociationReviewItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")
