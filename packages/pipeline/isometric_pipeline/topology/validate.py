"""Validate topology candidate graphs."""

from __future__ import annotations

from isometric_pipeline.topology.artifact import TopologyMetadata


def validate_topology(metadata: TopologyMetadata) -> list[str]:
    errors: list[str] = []
    node_ids = {node.id for node in metadata.nodes}
    edge_ids: set[str] = set()
    for edge in metadata.edges:
        if edge.id in edge_ids:
            errors.append(f"duplicate edge id: {edge.id}")
        edge_ids.add(edge.id)
        if edge.start_node_id not in node_ids:
            errors.append(
                f"edge {edge.id} references missing start node {edge.start_node_id}"
            )
        if edge.end_node_id not in node_ids:
            errors.append(
                f"edge {edge.id} references missing end node {edge.end_node_id}"
            )
        if edge.start_node_id == edge.end_node_id:
            errors.append(f"edge {edge.id} has identical start and end node")

    for hypothesis in metadata.hypotheses:
        for alt in hypothesis.alternatives:
            for node_id in alt.node_ids:
                if node_id not in node_ids:
                    errors.append(
                        f"hypothesis {hypothesis.id} alternative {alt.id} "
                        f"references missing node {node_id}"
                    )
            for edge_id in alt.edge_ids:
                if edge_id not in edge_ids:
                    errors.append(
                        f"hypothesis {hypothesis.id} alternative {alt.id} "
                        f"references missing edge {edge_id}"
                    )
        if (
            hypothesis.recommended_alternative_id is not None
            and hypothesis.recommended_alternative_id
            not in {alt.id for alt in hypothesis.alternatives}
        ):
            errors.append(
                f"hypothesis {hypothesis.id} recommends unknown alternative "
                f"{hypothesis.recommended_alternative_id}"
            )

    return errors
