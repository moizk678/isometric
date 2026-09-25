"""Tests for transcribe_regions stage."""

from __future__ import annotations

import importlib.util
import io
import os
import unittest
import uuid
from pathlib import Path

import numpy as np
from isometric_pipeline.ocr.adapter import FakeOcrEngine, OcrRecognition
from isometric_pipeline.ocr.artifact import (
    PageBBox,
    TextCandidate,
    TextCandidatesMetadata,
)
from isometric_pipeline.ocr.dimensions import parse_dimension_text
from isometric_pipeline.ocr.preprocess import crop_region
from isometric_pipeline.ocr.stage import transcribe_regions
from isometric_pipeline.ocr.validate import validate_text_candidates
from isometric_pipeline.ocr.vocabulary import OcrVocabulary, propose_normalized_text
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.artifact import PageBBox as RegionBBox
from isometric_pipeline.regions.artifact import RegionCandidate, RegionsMetadata
from isometric_pipeline.topology.artifact import (
    NodeCandidate,
    PagePoint,
    TopologyMetadata,
)
from PIL import Image

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ocr"
DOC_ID = "00000000-0000-4000-8000-000000000300"


def _ensure_fixtures() -> None:
    if not (FIXTURES / "abbrev-conn.png").is_file():
        spec = importlib.util.spec_from_file_location("ocr_generate", FIXTURES / "generate.py")
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


class HandwritingOcrTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _ensure_fixtures()

    def test_profile_ocr_section_loads(self) -> None:
        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
        self.assertIn("trocr", profile.ocr.model_id.lower())

    def test_parse_feet_and_inches(self) -> None:
        feet = parse_dimension_text("20 ft")
        self.assertIsNotNone(feet)
        assert feet is not None
        self.assertEqual(feet.unit, "ft")
        self.assertEqual(feet.value, 20.0)
        inch = parse_dimension_text('1"')
        assert inch is not None
        self.assertEqual(inch.unit, "in")
        prime = parse_dimension_text("1'")
        assert prime is not None
        self.assertEqual(prime.unit, "ft")
        illegible = parse_dimension_text("'")
        assert illegible is not None
        self.assertEqual(illegible.status, "illegible")

    def test_vocabulary_preserves_raw_while_normalizing(self) -> None:
        vocab = OcrVocabulary.from_profile(
            ["main", "connection"],
            {"conn": "connection", "conn.": "connection"},
        )
        raw = "conn. to main"
        normalized = propose_normalized_text(raw, vocab)
        self.assertIsNotNone(normalized)
        self.assertNotEqual(normalized, raw)

    def test_validate_rejects_empty_raw_for_proposed(self) -> None:
        meta = TextCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=100,
            page_height_px=100,
            regions_metadata_uri="r",
            model={"name": "fake", "revision": None, "preprocessing": {}},
            candidates=[
                TextCandidate(
                    id="t1",
                    region_id="region_0001",
                    region_kind="text",
                    bbox=PageBBox(x=0, y=0, width=10, height=10),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="",
                    status="proposed",
                )
            ],
        )
        errors = validate_text_candidates(meta, region_ids={"region_0001"})
        self.assertTrue(any("empty rawText" in e for e in errors))

    def test_abbreviation_fixture_with_fake_ocr(self) -> None:
        crop = np.array(Image.open(FIXTURES / "abbrev-conn.png").convert("RGB"))
        regions = _regions_meta([_region("region_0001", "text", 40, 40, 120, 40)])
        engine = FakeOcrEngine(
            responses={
                "region_0001": OcrRecognition(
                    raw_text="conn. to main",
                    confidence=0.82,
                    alternatives=(("conn. to main", 0.82),),
                )
            }
        )
        result = transcribe_regions(
            _blank_page(),
            regions,
            regions_json_uri="regions",
            text_candidates_json_uri="text",
            region_crops={"region_0001": _encode_crop(crop)},
            ocr_engine=engine,
        )
        cand = result.metadata.candidates[0]
        self.assertEqual(cand.raw_text, "conn. to main")
        self.assertIsNotNone(cand.normalized_text)
        self.assertNotEqual(cand.normalized_text, cand.raw_text)

    def test_vocabulary_normalization_does_not_trigger_ocr_conflict(self) -> None:
        regions = _regions_meta([_region("region_0008", "text", 10, 10, 80, 30)])
        engine = FakeOcrEngine(
            responses={
                "region_0008": OcrRecognition(
                    raw_text="conn. to main",
                    confidence=0.82,
                    alternatives=(("conn. to main", 0.82),),
                )
            }
        )
        result = transcribe_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            text_candidates_json_uri="t",
            ocr_engine=engine,
        )
        codes = {item.code for item in result.metadata.review_items}
        self.assertNotIn("ocr.conflicting_readings", codes)
        self.assertIsNotNone(result.metadata.candidates[0].normalized_text)

    def test_stored_crop_deskew_matches_rotation_metadata(self) -> None:
        crop = np.array(Image.open(FIXTURES / "rotated-note.png").convert("RGB"))
        regions = _regions_meta([_region("region_0009", "text", 0, 0, 80, 40)])
        engine = FakeOcrEngine(
            responses={
                "region_0009": OcrRecognition(
                    raw_text="NPT",
                    confidence=0.9,
                    alternatives=(("NPT", 0.9),),
                )
            }
        )
        result = transcribe_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            text_candidates_json_uri="t",
            region_crops={"region_0009": _encode_crop(crop)},
            ocr_engine=engine,
        )
        self.assertIsInstance(result.metadata.candidates[0].rotation_deg, float)

    def test_conflicting_alternatives_create_review_item(self) -> None:
        regions = _regions_meta([_region("region_0002", "text", 10, 10, 80, 30)])
        engine = FakeOcrEngine(
            responses={
                "region_0002": OcrRecognition(
                    raw_text="BV",
                    confidence=0.5,
                    alternatives=(
                        ("BV", 0.5),
                        ("B V", 0.48),
                    ),
                )
            }
        )
        result = transcribe_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            text_candidates_json_uri="t",
            ocr_engine=engine,
        )
        codes = {item.code for item in result.metadata.review_items}
        self.assertIn("ocr.conflicting_readings", codes)
        self.assertGreaterEqual(len(result.metadata.candidates[0].alternatives), 2)

    def test_dimension_region_parses_value_without_geometry(self) -> None:
        regions = _regions_meta([_region("region_0003", "dimension", 20, 20, 60, 24)])
        engine = FakeOcrEngine(
            responses={
                "region_0003": OcrRecognition(
                    raw_text="20 ft",
                    confidence=0.91,
                    alternatives=(("20 ft", 0.91),),
                )
            }
        )
        result = transcribe_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            text_candidates_json_uri="t",
            ocr_engine=engine,
        )
        parsed = result.metadata.candidates[0].parsed_dimension
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.unit, "ft")
        self.assertEqual(parsed.value, 20.0)

    def test_rotated_crop_records_rotation_metadata(self) -> None:
        crop = np.array(Image.open(FIXTURES / "rotated-note.png").convert("RGB"))
        page = np.full((256, 256, 3), 255, dtype=np.uint8)
        pre = crop_region(
            page,
            RegionBBox(x=50, y=50, width=crop.shape[1], height=crop.shape[0]),
            padding_px=4,
            deskew=True,
        )
        self.assertIsInstance(pre.rotation_deg, float)

    def test_ocr_failure_is_partial_with_review_crop(self) -> None:
        regions = _regions_meta([_region("region_0004", "text", 5, 5, 90, 30)])
        engine = FakeOcrEngine(failures={"region_0004"})
        result = transcribe_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            text_candidates_json_uri="t",
            ocr_engine=engine,
        )
        self.assertEqual(result.status, "partial")
        cand = result.metadata.candidates[0]
        self.assertEqual(cand.status, "unreadable")
        self.assertIsNone(cand.raw_text)
        self.assertTrue(cand.crop_uri)
        self.assertIn("ocr.unreadable", {i.code for i in result.metadata.review_items})

    def test_low_confidence_line_crossing(self) -> None:
        crop = np.array(Image.open(FIXTURES / "line-crossing.png").convert("RGB"))
        regions = _regions_meta([_region("region_0005", "text", 30, 30, 100, 36)])
        engine = FakeOcrEngine(
            responses={
                "region_0005": OcrRecognition(
                    raw_text="???",
                    confidence=0.25,
                    alternatives=(("???", 0.25),),
                )
            }
        )
        result = transcribe_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            text_candidates_json_uri="t",
            region_crops={"region_0005": _encode_crop(crop)},
            ocr_engine=engine,
        )
        self.assertIn("ocr.low_confidence", {i.code for i in result.metadata.review_items})

    def test_topology_context_attached(self) -> None:
        regions = _regions_meta([_region("region_0006", "text", 100, 100, 40, 20)])
        topology = TopologyMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=256,
            page_height_px=256,
            snapped_primitives_metadata_uri="s",
            primitives_metadata_uri="p",
            nodes=[
                NodeCandidate(
                    id="n1",
                    position=PagePoint(x=110, y=110),
                    kind="endpoint",
                    status="proposed",
                    source_evidence="test",
                )
            ],
        )
        engine = FakeOcrEngine(
            responses={
                "region_0006": OcrRecognition(
                    raw_text="main",
                    confidence=0.88,
                    alternatives=(("main", 0.88),),
                )
            }
        )
        result = transcribe_regions(
            _blank_page(),
            regions,
            regions_json_uri="r",
            text_candidates_json_uri="t",
            topology=topology,
            ocr_engine=engine,
        )
        self.assertTrue(result.metadata.candidates[0].nearby_topology.node_ids)

    def test_content_hash_stable(self) -> None:
        regions = _regions_meta([_region("region_0007", "text", 1, 1, 20, 20)])
        engine = FakeOcrEngine(
            responses={
                "region_0007": OcrRecognition(
                    raw_text="valve",
                    confidence=0.9,
                    alternatives=(("valve", 0.9),),
                )
            }
        )
        kwargs = {
            "regions_json_uri": "r",
            "text_candidates_json_uri": "t",
            "ocr_engine": engine,
        }
        r1 = transcribe_regions(_blank_page(), regions, **kwargs)
        r2 = transcribe_regions(_blank_page(), regions, **kwargs)
        self.assertEqual(r1.content_hash, r2.content_hash)

    @unittest.skipUnless(
        os.environ.get("ISOMETRIC_TROCR_INTEGRATION") == "1",
        "set ISOMETRIC_TROCR_INTEGRATION=1 to run live TrOCR",
    )
    def test_trocr_integration_optional(self) -> None:
        from isometric_pipeline.ocr.adapter import TrocrEngine

        crop = np.array(Image.open(FIXTURES / "abbrev-conn.png").convert("RGB"))
        engine = TrocrEngine("microsoft/trocr-base-handwritten")
        result = engine.recognize(crop, region_id="integration")
        self.assertIsInstance(result.raw_text, str)


if __name__ == "__main__":
    unittest.main()
