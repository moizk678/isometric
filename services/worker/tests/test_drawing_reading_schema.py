"""Unit tests for drawing reading table validation."""

from __future__ import annotations

import unittest

from isometric_worker.drawing_reading.schema import (
    DrawingReadingValidationError,
    validate_table,
)


class ValidateTableTest(unittest.TestCase):
    def test_rejects_wrong_group_count(self) -> None:
        with self.assertRaises(DrawingReadingValidationError):
            validate_table({"groups": []})

    def test_accepts_minimal_valid_table(self) -> None:
        table = validate_table(
            {
                "groups": [
                    {"id": "dimensions", "title": "Dimensions", "rows": []},
                    {"id": "connections", "title": "Connections", "rows": []},
                    {"id": "components", "title": "Components", "rows": []},
                    {"id": "handwriting", "title": "Other handwriting", "rows": []},
                ]
            }
        )
        self.assertEqual(len(table.groups), 4)


if __name__ == "__main__":
    unittest.main()
