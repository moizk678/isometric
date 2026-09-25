"""Tests for the bundled piping symbol library loader."""

from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

from isometric_pipeline.render.errors import RenderError, RenderIssueCode
from isometric_pipeline.render.symbols import load_symbol_library
from isometric_pipeline.render.versions import SYMBOL_LIBRARY_VERSION
from isometric_pipeline.scene.validation import SymbolCatalog

REPO_ROOT = Path(__file__).resolve().parents[2]
SYMBOL_LIBRARY_DIR = REPO_ROOT / "symbol-library"
LIBRARY_JSON = SYMBOL_LIBRARY_DIR / "piping-symbols-1.0.0.json"
FONT_PATH = SYMBOL_LIBRARY_DIR / "fonts" / "LiberationSans-Regular.ttf"

LIBERATION_SANS_REGULAR_SHA256 = (
    "76d04c18ea243f426b7de1f3ad208e927008f961dc5945e5aad352d0dfde8ee8"
)

_EXPECTED_SYMBOLS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "ball_valve": (frozenset({"inlet", "outlet"}), frozenset({"inlet", "outlet"})),
    "elbow_fitting": (frozenset({"a", "b"}), frozenset({"a", "b"})),
    "endpoint": (frozenset({"pipe"}), frozenset({"pipe"})),
    "tee_fitting": (
        frozenset({"run_a", "run_b", "branch"}),
        frozenset({"run_a", "run_b", "branch"}),
    ),
    "unknown": (
        frozenset({"port_1", "port_2", "port_3", "port_4"}),
        frozenset(),
    ),
}

_BALL_VALVE_PORTS = {
    "inlet": (-20.0, 0.0),
    "outlet": (20.0, 0.0),
}


class RenderSymbolsTest(unittest.TestCase):
    def test_loads_pinned_library_version(self) -> None:
        library = load_symbol_library(SYMBOL_LIBRARY_VERSION)
        self.assertEqual(library.version, SYMBOL_LIBRARY_VERSION)
        self.assertEqual(
            library.symbol_ids,
            (
                "ball_valve",
                "elbow_fitting",
                "endpoint",
                "tee_fitting",
                "unknown",
            ),
        )

    def test_unknown_version_raises_version_unsupported(self) -> None:
        with self.assertRaises(RenderError) as ctx:
            load_symbol_library("piping-symbols@9.9.9")
        self.assertEqual(ctx.exception.codes, (RenderIssueCode.VERSION_UNSUPPORTED,))

    def test_satisfies_symbol_catalog_protocol(self) -> None:
        library = load_symbol_library(SYMBOL_LIBRARY_VERSION)
        catalog: SymbolCatalog = library

        for symbol_id, (port_names, required_ports) in _EXPECTED_SYMBOLS.items():
            with self.subTest(symbol_id=symbol_id):
                self.assertEqual(catalog.port_names(symbol_id), port_names)
                self.assertEqual(catalog.required_ports(symbol_id), required_ports)

        self.assertIsNone(catalog.port_names("missing_symbol"))
        self.assertEqual(catalog.required_ports("missing_symbol"), frozenset())

    def test_ball_valve_port_coordinates_match_valve_inline(self) -> None:
        library = load_symbol_library(SYMBOL_LIBRARY_VERSION)
        symbol = library.get("ball_valve")
        self.assertIsNotNone(symbol)
        assert symbol is not None
        for name, (expected_x, expected_y) in _BALL_VALVE_PORTS.items():
            port = symbol.port(name)
            self.assertIsNotNone(port)
            assert port is not None
            self.assertEqual(port.x, expected_x)
            self.assertEqual(port.y, expected_y)

    def test_bundled_font_matches_pinned_sha256(self) -> None:
        digest = hashlib.sha256(FONT_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, LIBERATION_SANS_REGULAR_SHA256)

    def test_library_json_has_no_raw_svg_or_urls(self) -> None:
        text = LIBRARY_JSON.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertNotIn("<svg", lowered)
        self.assertNotIn("http://", lowered)
        self.assertNotIn("https://", lowered)
        self.assertNotRegex(text, re.compile(r"\burl\s*\(", re.IGNORECASE))

        payload = json.loads(text)
        serialized = json.dumps(payload)
        self.assertNotIn("<", serialized)
