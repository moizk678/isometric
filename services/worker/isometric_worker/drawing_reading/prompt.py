"""Prompt for drawing reading providers."""

from __future__ import annotations

DRAWING_READING_SYSTEM = """You read piping isometric drawings and return a JSON object only.

The JSON must match this shape exactly:
{
  "groups": [
    {"id": "dimensions", "title": "Dimensions", "rows": [{"location": "...", "reading": "..."}]},
    {"id": "connections", "title": "Connections", "rows": []},
    {"id": "components", "title": "Components", "rows": []},
    {"id": "handwriting", "title": "Other handwriting", "rows": []}
  ]
}

Rules:
- Include all four groups in order with the exact id and title values shown.
- Each row has non-empty location (spatial phrase) and reading (transcribed text, units included).
- Put measured lengths or offsets in dimensions; joins, nozzles, branch notes in connections;
  valves, fittings, equipment labels in components; any other handwriting in handwriting.
- Empty rows arrays are valid. Keep duplicate rows when the drawing repeats an item.
- No extra fields, coordinates, or commentary outside the JSON object.
"""
