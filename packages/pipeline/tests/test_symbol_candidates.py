"""Tests for classify_symbol_regions stage."""

from __future__ import annotations

import importlib.util
import io
import unittest
import uuid
from pathlib import Path

import numpy as np
from isometric_pipeline.ocr.artifact import (
    PageBBox as OcrBBox,
)
from isometric_pipeline.ocr.artifact import (
    TextCandidate,
    TextCandidatesMetadata,
)
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.artifact import PageBBox as RegionBBox
from isometric_pipeline.regions.artifact import RegionCandidate, RegionsMetadata
from isometric_pipeline.render.symbols import load_symbol_library
from isometric_pipeline.symbol_candidates.adapter import (
    FakeSymbolClassifier,
    SymbolScoreRow,
    SymbolScoringResult,
    UnavailableSymbolClassifier,
)
from isometric_pipeline.symbol_candidates.artifact import (
    PageBBox,
    SymbolCandidate,
    SymbolCandidatesMetadata,
    SymbolLabelAlternative,
)
from isometric_pipeline.symbol_candidates.stage import classify_symbol_regions
from isometric_pipeline.symbol_candidates.validate import validate_symbol_candidates
from isometric_pipeline.topology.artifact import (
    EdgeCandidate,
    NodeCandidate,
    PagePoint,
    TopologyMetadata,
)
from PIL import Image

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "symbols"
DOC_ID = "00000000-0000-4000-8000-000000000400"


