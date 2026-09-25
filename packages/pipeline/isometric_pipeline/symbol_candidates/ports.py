"""Propose and validate symbol port attachments against topology."""

from __future__ import annotations

import math
import uuid

from isometric_pipeline.profiles.loader import SymbolsProfile
from isometric_pipeline.render.types import SymbolDefinition, SymbolLibrary
from isometric_pipeline.symbol_candidates.artifact import (
    PagePoint,
    ProposedPortAttachment,
    SymbolLabelAlternative,
    SymbolReviewItem,
)
from isometric_pipeline.symbol_candidates.context import incident_edge_count
from isometric_pipeline.topology.artifact import TopologyMetadata


def propose_port_attachments(
    symbol_id: str,
    library: SymbolLibrary,
    topology: TopologyMetadata | None,
    anchor: PagePoint,
    rotation_deg: float,
    profile: SymbolsProfile,
) -> tuple[list[ProposedPortAttachment], list[SymbolReviewItem]]:
    review: list[SymbolReviewItem] = []
    symbol = library.get(symbol_id)
    if symbol is None or topology is None:
        return [], review

    attachments: list[ProposedPortAttachment] = []
    used_nodes: dict[str, str] = {}
    rad = math.radians(rotation_deg)
    cos_r = math.cos(rad)
    sin_r = math.sin(rad)
    scale = 1.0

    for port in symbol.ports:
        px = port.x * scale
        py = port.y * scale
        world_x = anchor.x + (px * cos_r - py * sin_r)
        world_y = anchor.y + (px * sin_r + py * cos_r)
        node_id = _nearest_node(
            world_x, world_y, topology, profile.port_attach_tolerance_px
        )
        attachments.append(ProposedPortAttachment(port_name=port.name, node_id=node_id))
        if node_id is not None:
            if node_id in used_nodes:
                review.append(
                    SymbolReviewItem(
                        id=f"rev_{uuid.uuid4().hex[:12]}",
                        code="symbol.port_conflict",
                        message=(
                            f"Ports {used_nodes[node_id]!r} and {port.name!r} "
                            f"map to node {node_id}"
                        ),
                        region_id=None,
                    )
                )
            used_nodes[node_id] = port.name

    review.extend(
        _validate_attachments(symbol, attachments, topology, symbol_id=symbol_id)
    )
    return attachments, review


def _nearest_node(
    x: float,
    y: float,
    topology: TopologyMetadata,
    tolerance_px: float,
) -> str | None:
    best_id: str | None = None
    best_dist = tolerance_px
    for node in topology.nodes:
        dist = math.hypot(node.position.x - x, node.position.y - y)
        if dist <= best_dist:
            best_dist = dist
            best_id = node.id
    return best_id


def _validate_attachments(
    symbol: SymbolDefinition,
    attachments: list[ProposedPortAttachment],
    topology: TopologyMetadata,
    *,
    symbol_id: str,
) -> list[SymbolReviewItem]:
    items: list[SymbolReviewItem] = []
    by_name = {a.port_name: a for a in attachments}
    for port in symbol.ports:
        if not port.required:
            continue
        att = by_name.get(port.name)
        if att is None or att.node_id is None:
            items.append(
                SymbolReviewItem(
                    id=f"rev_{uuid.uuid4().hex[:12]}",
                    code="symbol.port_conflict",
                    message=f"Required port {port.name!r} has no node for {symbol_id}",
                )
            )
            continue
        node = next((n for n in topology.nodes if n.id == att.node_id), None)
        if node is None:
            continue
        allowed = symbol.allowed_attachments
        if allowed is None:
            continue
        if allowed.node_kinds and node.kind not in allowed.node_kinds:
            items.append(
                SymbolReviewItem(
                    id=f"rev_{uuid.uuid4().hex[:12]}",
                    code="symbol.port_conflict",
                    message=(
                        f"Port {port.name!r} on node kind {node.kind!r} "
                        f"not allowed for {symbol_id}"
                    ),
                )
            )
        edge_count = incident_edge_count(node.id, topology)
        if (
            allowed.min_incident_edges is not None
            and edge_count < allowed.min_incident_edges
        ):
            items.append(
                SymbolReviewItem(
                    id=f"rev_{uuid.uuid4().hex[:12]}",
                    code="symbol.port_conflict",
                    message=f"Node {node.id} has too few incident edges for {symbol_id}",
                )
            )
        if (
            allowed.max_incident_edges is not None
            and edge_count > allowed.max_incident_edges
        ):
            items.append(
                SymbolReviewItem(
                    id=f"rev_{uuid.uuid4().hex[:12]}",
                    code="symbol.port_conflict",
                    message=f"Node {node.id} has too many incident edges for {symbol_id}",
                )
            )
    return items


def combined_score(alt: SymbolLabelAlternative) -> float:
    return alt.shape_score + alt.text_score + alt.topology_score
