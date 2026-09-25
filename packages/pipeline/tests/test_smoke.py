import json
import unittest
from pathlib import Path

from isometric_pipeline import __version__

FIXTURES = Path(__file__).resolve().parents[2] / "evaluation/fixtures/synthetic"


class PipelineSmokeTest(unittest.TestCase):
    def test_import(self):
        self.assertEqual(__version__, "0.0.0")

    def test_transform_fixture_has_invertible_matrices(self):
        cases = json.loads((FIXTURES / "transforms.json").read_text())
        for case in cases["cases"]:
            matrix = case["source_to_page"]
            determinant = (
                matrix[0][0]
                * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
                - matrix[0][1]
                * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
                + matrix[0][2]
                * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
            )
            with self.subTest(case=case["id"]):
                self.assertNotEqual(determinant, 0)
                source_to_display = case["source_to_display"]
                display_to_page = case["display_to_page"]
                composed = [
                    [
                        sum(
                            display_to_page[row][k] * source_to_display[k][col]
                            for k in range(3)
                        )
                        for col in range(3)
                    ]
                    for row in range(3)
                ]
                self.assertEqual(composed, matrix)
