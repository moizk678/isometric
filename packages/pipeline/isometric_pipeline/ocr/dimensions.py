"""Parse feet/inches dimension strings without geometry association."""

from __future__ import annotations

import re

from isometric_pipeline.ocr.artifact import ParsedDimensionHint

_FEET_INCH = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*['′]\s*(\d+(?:\.\d+)?)?\s*[\"″]?\s*$")
_FEET_ONLY = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*['′]\s*$")
_INCH_ONLY = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[\"″]\s*$")
_FEET_WORD = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*ft\.?\s*$", re.IGNORECASE)
_AMBIGUOUS_QUOTE = re.compile(r"^\s*['\"″′]\s*$")


def parse_dimension_text(text: str | None) -> ParsedDimensionHint | None:
    if text is None:
        return None
    stripped = text.strip()
    if not stripped:
        return ParsedDimensionHint(
            value=None,
            unit=None,
            display_text="",
            confidence=0.0,
            status="none",
        )
    if _AMBIGUOUS_QUOTE.match(stripped):
        return ParsedDimensionHint(
            value=None,
            unit=None,
            display_text=stripped,
            confidence=0.2,
            status="illegible",
        )

    m = _FEET_INCH.match(stripped)
    if m:
        feet = float(m.group(1))
        inches = float(m.group(2)) if m.group(2) else 0.0
        return ParsedDimensionHint(
            value=feet + inches / 12.0,
            unit="ft",
            display_text=stripped,
            confidence=0.85,
            status="parsed",
        )

    m = _FEET_ONLY.match(stripped)
    if m:
        return ParsedDimensionHint(
            value=float(m.group(1)),
            unit="ft",
            display_text=stripped,
            confidence=0.9,
            status="parsed",
        )

    m = _INCH_ONLY.match(stripped)
    if m:
        return ParsedDimensionHint(
            value=float(m.group(1)),
            unit="in",
            display_text=stripped,
            confidence=0.88,
            status="parsed",
        )

    m = _FEET_WORD.match(stripped)
    if m:
        return ParsedDimensionHint(
            value=float(m.group(1)),
            unit="ft",
            display_text=stripped,
            confidence=0.92,
            status="parsed",
        )

    if "'" in stripped and '"' in stripped:
        return ParsedDimensionHint(
            value=None,
            unit=None,
            display_text=stripped,
            confidence=0.35,
            status="ambiguous",
        )

    return None
