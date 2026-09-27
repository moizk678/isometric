"""Apply semantic edit commands to a DrawingScene."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from pydantic import TypeAdapter

from ..models import (
    Annotation,
    Dimension,
    DrawingObject,
    DrawingScene,
    Interpretation,
    Junction,
    Layer,
    PagePoint,
    PipeSegment,
    SymbolObject,
)
from ..validation import SymbolCatalog, validate_scene
from .commands import (
    ConnectPipeEndpoint,
    ConnectSymbolPort,
    DisconnectPipeEndpoint,
    DisconnectSymbolPort,
    EditCommand,
    MoveAnnotation,
    MoveJunction,
    SetDimensionText,
    SetLayerColor,
    SetSymbolRotation,
    SetSymbolType,
    UpdateAnnotationText,
)

_COMMAND_ADAPTER: TypeAdapter[EditCommand] = TypeAdapter(EditCommand)


@dataclass
class ApplyEditsResult:
    scene: DrawingScene
    affected_object_ids: list[str] = field(default_factory=list)
    new_object_ids: list[str] = field(default_factory=list)


def parse_edit_commands(raw: list[dict[str, Any]]) -> list[EditCommand]:
    return [_COMMAND_ADAPTER.validate_python(item) for item in raw]


def _confirm(interp: Interpretation) -> Interpretation:
    return interp.model_copy(update={"state": "confirmed"})


def _index_objects(scene: DrawingScene) -> dict[str, DrawingObject]:
    return {obj.id: obj for obj in scene.objects}


def _replace_object(
    objects: list[DrawingObject], object_id: str, updated: DrawingObject
) -> list[DrawingObject]:
    return [updated if obj.id == object_id else obj for obj in objects]


def _junction_at(objects: dict[str, DrawingObject], node_id: str) -> Junction:
    obj = objects.get(node_id)
    if obj is None or not isinstance(obj, Junction):
        raise ValueError(f"node {node_id} is not a junction")
    return obj


def _apply_one(
    scene: DrawingScene,
    command: EditCommand,
    affected: set[str],
    created: list[str],
) -> DrawingScene:
    objects = _index_objects(scene)
    layers = list(scene.layers)

    if isinstance(command, UpdateAnnotationText):
        obj = objects.get(command.object_id)
        if obj is None or not isinstance(obj, Annotation):
            raise ValueError(f"object {command.object_id} is not an annotation")
        recognized = (
            command.recognized_text
            if command.recognized_text is not None
            else obj.recognized_text
        )
        updated = obj.model_copy(
            update={
                "recognized_text": recognized,
                "normalized_text": command.normalized_text,
                "interpretation": _confirm(obj.interpretation),
            }
        )
        affected.add(command.object_id)
        return scene.model_copy(
            update={"objects": _replace_object(scene.objects, command.object_id, updated)}
        )

    if isinstance(command, MoveAnnotation):
        obj = objects.get(command.object_id)
        if obj is None or not isinstance(obj, Annotation):
            raise ValueError(f"object {command.object_id} is not an annotation")
        updated = obj.model_copy(
            update={
                "anchor": PagePoint(x=command.x, y=command.y),
                "interpretation": _confirm(obj.interpretation),
            }
        )
        affected.add(command.object_id)
        return scene.model_copy(
            update={"objects": _replace_object(scene.objects, command.object_id, updated)}
        )

    if isinstance(command, SetSymbolType):
        obj = objects.get(command.object_id)
        if obj is None or not isinstance(obj, SymbolObject):
            raise ValueError(f"object {command.object_id} is not a symbol")
        updated = obj.model_copy(
            update={
                "symbol_id": command.symbol_id,
                "interpretation": _confirm(obj.interpretation),
            }
        )
        affected.add(command.object_id)
        return scene.model_copy(
            update={"objects": _replace_object(scene.objects, command.object_id, updated)}
        )

    if isinstance(command, SetSymbolRotation):
        obj = objects.get(command.object_id)
        if obj is None or not isinstance(obj, SymbolObject):
            raise ValueError(f"object {command.object_id} is not a symbol")
        updated = obj.model_copy(
            update={
                "rotation_degrees": command.rotation_degrees,
                "interpretation": _confirm(obj.interpretation),
            }
        )
        affected.add(command.object_id)
        return scene.model_copy(
            update={"objects": _replace_object(scene.objects, command.object_id, updated)}
        )

    if isinstance(command, MoveJunction):
        obj = objects.get(command.object_id)
        if obj is None or not isinstance(obj, Junction):
            raise ValueError(f"object {command.object_id} is not a junction")
        new_pos = PagePoint(x=command.x, y=command.y)
        updated_objects: list[DrawingObject] = []
        for item in scene.objects:
            if item.id == command.object_id:
                updated_objects.append(
                    obj.model_copy(
                        update={
                            "position": new_pos,
                            "interpretation": _confirm(obj.interpretation),
                        }
                    )
                )
                continue
            if isinstance(item, PipeSegment) and (
                item.start_node_id == command.object_id
                or item.end_node_id == command.object_id
            ):
                prim = item.primitive
                if item.start_node_id == command.object_id:
                    prim = prim.model_copy(update={"start": new_pos})
                if item.end_node_id == command.object_id:
                    prim = prim.model_copy(update={"end": new_pos})
                updated_objects.append(
                    item.model_copy(
                        update={
                            "primitive": prim,
                            "interpretation": _confirm(item.interpretation),
                        }
                    )
                )
                affected.add(item.id)
                continue
            updated_objects.append(item)
        affected.add(command.object_id)
        return scene.model_copy(update={"objects": updated_objects})

    if isinstance(command, ConnectPipeEndpoint):
        pipe = objects.get(command.pipe_id)
        if pipe is None or not isinstance(pipe, PipeSegment):
            raise ValueError(f"object {command.pipe_id} is not a pipe segment")
        node = _junction_at(objects, command.node_id)
        point = node.position
        prim = pipe.primitive
        if command.endpoint == "start":
            prim = prim.model_copy(update={"start": point})
            pipe = pipe.model_copy(
                update={
                    "start_node_id": command.node_id,
                    "primitive": prim,
                    "interpretation": _confirm(pipe.interpretation),
                }
            )
        else:
            prim = prim.model_copy(update={"end": point})
            pipe = pipe.model_copy(
                update={
                    "end_node_id": command.node_id,
                    "primitive": prim,
                    "interpretation": _confirm(pipe.interpretation),
                }
            )
        affected.update({command.pipe_id, command.node_id})
        return scene.model_copy(
            update={"objects": _replace_object(scene.objects, command.pipe_id, pipe)}
        )

    if isinstance(command, ConnectSymbolPort):
        sym = objects.get(command.symbol_id)
        if sym is None or not isinstance(sym, SymbolObject):
            raise ValueError(f"object {command.symbol_id} is not a symbol")
        if command.port not in sym.port_node_ids:
            raise ValueError(f"symbol has no port {command.port!r}")
        _junction_at(objects, command.node_id)
        ports = dict(sym.port_node_ids)
        ports[command.port] = command.node_id
        updated = sym.model_copy(
            update={
                "port_node_ids": ports,
                "interpretation": _confirm(sym.interpretation),
            }
        )
        affected.update({command.symbol_id, command.node_id})
        return scene.model_copy(
            update={"objects": _replace_object(scene.objects, command.symbol_id, updated)}
        )

    if isinstance(command, DisconnectPipeEndpoint):
        pipe = objects.get(command.pipe_id)
        if pipe is None or not isinstance(pipe, PipeSegment):
            raise ValueError(f"object {command.pipe_id} is not a pipe segment")
        point = (
            pipe.primitive.start
            if command.endpoint == "start"
            else pipe.primitive.end
        )
        new_id = str(uuid.uuid4())
        new_junction = Junction(
            type="junction",
            id=new_id,
            layer_id=pipe.layer_id,
            position=point,
            kind="endpoint",
            interpretation=Interpretation(state="confirmed", evidence=[]),
        )
        created.append(new_id)
        if command.endpoint == "start":
            pipe = pipe.model_copy(
                update={
                    "start_node_id": new_id,
                    "interpretation": _confirm(pipe.interpretation),
                }
            )
        else:
            pipe = pipe.model_copy(
                update={
                    "end_node_id": new_id,
                    "interpretation": _confirm(pipe.interpretation),
                }
            )
        new_objects = [
            new_junction,
            *[
                pipe if obj.id == command.pipe_id else obj
                for obj in scene.objects
            ],
        ]
        affected.add(command.pipe_id)
        return scene.model_copy(update={"objects": new_objects})

    if isinstance(command, DisconnectSymbolPort):
        sym = objects.get(command.symbol_id)
        if sym is None or not isinstance(sym, SymbolObject):
            raise ValueError(f"object {command.symbol_id} is not a symbol")
        if command.port not in sym.port_node_ids:
            raise ValueError(f"symbol has no port {command.port!r}")
        ports = dict(sym.port_node_ids)
        ports[command.port] = None
        updated = sym.model_copy(
            update={
                "port_node_ids": ports,
                "interpretation": _confirm(sym.interpretation),
            }
        )
        affected.add(command.symbol_id)
        return scene.model_copy(
            update={"objects": _replace_object(scene.objects, command.symbol_id, updated)}
        )

    if isinstance(command, SetLayerColor):
        found = False
        new_layers: list[Layer] = []
        for layer in layers:
            if layer.id == command.layer_id:
                new_layers.append(
                    layer.model_copy(update={"render_color": command.render_color})
                )
                found = True
            else:
                new_layers.append(layer)
        if not found:
            raise ValueError(f"layer {command.layer_id} not found")
        return scene.model_copy(update={"layers": new_layers})

    if isinstance(command, SetDimensionText):
        obj = objects.get(command.object_id)
        if obj is None or not isinstance(obj, Dimension):
            raise ValueError(f"object {command.object_id} is not a dimension")
        updated = obj.model_copy(
            update={
                "display_text": command.display_text,
                "interpretation": _confirm(obj.interpretation),
            }
        )
        affected.add(command.object_id)
        return scene.model_copy(
            update={"objects": _replace_object(scene.objects, command.object_id, updated)}
        )

    raise TypeError(f"unsupported command: {type(command)!r}")


def apply_edits(
    scene: DrawingScene,
    commands: list[EditCommand],
    *,
    catalog: SymbolCatalog | None = None,
    new_revision_id: str | None = None,
    endpoint_tolerance_px: float | None = None,
) -> ApplyEditsResult:
    """Apply commands in order, validate, and return the updated scene."""
    current = scene
    affected: set[str] = set()
    created: list[str] = []
    for command in commands:
        current = _apply_one(current, command, affected, created)
    if new_revision_id is not None:
        current = current.model_copy(
            update={
                "revision_id": new_revision_id,
                "parent_revision_id": scene.revision_id,
            }
        )
    kwargs: dict[str, Any] = {}
    if catalog is not None:
        kwargs["catalog"] = catalog
    if endpoint_tolerance_px is not None:
        kwargs["endpoint_tolerance_px"] = endpoint_tolerance_px
    validate_scene(current, **kwargs)
    return ApplyEditsResult(
        scene=current,
        affected_object_ids=sorted(affected),
        new_object_ids=created,
    )

