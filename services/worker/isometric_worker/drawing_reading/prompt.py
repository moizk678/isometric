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

DRAWING_READING_VISION_USER = (
    "Read this isometric drawing. Reply with ONLY the JSON object described in the system "
    "instructions—no markdown, headings, steps, or prose."
)

DRAWING_READING_STRUCTURE_USER_PREFIX = (
    "Convert the following unstructured piping isometric reading notes into the required JSON "
    "object only. Every row must have non-empty location and reading strings.\n\n"
)
