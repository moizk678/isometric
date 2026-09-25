"""Validate symbol candidate artifacts."""

from __future__ import annotations

from isometric_pipeline.render.types import SymbolLibrary
from isometric_pipeline.symbol_candidates.artifact import SymbolCandidatesMetadata


def validate_symbol_candidates(
    metadata: SymbolCandidatesMetadata,
    *,
    region_ids: set[str],
    library: SymbolLibrary,
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    allowed_ports: dict[str, frozenset[str]] = {
        sid: library.port_names(sid) or frozenset() for sid in library.symbol_ids
    }
    for candidate in metadata.candidates:
        if candidate.id in seen:
            errors.append(f"duplicate symbol candidate id: {candidate.id}")
        seen.add(candidate.id)
        if candidate.region_id not in region_ids:
            errors.append(f"unknown region id: {candidate.region_id}")
        if not candidate.crop_uri:
            errors.append(f"missing cropUri for {candidate.id}")
        for alt in candidate.alternatives:
            if alt.symbol_id not in library.symbol_ids:
                errors.append(f"unknown symbol id {alt.symbol_id} on {candidate.id}")
        for att in candidate.proposed_port_attachments:
            names = allowed_ports.get(
                candidate.alternatives[0].symbol_id if candidate.alternatives else "",
                frozenset(),
            )
            if candidate.alternatives and att.port_name not in names:
                errors.append(
                    f"invalid port {att.port_name!r} for candidate {candidate.id}"
                )
    for item in metadata.review_items:
        if item.symbol_candidate_id and item.symbol_candidate_id not in seen:
            errors.append(
                f"review item references missing candidate {item.symbol_candidate_id}"
            )
    return errors
