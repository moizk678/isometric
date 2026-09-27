"""Workers AI response parsing."""

from __future__ import annotations

import json
import unittest

from isometric_worker.drawing_reading.providers.workers_ai import _extract_workers_text


class WorkersAiExtractTest(unittest.TestCase):
    def test_string_response(self) -> None:
        payload = {"result": {"response": '{"groups": []}'}}
        self.assertEqual(_extract_workers_text(payload), '{"groups": []}')

    def test_dict_response_with_groups(self) -> None:
        groups = [{"id": "dimensions", "title": "Dimensions", "rows": []}]
        payload = {"result": {"response": {"groups": groups}}}
        text = _extract_workers_text(payload)
        self.assertIsNotNone(text)
        parsed = json.loads(text or "")
        self.assertEqual(parsed["groups"], groups)


if __name__ == "__main__":
    unittest.main()
