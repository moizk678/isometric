"""Strict four-group drawing reading table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DRAWING_READING_SCHEMA_VERSION = "drawing-reading@1"
PROMPT_VERSION = "drawing-reading@1"

GROUP_SPECS: tuple[tuple[str, str], ...] = (
    ("dimensions", "Dimensions"),
    ("connections", "Connections"),
    ("components", "Components"),
    ("handwriting", "Other handwriting"),
)


@dataclass(frozen=True)
class DrawingReadingRow:
    location: str
    reading: str


@dataclass(frozen=True)
class DrawingReadingGroup:
    id: str
    title: str
    rows: tuple[DrawingReadingRow, ...]


@dataclass(frozen=True)
class DrawingReadingTable:
    groups: tuple[DrawingReadingGroup, ...]


class DrawingReadingValidationError(ValueError):
    pass


def _require_str(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise DrawingReadingValidationError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise DrawingReadingValidationError(f"{field} must be non-empty")
    return text


def _require_mapping(value: object, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DrawingReadingValidationError(f"{field} must be an object")
    return value


def validate_table(payload: object) -> DrawingReadingTable:
    root = _require_mapping(payload, field="payload")
    allowed_root = {"groups"}
    extra_root = set(root) - allowed_root
    if extra_root:
        raise DrawingReadingValidationError(f"unexpected fields: {sorted(extra_root)}")

    groups_raw = root.get("groups")
    if not isinstance(groups_raw, list):
        raise DrawingReadingValidationError("groups must be an array")
    if len(groups_raw) != len(GROUP_SPECS):
        raise DrawingReadingValidationError("groups must contain exactly four entries")

    groups: list[DrawingReadingGroup] = []
    for index, (expected_id, expected_title) in enumerate(GROUP_SPECS):
        group_obj = _require_mapping(groups_raw[index], field=f"groups[{index}]")
        allowed_group = {"id", "title", "rows"}
        extra_group = set(group_obj) - allowed_group
        if extra_group:
            raise DrawingReadingValidationError(
                f"groups[{index}] unexpected fields: {sorted(extra_group)}"
            )
        group_id = _require_str(group_obj.get("id"), field=f"groups[{index}].id")
        title = _require_str(group_obj.get("title"), field=f"groups[{index}].title")
        if group_id != expected_id or title != expected_title:
            raise DrawingReadingValidationError(
                f"groups[{index}] must be {expected_id!r} / {expected_title!r}"
            )
        rows_raw = group_obj.get("rows")
        if not isinstance(rows_raw, list):
            raise DrawingReadingValidationError(f"groups[{index}].rows must be an array")
        rows: list[DrawingReadingRow] = []
        for row_index, row_obj in enumerate(rows_raw):
            row = _require_mapping(row_obj, field=f"groups[{index}].rows[{row_index}]")
            allowed_row = {"location", "reading"}
            extra_row = set(row) - allowed_row
            if extra_row:
                raise DrawingReadingValidationError(
                    f"groups[{index}].rows[{row_index}] unexpected fields: "
                    f"{sorted(extra_row)}"
                )
            location = _require_str(
                row.get("location"),
                field=f"groups[{index}].rows[{row_index}].location",
            )
            reading = _require_str(
                row.get("reading"),
                field=f"groups[{index}].rows[{row_index}].reading",
            )
            rows.append(DrawingReadingRow(location=location, reading=reading))
        groups.append(
            DrawingReadingGroup(id=group_id, title=title, rows=tuple(rows))
        )
    return DrawingReadingTable(groups=tuple(groups))


def table_to_json(table: DrawingReadingTable) -> dict[str, Any]:
    return {
        "groups": [
            {
                "id": group.id,
                "title": group.title,
                "rows": [
                    {"location": row.location, "reading": row.reading}
                    for row in group.rows
                ],
            }
            for group in table.groups
        ]
    }
