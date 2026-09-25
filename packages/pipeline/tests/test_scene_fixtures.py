"""Table-driven checks for hand-written scene-schema fixtures."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from isometric_pipeline.scene import (
    IssueCode,
    SceneValidationError,
    dump_scene,
    load_scene,
)
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "scene-schema/fixtures"
VALID_DIR = FIXTURES / "valid"
INVALID_DIR = FIXTURES / "invalid"
SCHEMA_PATH = REPO_ROOT / "scene-schema/drawing-scene.schema.json"
EXPECTED_PATH = FIXTURES / "expected.json"

VALID_FIXTURES = tuple(sorted(VALID_DIR.glob("*.json")))
INVALID_EXPECTED: tuple[tuple[str, str], ...] = tuple(
    sorted(json.loads(EXPECTED_PATH.read_text(encoding="utf-8")).items())
)


class FixtureSymbolCatalog:
    """Minimal catalog for fixtures that reference fixture_two_port_valve."""

    _VALVE_ID = "fixture_two_port_valve"
    _PORTS = frozenset({"inlet", "outlet"})

    def port_names(self, symbol_id: str) -> frozenset[str] | None:
        if symbol_id == self._VALVE_ID:
            return self._PORTS
        return None

    def required_ports(self, symbol_id: str) -> frozenset[str]:
        if symbol_id == self._VALVE_ID:
            return self._PORTS
        return frozenset()


def _issue_code_set(exc: SceneValidationError) -> frozenset[IssueCode]:
    return frozenset(exc.codes)


class SceneFixturesTest(unittest.TestCase):
    catalog = FixtureSymbolCatalog()

    @classmethod
    def setUpClass(cls) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls._jsonschema_validator = Draft202012Validator(schema)

    def test_valid_fixtures_load_with_invariants(self) -> None:
        for path in VALID_FIXTURES:
            with self.subTest(fixture=path.stem):
                text = path.read_text(encoding="utf-8")
                scene = load_scene(text, catalog=self.catalog)
                self.assertIsNotNone(scene)

    def test_valid_fixtures_match_json_schema(self) -> None:
        for path in VALID_FIXTURES:
            with self.subTest(fixture=path.stem):
                payload = json.loads(path.read_text(encoding="utf-8"))
                errors = sorted(
                    self._jsonschema_validator.iter_errors(payload),
                    key=lambda err: list(err.absolute_path),
                )
                self.assertEqual(
                    [],
                    errors,
                    msg="\n".join(error.message for error in errors),
                )

    def test_python_serialized_fixtures_match_json_schema(self) -> None:
        for path in VALID_FIXTURES:
            with self.subTest(fixture=path.stem):
                scene = load_scene(path.read_text(encoding="utf-8"))
                payload = json.loads(dump_scene(scene))
                errors = sorted(
                    self._jsonschema_validator.iter_errors(payload),
                    key=lambda err: list(err.absolute_path),
                )
                self.assertEqual(
                    [],
                    errors,
                    msg="\n".join(error.message for error in errors),
                )

    def test_every_invalid_fixture_has_an_expected_code(self) -> None:
        self.assertEqual(
            sorted(path.stem for path in INVALID_DIR.glob("*.json")),
            [stem for stem, _ in INVALID_EXPECTED],
        )

    def test_valid_fixtures_have_no_confirmed_interpretations(self) -> None:
        for path in VALID_FIXTURES:
            with self.subTest(fixture=path.stem):
                scene = load_scene(path.read_text(encoding="utf-8"))
                owners = [*scene.objects, *scene.relationships]
                self.assertEqual(
                    [o.id for o in owners if o.interpretation.state == "confirmed"],
                    [],
                )

    def test_invalid_fixtures_raise_exactly_expected_code(self) -> None:
        for stem, expected_code in INVALID_EXPECTED:
            path = INVALID_DIR / f"{stem}.json"
            with self.subTest(fixture=stem, expected=expected_code):
                text = path.read_text(encoding="utf-8")
                with self.assertRaises(SceneValidationError) as ctx:
                    load_scene(text, catalog=self.catalog)
                actual = _issue_code_set(ctx.exception)
                expected = frozenset({IssueCode(expected_code)})
                if actual != expected:
                    self.fail(
                        f"{stem}: expected codes {sorted(c.value for c in expected)}, "
                        f"got {sorted(c.value for c in actual)}"
                    )


if __name__ == "__main__":
    unittest.main()
