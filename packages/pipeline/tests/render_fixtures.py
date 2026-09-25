"""Expected render properties for valid scene fixtures (Wave 2 golden tests)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALID_DIR = REPO_ROOT / "scene-schema/fixtures/valid"

# Page-pixel sample coordinates for crossing fixtures (200×200 page):
# - crossing-unconnected: pipes cross at (100, 100) with no junction there.
# - crossing-connected: shared crossing junction at (100, 100); degree 4 → connection dot.

CROSSING_SAMPLE_POINT: tuple[float, float] = (100.0, 100.0)

TEXT_METACHAR_STRING = '<script>"&]]>'


@dataclass(frozen=True)
class RenderFixtureExpectation:
    sample_point: tuple[float, float] | None
    expect_ink_at_sample: bool | None
    expected_use_count: int
    round_trip_texts: tuple[str, ...]


RENDER_FIXTURE_EXPECTATIONS: dict[str, RenderFixtureExpectation] = {
    "annotation": RenderFixtureExpectation(
        sample_point=None,
        expect_ink_at_sample=None,
        expected_use_count=0,
        round_trip_texts=(),
    ),
    "callout": RenderFixtureExpectation(
        sample_point=None,
        expect_ink_at_sample=None,
        expected_use_count=0,
        round_trip_texts=(),
    ),
    "connected-route": RenderFixtureExpectation(
        sample_point=None,
        expect_ink_at_sample=None,
        expected_use_count=0,
        round_trip_texts=(),
    ),
    "crossing-connected": RenderFixtureExpectation(
        sample_point=CROSSING_SAMPLE_POINT,
        expect_ink_at_sample=True,
        expected_use_count=0,
        round_trip_texts=(),
    ),
    "crossing-unconnected": RenderFixtureExpectation(
        sample_point=CROSSING_SAMPLE_POINT,
        expect_ink_at_sample=False,
        expected_use_count=0,
        round_trip_texts=(),
    ),
    "dimension": RenderFixtureExpectation(
        sample_point=None,
        expect_ink_at_sample=None,
        expected_use_count=0,
        round_trip_texts=(),
    ),
    "explicit-tee-fitting": RenderFixtureExpectation(
        sample_point=None,
        expect_ink_at_sample=None,
        expected_use_count=1,
        round_trip_texts=(),
    ),
    "structural-junctions": RenderFixtureExpectation(
        sample_point=None,
        expect_ink_at_sample=None,
        expected_use_count=0,
        round_trip_texts=(),
    ),
    "text-metacharacters": RenderFixtureExpectation(
        sample_point=None,
        expect_ink_at_sample=None,
        expected_use_count=0,
        round_trip_texts=(TEXT_METACHAR_STRING,),
    ),
    "unresolved-mark": RenderFixtureExpectation(
        sample_point=None,
        expect_ink_at_sample=None,
        expected_use_count=0,
        round_trip_texts=(),
    ),
    "valve-inline": RenderFixtureExpectation(
        sample_point=None,
        expect_ink_at_sample=None,
        expected_use_count=1,
        round_trip_texts=(),
    ),
}


def valid_fixture_stems() -> tuple[str, ...]:
    return tuple(sorted(path.stem for path in VALID_DIR.glob("*.json")))


def assert_expectations_cover_valid_fixtures() -> None:
    stems = valid_fixture_stems()
    missing = [stem for stem in stems if stem not in RENDER_FIXTURE_EXPECTATIONS]
    extra = [stem for stem in RENDER_FIXTURE_EXPECTATIONS if stem not in stems]
    if missing or extra:
        raise AssertionError(
            f"render fixture map mismatch: missing={missing!r} extra={extra!r}"
        )
