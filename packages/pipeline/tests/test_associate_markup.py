"""Tests for associate_markup stage."""

from __future__ import annotations

import importlib.util
import io
import unittest
import uuid
from pathlib import Path

import cv2
import numpy as np
from isometric_pipeline.associate_markup.artifact import (
    DimensionGeometryCandidate,
    LineSegment,
    PagePoint,
)
from isometric_pipeline.associate_markup.stage import associate_markup
from isometric_pipeline.associate_markup.validate import validate_association_candidates
from isometric_pipeline.ocr.artifact import (
    PageBBox as OcrBBox,
)
from isometric_pipeline.ocr.artifact import (
    ParsedDimensionHint,
    TextCandidate,
    TextCandidatesMetadata,
)
from isometric_pipeline.profiles.loader import (
    DEFAULT_PIPING_PROFILE_VERSION,
    load_piping_profile,
)
from isometric_pipeline.regions.artifact import PageBBox as RegionBBox
from isometric_pipeline.regions.artifact import RegionCandidate, RegionsMetadata
from isometric_pipeline.symbol_candidates.artifact import (
    PageBBox as SymBBox,
)
from isometric_pipeline.symbol_candidates.artifact import (
    PagePoint as SymPoint,
)
from isometric_pipeline.symbol_candidates.artifact import (
    SymbolCandidate,
    SymbolCandidatesMetadata,
    SymbolLabelAlternative,
)
from isometric_pipeline.topology.artifact import (
    EdgeCandidate,
    NodeCandidate,
    TopologyMetadata,
)
from isometric_pipeline.topology.artifact import (
    PagePoint as TopoPoint,
)
from PIL import Image

DOC_ID = "00000000-0000-4000-8000-000000000500"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "associations"