def _ensure_fixtures() -> None:
    if not (FIXTURES / "ball-valve.png").is_file():
        spec = importlib.util.spec_from_file_location(
            "sym_generate", FIXTURES / "generate.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.generate_all()


def _blank_page(width: int = 256, height: int = 256) -> bytes:
    rgb = np.full((height, width, 3), 255, dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(rgb, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


def _encode_crop(rgb: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(rgb, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


def _region(
    region_id: str,
    kind: str,
    x: float,
    y: float,
    w: float,
    h: float,
) -> RegionCandidate:
    doc = str(uuid.UUID(DOC_ID))
    return RegionCandidate(
        id=region_id,
        kind=kind,
        bbox=RegionBBox(x=x, y=y, width=w, height=h),
        score=0.9,
        crop_uri=f"documents/{doc}/crops/{region_id}.png",
        evidence="test",
    )


def _regions_meta(regions: list[RegionCandidate]) -> RegionsMetadata:
    doc = str(uuid.UUID(DOC_ID))
    return RegionsMetadata(
        page_width_px=256,
        page_height_px=256,
        masks_metadata_uri=f"documents/{doc}/masks.json",
        regions=regions,
        protection_mask_uri=f"documents/{doc}/masks/protection.png",
        geometry_ink_mask_uri=f"documents/{doc}/masks/geometry-ink.png",
        warnings=[],
    )


def _topology_with_inline_valve() -> TopologyMetadata:
    return TopologyMetadata(
        profile_version=DEFAULT_PIPING_PROFILE_VERSION,
        page_width_px=256,
        page_height_px=256,
        snapped_primitives_metadata_uri="s",
        primitives_metadata_uri="p",
        nodes=[
            NodeCandidate(
                id="n_left",
                position=PagePoint(x=80, y=120),
                kind="endpoint",
                status="proposed",
                source_evidence="test",
            ),
            NodeCandidate(
                id="n_right",
                position=PagePoint(x=180, y=120),
                kind="endpoint",
                status="proposed",
                source_evidence="test",
            ),
        ],
        edges=[
            EdgeCandidate(
                id="e1",
                start_node_id="n_left",
                end_node_id="n_right",
                layer_id="yellow",
                start=PagePoint(x=80, y=120),
                end=PagePoint(x=180, y=120),
            )
        ],
    )


def _text_meta(candidates: list[TextCandidate]) -> TextCandidatesMetadata:
    return TextCandidatesMetadata(
        profile_version=DEFAULT_PIPING_PROFILE_VERSION,
        page_width_px=256,
        page_height_px=256,
        regions_metadata_uri="r",
        model={"name": "fake", "revision": None, "preprocessing": {}},
        candidates=candidates,
    )


class SymbolCandidatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _ensure_fixtures()

    def test_profile_symbols_section_loads(self) -> None:
        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
        self.assertEqual(profile.symbols.library_version, "piping-symbols@1.1.0")
        self.assertIn("ball_valve", profile.symbols.allowed_symbol_ids)

    def test_ball_valve_in_top_alternatives(self) -> None:
        crop = np.array(Image.open(FIXTURES / "ball-valve.png").convert("RGB"))
        regions = _regions_meta([_region("region_0001", "symbol", 88, 100, 80, 40)])
        engine = FakeSymbolClassifier(
            responses={
                "region_0001": SymbolScoringResult(
                    alternatives=(
                        SymbolScoreRow("ball_valve", 0.82, 0.1, 0.3),
                        SymbolScoreRow("unknown", 0.2, 0.0, 0.0),
                    ),
                    rotation_deg=0.0,
                )
            }
        )
        result = classify_symbol_regions(
            _blank_page(),
            regions,
            regions_json_uri="regions",
            symbol_candidates_json_uri="symbols",
            region_crops={"region_0001": _encode_crop(crop)},
            topology=_topology_with_inline_valve(),
            topology_json_uri="topology",
            classifier=engine,
        )
        cand = result.metadata.candidates[0]
        self.assertEqual(cand.alternatives[0].symbol_id, "ball_valve")
        self.assertEqual(cand.status, "proposed")
        self.assertTrue(cand.proposed_port_attachments)

    def test_ambiguous_mark_unknown_with_review(self) -> None:
        crop = np.array(Image.open(FIXTURES / "ambiguous-blob.png").convert("RGB"))
        regions = _regions_meta([_region("region_0002", "symbol", 100, 100, 48, 48)])
        engine = FakeSymbolClassifier(
            responses={
                "region_0002": SymbolScoringResult(
                    alternatives=(
                        SymbolScoreRow("unknown", 0.4, 0.0, 0.0),
                        SymbolScoreRow("ball_valve", 0.38, 0.0, 0.0),
                    ),
                )
            }
        )
        result = classify_symbol_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            symbol_candidates_json_uri="s",
            region_crops={"region_0002": _encode_crop(crop)},
            classifier=engine,
        )
        cand = result.metadata.candidates[0]
        self.assertEqual(cand.alternatives[0].symbol_id, "unknown")
        codes = {i.code for i in result.metadata.review_items}
        self.assertIn("symbol.low_margin", codes)

    def test_text_changes_ranking_not_topology(self) -> None:
        topology = _topology_with_inline_valve()
        edge_count_before = len(topology.edges)
        regions = _regions_meta([_region("region_0003", "symbol", 88, 100, 80, 40)])
        text = _text_meta(
            [
                TextCandidate(
                    id="txt_1",
                    region_id="region_text",
                    region_kind="text",
                    bbox=OcrBBox(x=90, y=70, width=60, height=20),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="BV",
                    normalized_text="ball valve",
                    status="proposed",
                )
            ]
        )
        low_text = FakeSymbolClassifier(
            responses={
                "region_0003": SymbolScoringResult(
                    alternatives=(
                        SymbolScoreRow("flange", 0.7, 0.0, 0.2),
                        SymbolScoreRow("ball_valve", 0.68, 0.0, 0.2),
                    ),
                )
            }
        )
        high_text = FakeSymbolClassifier(
            responses={
                "region_0003": SymbolScoringResult(
                    alternatives=(
                        SymbolScoreRow("flange", 0.7, 0.0, 0.2),
                        SymbolScoreRow("ball_valve", 0.68, 0.8, 0.2),
                    ),
                )
            }
        )
        r1 = classify_symbol_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            symbol_candidates_json_uri="s",
            topology=topology,
            text_candidates=text,
            classifier=low_text,
        )
        r2 = classify_symbol_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            symbol_candidates_json_uri="s",
            topology=topology,
            text_candidates=text,
            classifier=high_text,
        )
        self.assertEqual(len(topology.edges), edge_count_before)
        self.assertEqual(
            r1.metadata.candidates[0].alternatives[0].symbol_id,
            "flange",
        )
        self.assertEqual(
            r2.metadata.candidates[0].alternatives[0].symbol_id,
            "ball_valve",
        )

    def test_weak_shape_text_cannot_force_type(self) -> None:
        regions = _regions_meta([_region("region_0004", "symbol", 10, 10, 40, 40)])
        text = _text_meta(
            [
                TextCandidate(
                    id="txt_2",
                    region_id="region_text2",
                    region_kind="text",
                    bbox=OcrBBox(x=12, y=8, width=30, height=16),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="flange",
                    normalized_text="flange",
                    status="proposed",
                )
            ]
        )
        engine = FakeSymbolClassifier(
            responses={
                "region_0004": SymbolScoringResult(
                    alternatives=(SymbolScoreRow("flange", 0.1, 0.9, 0.0),),
                )
            }
        )
        result = classify_symbol_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            symbol_candidates_json_uri="s",
            text_candidates=text,
            classifier=engine,
        )
        self.assertEqual(result.metadata.candidates[0].status, "unknown")
        codes = {i.code for i in result.metadata.review_items}
        self.assertIn("symbol.ocr_insufficient_evidence", codes)

    def test_classifier_failure_partial(self) -> None:
        regions = _regions_meta([_region("region_0005", "symbol", 20, 20, 30, 30)])
        engine = FakeSymbolClassifier(failures=frozenset({"region_0005"}))
        result = classify_symbol_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            symbol_candidates_json_uri="s",
            classifier=engine,
        )
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.metadata.candidates[0].status, "unreadable")
        self.assertIn(
            "symbol.classifier_unavailable",
            {i.code for i in result.metadata.review_items},
        )

    def test_unavailable_classifier_backend_partial(self) -> None:
        regions = _regions_meta([_region("region_0006", "symbol", 30, 30, 40, 40)])
        result = classify_symbol_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            symbol_candidates_json_uri="s",
            classifier=UnavailableSymbolClassifier(),
        )
        self.assertEqual(result.status, "partial")

    def test_structural_junction_suppresses_fitting(self) -> None:
        topology = TopologyMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=256,
            page_height_px=256,
            snapped_primitives_metadata_uri="s",
            primitives_metadata_uri="p",
            nodes=[
                NodeCandidate(
                    id="tee_1",
                    position=PagePoint(x=120, y=120),
                    kind="tee",
                    status="confirmed_structure",
                    source_evidence="test",
                ),
            ],
        )
        regions = _regions_meta([_region("region_0007", "symbol", 108, 108, 24, 24)])
        engine = FakeSymbolClassifier(
            responses={
                "region_0007": SymbolScoringResult(
                    alternatives=(
                        SymbolScoreRow("tee_fitting", 0.9, 0.0, 0.5),
                        SymbolScoreRow("unknown", 0.2, 0.0, 0.0),
                    ),
                )
            }
        )
        result = classify_symbol_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            symbol_candidates_json_uri="s",
            topology=topology,
            classifier=engine,
        )
        codes = {i.code for i in result.metadata.review_items}
        self.assertIn("symbol.structural_junction_only", codes)
        self.assertEqual(
            result.metadata.candidates[0].alternatives[0].symbol_id,
            "unknown",
        )

    def test_validate_rejects_invalid_port(self) -> None:
        library = load_symbol_library("piping-symbols@1.1.0")
        meta = SymbolCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=100,
            page_height_px=100,
            regions_metadata_uri="r",
            symbol_library_version="piping-symbols@1.1.0",
            classifier={"backend": "fake", "version": "x", "parameters": {}},
            candidates=[
                SymbolCandidate(
                    id="sym_r1",
                    region_id="region_0001",
                    region_kind="symbol",
                    bbox=PageBBox(x=0, y=0, width=10, height=10),
                    crop_uri="c",
                    anchor={"x": 5, "y": 5},
                    rotation_deg=0.0,
                    status="proposed",
                    alternatives=[
                        SymbolLabelAlternative(
                            symbol_id="ball_valve",
                            shape_score=0.8,
                            text_score=0.0,
                            topology_score=0.0,
                        )
                    ],
                    proposed_port_attachments=[
                        {"portName": "bogus_port", "nodeId": "n1"}
                    ],
                )
            ],
        )
        errors = validate_symbol_candidates(
            meta, region_ids={"region_0001"}, library=library
        )
        self.assertTrue(any("invalid port" in e for e in errors))

    def test_content_hash_stable(self) -> None:
        regions = _regions_meta([_region("region_0008", "symbol", 50, 50, 40, 40)])
        engine = FakeSymbolClassifier(
            responses={
                "region_0008": SymbolScoringResult(
                    alternatives=(SymbolScoreRow("unknown", 0.5, 0.0, 0.0),),
                )
            }
        )
        kwargs = {
            "regions_json_uri": "r",
            "symbol_candidates_json_uri": "s",
            "classifier": engine,
        }
        r1 = classify_symbol_regions(_blank_page(), regions, **kwargs)
        r2 = classify_symbol_regions(_blank_page(), regions, **kwargs)
        self.assertEqual(r1.content_hash, r2.content_hash)

    def test_template_classifier_on_fixtures(self) -> None:
        crop = np.array(Image.open(FIXTURES / "flow-arrow.png").convert("RGB"))
        regions = _regions_meta([_region("region_0009", "arrow", 90, 110, 72, 32)])
        result = classify_symbol_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            symbol_candidates_json_uri="s",
            region_crops={"region_0009": _encode_crop(crop)},
        )
        top_ids = [a.symbol_id for a in result.metadata.candidates[0].alternatives[:3]]
        self.assertIn("flow_arrow", top_ids)


if __name__ == "__main__":
    unittest.main()
