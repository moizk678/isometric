"""Page transforms and drawing layers."""

from __future__ import annotations

import uuid

from isometric_pipeline.masks.artifact import MasksMetadata
from isometric_pipeline.normalize.artifact import NormalizePageMetadata
from isometric_pipeline.scene.models import Layer, Page

from .scene_ids import scene_layer_id


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def build_page(normalize: NormalizePageMetadata) -> Page:
    return Page(
        source_width_px=normalize.source_width_px,
        source_height_px=normalize.source_height_px,
        display_width_px=normalize.display_width_px,
        display_height_px=normalize.display_height_px,
        width_px=normalize.page_width_px,
        height_px=normalize.page_height_px,
        source_to_display=normalize.source_to_display,
        display_to_source=normalize.display_to_source,
        source_to_page=normalize.source_to_page,
        page_to_source=normalize.page_to_source,
    )


def build_layers(
    document_id: uuid.UUID,
    masks: MasksMetadata | None,
    *,
    default_name: str = "geometry",
) -> list[Layer]:
    if masks and masks.color_layers:
        layers: list[Layer] = []
        for record in masks.color_layers:
            layer_uuid = scene_layer_id(document_id, record.layer_id)
            color = _rgb_hex(record.normalized_rgb)
            layers.append(
                Layer(
                    id=layer_uuid,
                    name=record.layer_id,
                    source_color=color,
                    render_color=color,
                )
            )
        return layers
    layer_uuid = scene_layer_id(document_id, "default")
    return [
        Layer(
            id=layer_uuid,
            name=default_name,
            source_color="#1a1a1a",
            render_color="#0b5fff",
        )
    ]


def layer_uuid_for_pipeline_layer(
    document_id: uuid.UUID,
    pipeline_layer_id: str,
    layers: list[Layer],
) -> str:
    key = pipeline_layer_id or "default"
    mapped = scene_layer_id(document_id, key)
    for layer in layers:
        if layer.id == mapped or layer.name == key:
            return layer.id
    return layers[0].id