def _ensure_fixtures() -> None:
    if not (FIXTURES / "clean-dimension-page.png").is_file():
        spec = importlib.util.spec_from_file_location(
            "assoc_generate", FIXTURES / "generate.py"
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


def _encode_mask(mask: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(mask, mode="L").save(buf, format="PNG")
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


def _regions_meta(
    regions: list[RegionCandidate], *, h: int = 200, w: int = 320
) -> RegionsMetadata:
    doc = str(uuid.UUID(DOC_ID))
    return RegionsMetadata(
        page_width_px=w,
        page_height_px=h,
        masks_metadata_uri=f"documents/{doc}/masks.json",
        regions=regions,
        protection_mask_uri=f"documents/{doc}/masks/protection.png",
        geometry_ink_mask_uri=f"documents/{doc}/masks/geometry-ink.png",
        warnings=[],
    )


def _topology_horizontal_pipe() -> TopologyMetadata:
    return TopologyMetadata(
        profile_version=DEFAULT_PIPING_PROFILE_VERSION,
        page_width_px=320,
        page_height_px=200,
        snapped_primitives_metadata_uri="s",
        primitives_metadata_uri="p",
        nodes=[
            NodeCandidate(
                id="n1",
                position=TopoPoint(x=40, y=120),
                kind="endpoint",
                status="proposed",
                source_evidence="test",
            ),
            NodeCandidate(
                id="n2",
                position=TopoPoint(x=240, y=120),
                kind="endpoint",
                status="proposed",
                source_evidence="test",
            ),
        ],
        edges=[
            EdgeCandidate(
                id="e_pipe",
                start_node_id="n1",
                end_node_id="n2",
                layer_id="yellow",
                start=TopoPoint(x=40, y=120),
                end=TopoPoint(x=240, y=120),
            )
        ],
    )


class AssociateMarkupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _ensure_fixtures()

    def test_profile_associations_section_loads(self) -> None:
        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION)
        self.assertGreater(profile.associations.max_witness_text_distance_px, 0.0)

    def test_clean_dimension_measures_relationship(self) -> None:
        page = (FIXTURES / "clean-dimension-page.png").read_bytes()
        geom = (FIXTURES / "clean-dimension-geometry.png").read_bytes()
        regions = _regions_meta(
            [
                _region("region_dim", "dimension", 100, 70, 70, 30),
                _region("region_arrow_l", "arrow", 36, 112, 10, 10),
                _region("region_arrow_r", "arrow", 234, 112, 10, 10),
            ]
        )
        text = TextCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=320,
            page_height_px=200,
            regions_metadata_uri="r",
            model={"name": "fake", "revision": None, "preprocessing": {}},
            candidates=[
                TextCandidate(
                    id="txt_dim",
                    region_id="region_dim",
                    region_kind="dimension",
                    bbox=OcrBBox(x=100, y=70, width=70, height=30),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="20 ft",
                    normalized_text="20 ft",
                    parsed_dimension=ParsedDimensionHint(
                        value=20.0,
                        unit="ft",
                        display_text="20 ft",
                        confidence=0.92,
                        status="parsed",
                    ),
                    status="proposed",
                )
            ],
        )
        topology = _topology_horizontal_pipe()
        result = associate_markup(
            page,
            regions,
            regions_json_uri="regions",
            association_candidates_json_uri="assoc",
            geometry_ink_png=geom,
            topology=topology,
            topology_json_uri="topology",
            text_candidates=text,
            text_candidates_json_uri="text",
        )
        self.assertEqual(result.metadata.dimension_candidates[0].display_text, "20 ft")
        self.assertEqual(
            result.metadata.dimension_candidates[0].parsed_dimension.value, 20.0
        )
        measures = [r for r in result.metadata.relationships if r.type == "measures"]
        self.assertTrue(measures)
        self.assertEqual(measures[0].to_ref_id, "e_pipe")

    def test_note_with_leader_callout(self) -> None:
        page = (FIXTURES / "note-leader-page.png").read_bytes()
        geom = (FIXTURES / "note-leader-geometry.png").read_bytes()
        regions = _regions_meta(
            [_region("region_note", "text", 20, 20, 50, 30)],
            h=200,
            w=240,
        )
        text = TextCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=240,
            page_height_px=200,
            regions_metadata_uri="r",
            model={"name": "fake", "revision": None, "preprocessing": {}},
            candidates=[
                TextCandidate(
                    id="txt_note",
                    region_id="region_note",
                    region_kind="text",
                    bbox=OcrBBox(x=20, y=20, width=50, height=30),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="BV",
                    normalized_text="BV",
                    status="proposed",
                )
            ],
        )
        symbols = SymbolCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=240,
            page_height_px=200,
            regions_metadata_uri="r",
            symbol_library_version="piping-symbols@1.1.0",
            classifier={"backend": "fake", "version": "x", "parameters": {}},
            candidates=[
                SymbolCandidate(
                    id="sym_region_valve",
                    region_id="region_valve",
                    region_kind="symbol",
                    bbox=SymBBox(x=108, y=100, width=24, height=24),
                    crop_uri="c",
                    anchor=SymPoint(x=120, y=110),
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
                )
            ],
        )
        result = associate_markup(
            page,
            regions,
            regions_json_uri="r",
            association_candidates_json_uri="a",
            geometry_ink_png=geom,
            text_candidates=text,
            text_candidates_json_uri="t",
            symbol_candidates=symbols,
            symbol_candidates_json_uri="s",
        )
        ann = result.metadata.annotation_targets[0]
        self.assertGreaterEqual(len(ann.leader_polyline), 2)
        rel_types = {r.type for r in result.metadata.relationships}
        self.assertIn("callout_targets", rel_types)

    def test_note_without_leader_review(self) -> None:
        regions = _regions_meta([_region("region_note2", "text", 40, 40, 60, 24)])
        text = TextCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=256,
            page_height_px=256,
            regions_metadata_uri="r",
            model={"name": "fake", "revision": None, "preprocessing": {}},
            candidates=[
                TextCandidate(
                    id="txt_lonely",
                    region_id="region_note2",
                    region_kind="text",
                    bbox=OcrBBox(x=40, y=40, width=60, height=24),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="note",
                    normalized_text="note",
                    status="proposed",
                )
            ],
        )
        symbols = SymbolCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=256,
            page_height_px=256,
            regions_metadata_uri="r",
            symbol_library_version="piping-symbols@1.1.0",
            classifier={"backend": "fake", "version": "x", "parameters": {}},
            candidates=[
                SymbolCandidate(
                    id="sym_far",
                    region_id="region_sym",
                    region_kind="symbol",
                    bbox=SymBBox(x=180, y=160, width=20, height=20),
                    crop_uri="c",
                    anchor=SymPoint(x=190, y=170),
                    rotation_deg=0.0,
                    status="proposed",
                    alternatives=[
                        SymbolLabelAlternative(
                            symbol_id="flange",
                            shape_score=0.7,
                            text_score=0.0,
                            topology_score=0.0,
                        )
                    ],
                )
            ],
        )
        result = associate_markup(
            _blank_page(),
            regions,
            regions_json_uri="r",
            association_candidates_json_uri="a",
            geometry_ink_png=_encode_mask(np.zeros((256, 256), dtype=np.uint8)),
            text_candidates=text,
            text_candidates_json_uri="t",
            symbol_candidates=symbols,
            symbol_candidates_json_uri="s",
        )
        codes = {i.code for i in result.metadata.review_items}
        self.assertIn("annotation.no_leader", codes)

    def test_overlapping_note_pipe_ink_topology_unchanged(self) -> None:
        """Note near pipe ink must not mutate topology (Run 13 exit check)."""
        topology = _topology_horizontal_pipe()
        edge_count = len(topology.edges)
        node_count = len(topology.nodes)
        regions = _regions_meta(
            [
                _region("region_note_pipe", "text", 100, 108, 50, 24),
                _region("region_dim2", "dimension", 90, 60, 80, 30),
            ]
        )
        text = TextCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=320,
            page_height_px=200,
            regions_metadata_uri="r",
            model={"name": "fake", "revision": None, "preprocessing": {}},
            candidates=[
                TextCandidate(
                    id="txt_note_pipe",
                    region_id="region_note_pipe",
                    region_kind="text",
                    bbox=OcrBBox(x=100, y=108, width=50, height=24),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="note",
                    normalized_text="note",
                    status="proposed",
                ),
                TextCandidate(
                    id="txt_dim2",
                    region_id="region_dim2",
                    region_kind="dimension",
                    bbox=OcrBBox(x=90, y=60, width=80, height=30),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="20 ft",
                    normalized_text="20 ft",
                    parsed_dimension=ParsedDimensionHint(
                        value=20.0,
                        unit="ft",
                        display_text="20 ft",
                        confidence=0.9,
                        status="parsed",
                    ),
                    status="proposed",
                ),
            ],
        )
        mask = np.zeros((200, 320), dtype=np.uint8)
        cv2.line(mask, (40, 120), (240, 120), 255, 1)
        cv2.line(mask, (40, 90), (240, 90), 255, 1)
        result = associate_markup(
            _blank_page(320, 200),
            regions,
            regions_json_uri="r",
            association_candidates_json_uri="a",
            geometry_ink_png=_encode_mask(mask),
            topology=topology,
            topology_json_uri="t",
            text_candidates=text,
            text_candidates_json_uri="tx",
        )
        self.assertEqual(len(topology.edges), edge_count)
        self.assertEqual(len(topology.nodes), node_count)
        self.assertTrue(result.metadata.annotation_targets)

    def test_topology_unchanged_after_stage(self) -> None:
        topology = _topology_horizontal_pipe()
        edge_count = len(topology.edges)
        regions = _regions_meta([_region("region_dim2", "dimension", 90, 60, 80, 30)])
        text = TextCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=320,
            page_height_px=200,
            regions_metadata_uri="r",
            model={"name": "fake", "revision": None, "preprocessing": {}},
            candidates=[
                TextCandidate(
                    id="txt_dim2",
                    region_id="region_dim2",
                    region_kind="dimension",
                    bbox=OcrBBox(x=90, y=60, width=80, height=30),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="20 ft",
                    normalized_text="20 ft",
                    parsed_dimension=ParsedDimensionHint(
                        value=20.0,
                        unit="ft",
                        display_text="20 ft",
                        confidence=0.9,
                        status="parsed",
                    ),
                    status="proposed",
                )
            ],
        )
        mask = np.zeros((200, 320), dtype=np.uint8)
        cv2.line(mask, (40, 120), (240, 120), 255, 1)
        associate_markup(
            _blank_page(320, 200),
            regions,
            regions_json_uri="r",
            association_candidates_json_uri="a",
            geometry_ink_png=_encode_mask(mask),
            topology=topology,
            topology_json_uri="t",
            text_candidates=text,
            text_candidates_json_uri="tx",
        )
        self.assertEqual(len(topology.edges), edge_count)

    def test_pixel_span_inconsistent_preserves_parsed_value(self) -> None:
        regions = _regions_meta([_region("region_dim3", "dimension", 100, 70, 40, 20)])
        text = TextCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=320,
            page_height_px=200,
            regions_metadata_uri="r",
            model={"name": "fake", "revision": None, "preprocessing": {}},
            candidates=[
                TextCandidate(
                    id="txt_dim3",
                    region_id="region_dim3",
                    region_kind="dimension",
                    bbox=OcrBBox(x=100, y=70, width=40, height=20),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="20 ft",
                    normalized_text="20 ft",
                    parsed_dimension=ParsedDimensionHint(
                        value=20.0,
                        unit="ft",
                        display_text="20 ft",
                        confidence=0.9,
                        status="parsed",
                    ),
                    status="proposed",
                )
            ],
        )
        mask = np.zeros((200, 320), dtype=np.uint8)
        cv2.line(mask, (40, 120), (80, 120), 255, 1)
        result = associate_markup(
            _blank_page(320, 200),
            regions,
            regions_json_uri="r",
            association_candidates_json_uri="a",
            geometry_ink_png=_encode_mask(mask),
            text_candidates=text,
            text_candidates_json_uri="t",
        )
        dim = result.metadata.dimension_candidates[0]
        self.assertEqual(dim.parsed_dimension.value, 20.0)
        self.assertEqual(dim.parsed_dimension.unit, "ft")

    def test_ambiguous_annotation_targets(self) -> None:
        regions = _regions_meta([_region("region_note3", "text", 20, 20, 40, 20)])
        text = TextCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=256,
            page_height_px=256,
            regions_metadata_uri="r",
            model={"name": "fake", "revision": None, "preprocessing": {}},
            candidates=[
                TextCandidate(
                    id="txt_amb",
                    region_id="region_note3",
                    region_kind="text",
                    bbox=OcrBBox(x=20, y=20, width=40, height=20),
                    crop_uri="c",
                    rotation_deg=0.0,
                    raw_text="?",
                    normalized_text="?",
                    status="proposed",
                )
            ],
        )
        symbols = SymbolCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=256,
            page_height_px=256,
            regions_metadata_uri="r",
            symbol_library_version="piping-symbols@1.1.0",
            classifier={"backend": "fake", "version": "x", "parameters": {}},
            candidates=[
                SymbolCandidate(
                    id="sym_a",
                    region_id="r_a",
                    region_kind="symbol",
                    bbox=SymBBox(x=40, y=30, width=16, height=16),
                    crop_uri="c",
                    anchor=SymPoint(x=48, y=38),
                    rotation_deg=0.0,
                    status="proposed",
                    alternatives=[
                        SymbolLabelAlternative(
                            symbol_id="flange",
                            shape_score=0.8,
                            text_score=0.0,
                            topology_score=0.0,
                        )
                    ],
                ),
                SymbolCandidate(
                    id="sym_b",
                    region_id="r_b",
                    region_kind="symbol",
                    bbox=SymBBox(x=46, y=30, width=16, height=16),
                    crop_uri="c",
                    anchor=SymPoint(x=54, y=38),
                    rotation_deg=0.0,
                    status="proposed",
                    alternatives=[
                        SymbolLabelAlternative(
                            symbol_id="ball_valve",
                            shape_score=0.79,
                            text_score=0.0,
                            topology_score=0.0,
                        )
                    ],
                ),
            ],
        )
        result = associate_markup(
            _blank_page(),
            regions,
            regions_json_uri="r",
            association_candidates_json_uri="a",
            geometry_ink_png=_encode_mask(np.zeros((256, 256), dtype=np.uint8)),
            text_candidates=text,
            text_candidates_json_uri="t",
            symbol_candidates=symbols,
            symbol_candidates_json_uri="s",
        )
        ann = result.metadata.annotation_targets[0]
        self.assertGreaterEqual(len(ann.alternatives), 2)
        codes = {i.code for i in result.metadata.review_items}
        self.assertIn("annotation.ambiguous_target", codes)

    def test_validate_rejects_bad_reference(self) -> None:
        from isometric_pipeline.associate_markup.artifact import (
            AssociationCandidatesMetadata,
            DimensionCandidate,
            TargetRef,
        )

        meta = AssociationCandidatesMetadata(
            profile_version=DEFAULT_PIPING_PROFILE_VERSION,
            page_width_px=100,
            page_height_px=100,
            regions_metadata_uri="r",
            dimension_candidates=[
                DimensionCandidate(
                    id="dim_x",
                    text_candidate_id="txt_x",
                    region_id="region_x",
                    display_text="1 ft",
                    witness_start=PagePoint(x=0, y=0),
                    witness_end=PagePoint(x=10, y=0),
                    target_refs=[
                        TargetRef(
                            ref_kind="topology_edge",
                            ref_id="missing_edge",
                            score=0.5,
                        )
                    ],
                    status="proposed",
                )
            ],
        )
        errors = validate_association_candidates(
            meta,
            text_candidate_ids={"txt_x"},
            region_ids={"region_x"},
            topology_edge_ids=set(),
            topology_node_ids=set(),
            symbol_candidate_ids=set(),
        )
        self.assertTrue(errors)

    def test_content_hash_stable(self) -> None:
        regions = _regions_meta([_region("region_dim4", "dimension", 80, 60, 60, 24)])
        kwargs = {
            "regions_json_uri": "r",
            "association_candidates_json_uri": "a",
            "geometry_ink_png": _encode_mask(np.zeros((200, 320), dtype=np.uint8)),
        }
        r1 = associate_markup(_blank_page(320, 200), regions, **kwargs)
        r2 = associate_markup(_blank_page(320, 200), regions, **kwargs)
        self.assertEqual(r1.content_hash, r2.content_hash)

    def test_injected_geometry_candidate(self) -> None:
        geo = DimensionGeometryCandidate(
            id="dim_geo_test",
            witness_line=LineSegment(
                start=PagePoint(x=10, y=50),
                end=PagePoint(x=100, y=50),
            ),
            arrowhead_points=[PagePoint(x=10, y=50), PagePoint(x=100, y=50)],
            evidence="unit test geometry",
        )
        from isometric_pipeline.associate_markup.dimensions import (
            build_dimension_candidates,
        )

        profile = load_piping_profile(DEFAULT_PIPING_PROFILE_VERSION).associations
        text = TextCandidate(
            id="txt_g",
            region_id="region_g",
            region_kind="dimension",
            bbox=OcrBBox(x=40, y=30, width=40, height=20),
            crop_uri="c",
            rotation_deg=0.0,
            raw_text="20 ft",
            normalized_text="20 ft",
            parsed_dimension=ParsedDimensionHint(
                value=20.0,
                unit="ft",
                display_text="20 ft",
                confidence=0.9,
                status="parsed",
            ),
            status="proposed",
        )
        dims, _ = build_dimension_candidates(
            [text], [geo], _topology_horizontal_pipe(), profile
        )
        self.assertEqual(dims[0].geometry_candidate_id, "dim_geo_test")


if __name__ == "__main__":
    unittest.main()
