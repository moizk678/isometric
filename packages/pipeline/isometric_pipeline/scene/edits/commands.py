"""Semantic edit commands for DrawingScene revisions."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ..models import Color, FiniteFloat, NonEmptyStr, SceneId


class _CommandModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        strict=True,
    )


class UpdateAnnotationText(_CommandModel):
    type: Literal["update_annotation_text"] = "update_annotation_text"
    object_id: SceneId
    normalized_text: str
    recognized_text: str | None = None


class MoveAnnotation(_CommandModel):
    type: Literal["move_annotation"] = "move_annotation"
    object_id: SceneId
    x: FiniteFloat
    y: FiniteFloat


class SetSymbolType(_CommandModel):
    type: Literal["set_symbol_type"] = "set_symbol_type"
    object_id: SceneId
    symbol_id: NonEmptyStr


class SetSymbolRotation(_CommandModel):
    type: Literal["set_symbol_rotation"] = "set_symbol_rotation"
    object_id: SceneId
    rotation_degrees: FiniteFloat


class MoveJunction(_CommandModel):
    type: Literal["move_junction"] = "move_junction"
    object_id: SceneId
    x: FiniteFloat
    y: FiniteFloat


class ConnectPipeEndpoint(_CommandModel):
    type: Literal["connect_pipe_endpoint"] = "connect_pipe_endpoint"
    pipe_id: SceneId
    endpoint: Literal["start", "end"]
    node_id: SceneId


class ConnectSymbolPort(_CommandModel):
    type: Literal["connect_symbol_port"] = "connect_symbol_port"
    symbol_id: SceneId
    port: NonEmptyStr
    node_id: SceneId


class DisconnectPipeEndpoint(_CommandModel):
    type: Literal["disconnect_pipe_endpoint"] = "disconnect_pipe_endpoint"
    pipe_id: SceneId
    endpoint: Literal["start", "end"]


class DisconnectSymbolPort(_CommandModel):
    type: Literal["disconnect_symbol_port"] = "disconnect_symbol_port"
    symbol_id: SceneId
    port: NonEmptyStr


class SetLayerColor(_CommandModel):
    type: Literal["set_layer_color"] = "set_layer_color"
    layer_id: SceneId
    render_color: Color


class SetDimensionText(_CommandModel):
    type: Literal["set_dimension_text"] = "set_dimension_text"
    object_id: SceneId
    display_text: str


EditCommand = Annotated[
    UpdateAnnotationText
    | MoveAnnotation
    | SetSymbolType
    | SetSymbolRotation
    | MoveJunction
    | ConnectPipeEndpoint
    | ConnectSymbolPort
    | DisconnectPipeEndpoint
    | DisconnectSymbolPort
    | SetLayerColor
    | SetDimensionText,
    Field(discriminator="type"),
]
