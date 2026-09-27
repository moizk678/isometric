"""Inputs for scene assembly."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from isometric_pipeline.associate_markup.artifact import AssociationCandidatesMetadata
from isometric_pipeline.masks.artifact import MasksMetadata
from isometric_pipeline.normalize.artifact import NormalizePageMetadata
from isometric_pipeline.ocr.artifact import TextCandidatesMetadata
from isometric_pipeline.profiles.loader import PipingIsometricProfile
from isometric_pipeline.regions.artifact import RegionsMetadata
from isometric_pipeline.render.symbols import SymbolLibrary
from isometric_pipeline.snapping.artifact import SnappedPrimitivesMetadata
from isometric_pipeline.symbol_candidates.artifact import SymbolCandidatesMetadata
from isometric_pipeline.topology.artifact import TopologyMetadata


@dataclass(frozen=True)
class AssemblyContext:
    document_id: uuid.UUID
    revision_id: uuid.UUID
    parent_revision_id: uuid.UUID | None
    profile: PipingIsometricProfile
    symbol_library: SymbolLibrary
    normalize: NormalizePageMetadata
    masks: MasksMetadata | None = None
    regions: RegionsMetadata | None = None
    snapped: SnappedPrimitivesMetadata | None = None
    topology: TopologyMetadata | None = None
    text: TextCandidatesMetadata | None = None
    symbols: SymbolCandidatesMetadata | None = None
    associations: AssociationCandidatesMetadata | None = None
    warnings: list[str] = field(default_factory=list)
