"""Typed artifacts for the extract_centerlines stage."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1.0"
PRODUCER_VERSION = "extract_centerlines@1.0.0"

CoordinateSpace = Literal["page"]
ComponentStatus = Literal["accepted", "rejected_tiny", "rejected_spur"]
NodeKind = Literal["endpoint", "branch", "junction_pixel"]


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


class CenterlineComponent(_ArtifactModel):
    id: str
    layer_id: str
    status: ComponentStatus
    pixel_count: int
    bbox: PageBBox
    source_crop_uri: str | None = None


class RejectedComponent(_ArtifactModel):
    id: str
    layer_id: str
    status: ComponentStatus
    pixel_count: int
    bbox: PageBBox
    reason: str
    source_crop_uri: str | None = None


class CenterlineNode(_ArtifactModel):
    id: str
    component_id: str
    position: PagePoint
    kind: NodeKind


class CenterlineEdge(_ArtifactModel):
    id: str
    component_id: str
    layer_id: str
    samples: list[tuple[float, float]]
    start_node_id: str
    end_node_id: str


class CenterlineLayerRecord(_ArtifactModel):
    layer_id: str
    mask_uri: str
    component_count: int
    edge_count: int


class CenterlinesMetadata(_ArtifactModel):
    schema_version: str = SCHEMA_VERSION
    producer_version: str = PRODUCER_VERSION
    profile_version: str
    page_width_px: int
    page_height_px: int
    coordinate_space: CoordinateSpace = "page"
    masks_metadata_uri: str
    regions_metadata_uri: str | None = None
    layers: list[CenterlineLayerRecord] = Field(default_factory=list)
    components: list[CenterlineComponent] = Field(default_factory=list)
    rejected_components: list[RejectedComponent] = Field(default_factory=list)
    nodes: list[CenterlineNode] = Field(default_factory=list)
    edges: list[CenterlineEdge] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_wire(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")
