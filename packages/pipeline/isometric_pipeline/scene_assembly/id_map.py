"""Candidate ID to scene UUID lookups built during assembly."""

from __future__ import annotations

import uuid

from .scene_ids import scene_object_id


class AssemblyIdMap:
    def __init__(self, document_id: uuid.UUID) -> None:
        self._document_id = document_id
        self.node_to_scene: dict[str, str] = {}
        self.edge_to_scene: dict[str, str] = {}
        self.symbol_to_scene: dict[str, str] = {}
        self.text_to_scene: dict[str, str] = {}
        self.dimension_to_scene: dict[str, str] = {}
        self.annotation_to_scene: dict[str, str] = {}

    def object_id(self, candidate_id: str) -> str:
        return scene_object_id(self._document_id, candidate_id)

    def register_node(self, node_id: str, scene_id: str) -> None:
        self.node_to_scene[node_id] = scene_id

    def register_edge(self, edge_id: str, scene_id: str) -> None:
        self.edge_to_scene[edge_id] = scene_id

    def register_symbol(self, candidate_id: str, scene_id: str) -> None:
        self.symbol_to_scene[candidate_id] = scene_id

    def register_text(self, text_id: str, scene_id: str) -> None:
        self.text_to_scene[text_id] = scene_id

    def register_dimension(self, dim_candidate_id: str, scene_id: str) -> None:
        self.dimension_to_scene[dim_candidate_id] = scene_id

    def register_annotation(self, ann_key: str, scene_id: str) -> None:
        self.annotation_to_scene[ann_key] = scene_id

    def resolve_target(self, ref_kind: str, ref_id: str) -> str | None:
        if ref_kind == "topology_node":
            return self.node_to_scene.get(ref_id)
        if ref_kind == "topology_edge":
            return self.edge_to_scene.get(ref_id)
        if ref_kind == "symbol_candidate":
            return self.symbol_to_scene.get(ref_id)
        return None
