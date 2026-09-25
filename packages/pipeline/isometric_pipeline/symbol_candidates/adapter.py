"""Symbol classifier adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from isometric_pipeline.ocr.artifact import TextCandidatesMetadata
from isometric_pipeline.profiles.loader import SymbolsProfile
from isometric_pipeline.render.types import SymbolLibrary
from isometric_pipeline.topology.artifact import TopologyMetadata


@dataclass(frozen=True)
class SymbolScoreRow:
    symbol_id: str
    shape_score: float
    text_score: float
    topology_score: float


@dataclass(frozen=True)
class SymbolScoringResult:
    alternatives: tuple[SymbolScoreRow, ...]
    rotation_deg: float = 0.0


class SymbolClassifier(Protocol):
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
    ) -> SymbolScoringResult: ...


class FakeSymbolClassifier:
    """Deterministic scripted scores for tests."""

    def __init__(
        self,
        *,
        responses: dict[str, SymbolScoringResult] | None = None,
        failures: frozenset[str] | None = None,
    ) -> None:
        self._responses = responses or {}
        self._failures = failures or frozenset()

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
        if region_id in self._failures:
            raise RuntimeError(f"fake classifier failure for {region_id}")
        if region_id in self._responses:
            return self._responses[region_id]
        return SymbolScoringResult(
            alternatives=(SymbolScoreRow("unknown", 0.5, 0.0, 0.0),),
            rotation_deg=0.0,
        )


class UnavailableSymbolClassifier:
    """Signals classifier absence; stage handles partial status."""

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
        raise RuntimeError("symbol classifier unavailable")


def default_symbol_classifier(backend: str) -> SymbolClassifier:
    if backend == "template":
        from isometric_pipeline.symbol_candidates.template import (
            TemplateSymbolClassifier,
        )

        return TemplateSymbolClassifier()
    if backend == "fake":
        return FakeSymbolClassifier()
    raise ValueError(f"unsupported symbol classifier backend: {backend!r}")
