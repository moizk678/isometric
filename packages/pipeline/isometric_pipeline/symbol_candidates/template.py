"""Template/shape-feature symbol classifier baseline."""

from __future__ import annotations

import cv2
import numpy as np

from isometric_pipeline.ocr.artifact import TextCandidatesMetadata
from isometric_pipeline.profiles.loader import SymbolsProfile
from isometric_pipeline.render.types import SymbolDefinition, SymbolLibrary
from isometric_pipeline.symbol_candidates.adapter import (
    SymbolScoreRow,
    SymbolScoringResult,
)
from isometric_pipeline.symbol_candidates.context import (
    dominant_edge_rotation,
    incident_edge_count,
    nearby_text_candidates,
    nearby_topology,
)
from isometric_pipeline.topology.artifact import TopologyMetadata


class TemplateSymbolClassifier:
    """Shape descriptors plus topology/text evidence; no opaque single score."""

    _VERSION = "template@1.0.0"

    def score(
        self,
        crop_rgb: np.ndarray,
        *,
        region_id: str,
        region_kind: str,
        topology: TopologyMetadata | None,
        text_candidates: TextCandidatesMetadata | None,
        library: SymbolLibrary,
        profile: SymbolsProfile,
        bbox_center: tuple[float, float],
    ) -> SymbolScoringResult:
        from isometric_pipeline.symbol_candidates.artifact import PageBBox

        features = _shape_features(crop_rgb)
        topo_ref = nearby_topology(
            PageBBox(x=bbox_center[0], y=bbox_center[1], width=1, height=1),
            topology,
            radius_px=profile.port_attach_tolerance_px * 2,
        )
        texts = nearby_text_candidates(
            PageBBox(x=bbox_center[0], y=bbox_center[1], width=1, height=1),
            text_candidates,
            radius_px=profile.nearby_text_radius_px,
        )
        rotation = 0.0
        if topology and topo_ref.node_ids:
            rotation = dominant_edge_rotation(topo_ref.node_ids[0], topology)

        rows: list[SymbolScoreRow] = []
        for symbol_id in profile.allowed_symbol_ids:
            symbol = library.get(symbol_id)
            if symbol is None:
                continue
            shape = _shape_score(symbol, features, region_kind)
            text = _text_score(symbol, texts)
            topo = _topology_score(symbol, topology, topo_ref.node_ids)
            rows.append(
                SymbolScoreRow(
                    symbol_id=symbol_id,
                    shape_score=shape,
                    text_score=text,
                    topology_score=topo,
                )
            )
        rows.sort(
            key=lambda r: r.shape_score + r.text_score + r.topology_score, reverse=True
        )
        if not rows:
            rows = [SymbolScoreRow("unknown", 0.0, 0.0, 0.0)]
        return SymbolScoringResult(alternatives=tuple(rows[:5]), rotation_deg=rotation)


def _shape_features(crop_rgb: np.ndarray) -> dict[str, float]:
    if crop_rgb.size == 0:
        return {"aspect": 1.0, "fill": 0.0, "symmetry": 0.0, "vertices": 0.0}
    gray = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = binary.shape[:2]
    aspect = w / max(h, 1)
    fill = float(np.count_nonzero(binary)) / max(w * h, 1)
    left = binary[:, : w // 2]
    right = np.fliplr(binary[:, w - w // 2 :])
    min_w = min(left.shape[1], right.shape[1])
    if min_w > 0:
        symmetry = 1.0 - float(
            np.count_nonzero(left[:, :min_w] != right[:, :min_w])
        ) / (left.shape[0] * min_w)
    else:
        symmetry = 0.0
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    vertices = 0.0
    if contours:
        peri = cv2.arcLength(contours[0], True)
        approx = cv2.approxPolyDP(contours[0], 0.04 * peri, True)
        vertices = float(len(approx))
    return {
        "aspect": aspect,
        "fill": fill,
        "symmetry": symmetry,
        "vertices": vertices,
    }


def _shape_score(
    symbol: SymbolDefinition,
    features: dict[str, float],
    region_kind: str,
) -> float:
    if region_kind == "arrow" and symbol.id == "flow_arrow":
        return 0.85
    aspect = features["aspect"]
    fill = features["fill"]
    sym = features["symmetry"]
    verts = features["vertices"]
    if symbol.id == "ball_valve":
        return _clamp(0.5 + 0.2 * sym + 0.1 * (1.0 - abs(aspect - 1.5)))
    if symbol.id == "flange":
        return _clamp(0.4 + 0.3 * sym + 0.2 * (1.0 if aspect > 1.2 else 0.0))
    if symbol.id == "flow_arrow":
        return _clamp(
            0.3
            + 0.4 * (1.0 if verts <= 4 else 0.0)
            + 0.2 * (1.0 if aspect > 1.0 else 0.0)
        )
    if symbol.id == "endpoint":
        return _clamp(0.35 + 0.2 * fill)
    if symbol.id == "unknown":
        return _clamp(0.25 + 0.15 * fill)
    if symbol.id in ("drop", "riser"):
        return _clamp(0.35 + 0.25 * (1.0 if verts <= 4 else 0.0))
    if symbol.id == "threaded_connection":
        return _clamp(0.3 + 0.2 * sym)
    if symbol.id == "block_bleed_assembly":
        return _clamp(0.35 + 0.15 * sym + 0.1 * fill)
    if symbol.id == "equipment_connection":
        return _clamp(0.3 + 0.2 * (1.0 if aspect < 1.2 else 0.0))
    return _clamp(0.2 + 0.1 * sym)


def _text_score(symbol: SymbolDefinition, texts: list) -> float:
    if not symbol.aliases:
        return 0.0
    best = 0.0
    alias_set = {a.lower() for a in symbol.aliases}
    for cand in texts:
        for field in (cand.normalized_text, cand.raw_text):
            if not field:
                continue
            lowered = field.lower()
            for alias in alias_set:
                if alias in lowered:
                    best = max(best, 0.7)
    return best


def _topology_score(
    symbol: SymbolDefinition,
    topology: TopologyMetadata | None,
    node_ids: list[str],
) -> float:
    if topology is None or not node_ids:
        return 0.0
    node = next((n for n in topology.nodes if n.id == node_ids[0]), None)
    if node is None:
        return 0.0
    edges = incident_edge_count(node.id, topology)
    allowed = symbol.allowed_attachments
    if allowed is None:
        return 0.2
    score = 0.1
    if allowed.node_kinds and node.kind in allowed.node_kinds:
        score += 0.4
    if allowed.min_incident_edges is not None and edges >= allowed.min_incident_edges:
        score += 0.2
    if allowed.max_incident_edges is not None and edges <= allowed.max_incident_edges:
        score += 0.2
    return _clamp(score)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
