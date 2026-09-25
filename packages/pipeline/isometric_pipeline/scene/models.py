"""Pydantic models for the DrawingScene v1 wire format.

These models enforce every rule a JSON Schema can express. Rules that span
objects (reference integrity, bounds, transform inverses, connectivity) live
in ``validation.py``.
"""

from __future__ import annotations

from typing import Annotated, Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from pydantic.alias_generators import to_camel
from pydantic.json_schema import SkipJsonSchema

SCENE_SCHEMA_VERSION: Final = "1.0"

UUID_PATTERN: Final = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
SCHEMA_VERSION_PATTERN: Final = r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
COLOR_PATTERN: Final = r"^#[0-9a-f]{6}$"

SceneId = Annotated[str, StringConstraints(pattern=UUID_PATTERN)]
NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
PositiveInt = Annotated[int, Field(gt=0)]
Color = Annotated[str, StringConstraints(pattern=COLOR_PATTERN)]
Transform3x3 = Annotated[list[FiniteFloat], Field(min_length=9, max_length=9)]
ObservationValue = bool | int | FiniteFloat | str


def _drop_default(schema: dict[str, Any]) -> None:
    schema.pop("default", None)


def _drop_property_titles(schema: dict[str, Any]) -> None:
    """Keep json2ts from emitting a named alias for every titled property."""
    for prop in schema.get("properties", {}).values():
        prop.pop("title", None)


def _omittable() -> Any:
    """Field that may be absent on the wire but is never JSON ``null``."""
    return Field(default=None, json_schema_extra=_drop_default)


def _reject_explicit_null(value: Any) -> Any:
    if value is None:
        raise ValueError("field may be omitted but must not be null")
    return value


class _SceneModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        strict=True,
        json_schema_extra=_drop_property_titles,
    )


class _XYPoint(_SceneModel):
    x: FiniteFloat
    y: FiniteFloat


class PagePoint(_XYPoint):
    """A point in rectified page pixels."""


class SourcePoint(_XYPoint):
    """A point in immutable input pixels, before EXIF orientation."""


class Page(_SceneModel):
    """Source, display, and page sizes with row-major 3x3 transforms."""

    source_width_px: PositiveInt
    source_height_px: PositiveInt
    display_width_px: PositiveInt
    display_height_px: PositiveInt
    width_px: PositiveInt
    height_px: PositiveInt
    source_to_display: Transform3x3
    display_to_source: Transform3x3
    source_to_page: Transform3x3
    page_to_source: Transform3x3


class Layer(_SceneModel):
    """A drawing layer with its source and render colors."""

    id: SceneId
    name: str
    source_color: Color
    render_color: Color


class Evidence(_SceneModel):
    """Source-image support for an interpretation."""

    source_polygon: Annotated[list[SourcePoint], Field(min_length=3)]
    stage: NonEmptyStr
    artifact_id: NonEmptyStr
    observations: dict[str, ObservationValue]


class Interpretation(_SceneModel):
    """Review state, optional calibrated score, and supporting evidence."""

    state: Literal["machine", "confirmed", "rejected", "unknown"]
    score: Annotated[float, Field(ge=0, le=1)] | SkipJsonSchema[None] = _omittable()
    evidence: list[Evidence]

    _no_null_score = field_validator("score", mode="before")(_reject_explicit_null)


class _SceneObject(_SceneModel):
    id: SceneId
    layer_id: SceneId
    interpretation: Interpretation


class LinePrimitive(_SceneModel):
    """A straight line in page coordinates."""

    kind: Literal["line"]
    start: PagePoint
    end: PagePoint


class OriginalPrimitive(_SceneModel):
    """The detected line before snapping to junctions."""

    start: PagePoint
    end: PagePoint


class PipeSegment(_SceneObject):
    """A pipe run between two junctions."""

    type: Literal["pipe_segment"]
    start_node_id: SceneId
    end_node_id: SceneId
    primitive: LinePrimitive
    original_primitive: OriginalPrimitive | SkipJsonSchema[None] = _omittable()

    _no_null_original = field_validator("original_primitive", mode="before")(
        _reject_explicit_null
    )


class Junction(_SceneObject):
    """A pipe node: endpoint, elbow, tee, crossing, or unknown."""

    type: Literal["junction"]
    position: PagePoint
    kind: Literal["endpoint", "elbow", "tee", "crossing", "unknown"]


class SymbolObject(_SceneObject):
    """A library symbol; each port maps to a junction ID or null if unresolved."""

    type: Literal["symbol"]
    symbol_id: NonEmptyStr
    anchor: PagePoint
    rotation_degrees: FiniteFloat
    port_node_ids: dict[NonEmptyStr, SceneId | None]


class Annotation(_SceneObject):
    """Text on the drawing, keeping recognized and normalized forms."""

    type: Literal["annotation"]
    recognized_text: str
    normalized_text: str
    alternatives: list[str]
    anchor: PagePoint
    target_object_id: SceneId | SkipJsonSchema[None] = _omittable()

    _no_null_target = field_validator("target_object_id", mode="before")(
        _reject_explicit_null
    )


class Dimension(_SceneObject):
    """A dimension; parsed value and unit are independent of pixel span."""

    type: Literal["dimension"]
    display_text: str
    parsed_value: FiniteFloat | SkipJsonSchema[None] = _omittable()
    unit: NonEmptyStr | SkipJsonSchema[None] = _omittable()
    witness_start: PagePoint
    witness_end: PagePoint
    target_object_ids: list[SceneId]

    _no_null_optionals = field_validator("parsed_value", "unit", mode="before")(
        _reject_explicit_null
    )


class UnknownMark(_SceneObject):
    """An unresolved mark kept for review."""

    type: Literal["unknown_mark"]
    source_crop_id: NonEmptyStr
    candidate_labels: list[str]


DrawingObject = Annotated[
    PipeSegment | Junction | SymbolObject | Annotation | Dimension | UnknownMark,
    Field(discriminator="type"),
]


class Relationship(_SceneModel):
    """A non-connectivity link between two scene objects."""

    id: SceneId
    type: Literal["annotates", "measures", "callout_targets"]
    from_id: SceneId
    to_id: SceneId
    interpretation: Interpretation


class DrawingScene(_SceneModel):
    """A versioned semantic scene for one drawing revision."""

    schema_version: Annotated[str, StringConstraints(pattern=SCHEMA_VERSION_PATTERN)]
    document_id: SceneId
    revision_id: SceneId
    parent_revision_id: SceneId | SkipJsonSchema[None] = _omittable()
    profile_id: Literal["piping_isometric"]
    page: Page
    layers: list[Layer]
    objects: list[DrawingObject]
    relationships: list[Relationship]

    _no_null_parent = field_validator("parent_revision_id", mode="before")(
        _reject_explicit_null
    )
