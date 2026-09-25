"""Frozen value types shared by the renderer, validator, preview, and symbols."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

UnresolvedKind = Literal["unknown_junction", "unresolved_port", "unknown_mark"]


@dataclass(frozen=True)
class UnresolvedItem:
    """Something drawn in the ``unresolved`` group instead of being guessed.

    ``port`` is the symbol port name for ``unresolved_port`` and ``None``
    otherwise.
    """

    kind: UnresolvedKind
    object_id: str
    port: str | None = None


@dataclass(frozen=True)
class ExportMetadata:
    """Contents of the SVG ``<metadata>`` block. It never holds URIs."""

    schema_version: str
    document_id: str
    revision_id: str
    renderer_version: str
    symbol_library_version: str
    style_profile_version: str
    unresolved_count: int

    def to_json_object(self) -> dict[str, Any]:
        """Wire form in a fixed key order, serialized as compact JSON."""
        return {
            "schemaVersion": self.schema_version,
            "documentId": self.document_id,
            "revisionId": self.revision_id,
            "rendererVersion": self.renderer_version,
            "symbolLibraryVersion": self.symbol_library_version,
            "styleProfileVersion": self.style_profile_version,
            "unresolvedCount": self.unresolved_count,
        }


@dataclass(frozen=True)
class RenderResult:
    """UTF-8 SVG bytes with LF line endings, and the hex sha256 of those bytes."""

    svg: bytes
    sha256: str
    metadata: ExportMetadata
    unresolved: tuple[UnresolvedItem, ...]


@dataclass(frozen=True)
class PreviewResult:
    """PNG bytes, their hex sha256, and what produced them.

    ``rasterizer`` is ``versions.RASTERIZER``. ``font`` identifies the bundled
    font as ``"{file name}@sha256:{hex}"``.
    """

    png: bytes
    sha256: str
    rasterizer: str
    font: str


@dataclass(frozen=True)
class SymbolPort:
    """A named connection point in symbol-local pixels."""

    name: str
    x: float
    y: float
    required: bool


@dataclass(frozen=True)
class SymbolPrimitive:
    """One piece of symbol geometry in symbol-local pixels.

    ``points`` holds 2 points for a line, at least 3 for a polygon, and the
    single center point for a circle. ``radius`` is set only for circles.
    ``fill`` means the shape is filled with the stroke color; otherwise it is
    outline only.
    """

    kind: Literal["line", "circle", "polygon"]
    points: tuple[tuple[float, float], ...]
    radius: float | None = None
    fill: bool = False


@dataclass(frozen=True)
class SymbolAllowedAttachments:
    """Topology constraints for port binding during symbol classification."""

    node_kinds: frozenset[str]
    min_incident_edges: int | None
    max_incident_edges: int | None


@dataclass(frozen=True)
class SymbolDefinition:
    id: str
    label: str
    ports: tuple[SymbolPort, ...]
    primitives: tuple[SymbolPrimitive, ...]
    aliases: tuple[str, ...] = ()
    anchor_x: float = 0.0
    anchor_y: float = 0.0
    allowed_attachments: SymbolAllowedAttachments | None = None

    def port(self, name: str) -> SymbolPort | None:
        for port in self.ports:
            if port.name == name:
                return port
        return None


class SymbolLibrary:
    """A versioned set of symbols; satisfies ``scene.validation.SymbolCatalog``."""

    def __init__(self, version: str, symbols: Iterable[SymbolDefinition]) -> None:
        by_id: dict[str, SymbolDefinition] = {}
        for symbol in symbols:
            if symbol.id in by_id:
                raise ValueError(f"duplicate symbol id {symbol.id!r}")
            by_id[symbol.id] = symbol
        self._version = version
        self._symbols = MappingProxyType(dict(sorted(by_id.items())))

    @property
    def version(self) -> str:
        return self._version

    @property
    def symbol_ids(self) -> tuple[str, ...]:
        return tuple(self._symbols)

    def get(self, symbol_id: str) -> SymbolDefinition | None:
        return self._symbols.get(symbol_id)

    def port_names(self, symbol_id: str) -> frozenset[str] | None:
        symbol = self._symbols.get(symbol_id)
        if symbol is None:
            return None
        return frozenset(port.name for port in symbol.ports)

    def required_ports(self, symbol_id: str) -> frozenset[str]:
        symbol = self._symbols.get(symbol_id)
        if symbol is None:
            return frozenset()
        return frozenset(port.name for port in symbol.ports if port.required)
