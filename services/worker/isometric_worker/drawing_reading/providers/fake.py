"""Test double for drawing reading providers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..schema import table_to_json, validate_table


def _sample_table() -> dict[str, Any]:
    table = validate_table(
        {
            "groups": [
                {
                    "id": "dimensions",
                    "title": "Dimensions",
                    "rows": [
                        {
                            "location": "bottom center",
                            "reading": '6"-150#',
                        }
                    ],
                },
                {"id": "connections", "title": "Connections", "rows": []},
                {"id": "components", "title": "Components", "rows": []},
                {"id": "handwriting", "title": "Other handwriting", "rows": []},
            ]
        }
    )
    return table_to_json(table)


@dataclass
class FakeProviderOutcome:
    body: str | None
    error: str | None = None
    status: int = 200


class FakeDrawingReadingProviders:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.workers_calls = 0
        self.gemini_calls = 0

    def call_workers(self, *, image_bytes: bytes) -> FakeProviderOutcome:
        del image_bytes
        self.workers_calls += 1
        if self.mode == "valid":
            return FakeProviderOutcome(body=json.dumps({"groups": _sample_table()["groups"]}))
        if self.mode == "invalid_then_valid":
            return FakeProviderOutcome(body='{"groups": []}')
        if self.mode == "workers_error":
            return FakeProviderOutcome(body=None, error="workers_failed", status=502)
        if self.mode == "fail":
            return FakeProviderOutcome(body=None, error="workers_failed", status=502)
        return FakeProviderOutcome(body=json.dumps({"groups": _sample_table()["groups"]}))

    def call_gemini(self, *, image_bytes: bytes) -> FakeProviderOutcome:
        del image_bytes
        self.gemini_calls += 1
        if self.mode in {"fail", "workers_error"}:
            return FakeProviderOutcome(body=None, error="gemini_failed", status=502)
        if self.mode == "invalid_then_valid":
            return FakeProviderOutcome(body=json.dumps({"groups": _sample_table()["groups"]}))
        return FakeProviderOutcome(body=json.dumps({"groups": _sample_table()["groups"]}))
