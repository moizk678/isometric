"""Load assembly inputs from persisted document artifacts."""

from __future__ import annotations

import json
import uuid

from isometric_persistence.artifacts import ArtifactStore
from isometric_persistence.keys import (
    document_association_candidates_metadata_key,
    document_masks_metadata_key,
    document_normalize_metadata_key,
    document_regions_metadata_key,
    document_snapped_primitives_metadata_key,
    document_symbol_candidates_metadata_key,
    document_text_candidates_metadata_key,
    document_topology_metadata_key,
)
from isometric_pipeline.associate_markup.artifact import AssociationCandidatesMetadata
from isometric_pipeline.masks.artifact import MasksMetadata
from isometric_pipeline.normalize.artifact import NormalizePageMetadata
from isometric_pipeline.ocr.artifact import TextCandidatesMetadata
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
    resolve_piping_profile_version,
)
from isometric_pipeline.regions.artifact import RegionsMetadata
from isometric_pipeline.render import load_symbol_library
from isometric_pipeline.scene_assembly.context import AssemblyContext
from isometric_pipeline.snapping.artifact import SnappedPrimitivesMetadata
from isometric_pipeline.symbol_candidates.artifact import SymbolCandidatesMetadata
from isometric_pipeline.topology.artifact import TopologyMetadata


def _read_json(store: ArtifactStore, key: str) -> dict | None:
    try:
        return json.loads(store.read(key).decode("utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def load_assembly_context(
    store: ArtifactStore,
    *,
    document_id: uuid.UUID,
    revision_id: uuid.UUID,
    parent_revision_id: uuid.UUID | None,
    profile_version: str = DEFAULT_PIPING_PROFILE_VERSION,
) -> AssemblyContext:
    normalize_key = document_normalize_metadata_key(document_id)
    normalize_wire = _read_json(store, normalize_key)
    if normalize_wire is None:
        raise FileNotFoundError(normalize_key)
    normalize = NormalizePageMetadata.model_validate(normalize_wire)
    profile = load_piping_profile(resolve_piping_profile_version(profile_version))
    sym_profile = profile.symbols

    masks: MasksMetadata | None = None
    masks_wire = _read_json(store, document_masks_metadata_key(document_id))
    if masks_wire is not None:
        masks = MasksMetadata.model_validate(masks_wire)

    regions: RegionsMetadata | None = None
    regions_wire = _read_json(store, document_regions_metadata_key(document_id))
    if regions_wire is not None:
        regions = RegionsMetadata.model_validate(regions_wire)

    snapped: SnappedPrimitivesMetadata | None = None
    snapped_wire = _read_json(
        store, document_snapped_primitives_metadata_key(document_id)
    )
    if snapped_wire is not None:
        snapped = SnappedPrimitivesMetadata.model_validate(snapped_wire)

    topology: TopologyMetadata | None = None
    topology_wire = _read_json(store, document_topology_metadata_key(document_id))
    if topology_wire is not None:
        topology = TopologyMetadata.model_validate(topology_wire)

    text: TextCandidatesMetadata | None = None
    text_wire = _read_json(store, document_text_candidates_metadata_key(document_id))
    if text_wire is not None:
        text = TextCandidatesMetadata.model_validate(text_wire)

    symbols: SymbolCandidatesMetadata | None = None
    symbol_wire = _read_json(
        store, document_symbol_candidates_metadata_key(document_id)
    )
    if symbol_wire is not None:
        symbols = SymbolCandidatesMetadata.model_validate(symbol_wire)

    associations: AssociationCandidatesMetadata | None = None
    assoc_wire = _read_json(
        store, document_association_candidates_metadata_key(document_id)
    )
    if assoc_wire is not None:
        associations = AssociationCandidatesMetadata.model_validate(assoc_wire)

    return AssemblyContext(
        document_id=document_id,
        revision_id=revision_id,
        parent_revision_id=parent_revision_id,
        profile=profile,
        symbol_library=load_symbol_library(sym_profile.library_version),
        normalize=normalize,
        masks=masks,
        regions=regions,
        snapped=snapped,
        topology=topology,
        text=text,
        symbols=symbols,
        associations=associations,
    )
