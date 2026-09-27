"""Safety validation for trace SVG exports."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from xml.parsers import expat

_TRACE_ELEMENTS = frozenset({"svg", "metadata", "g", "path"})
_TRACE_ATTRS: dict[str, frozenset[str]] = {
    "svg": frozenset({"xmlns", "viewBox", "width", "height"}),
    "metadata": frozenset(),
    "g": frozenset({"id"}),
    "path": frozenset(
        {
            "id",
            "d",
            "fill",
            "stroke",
            "stroke-width",
            "stroke-linecap",
            "stroke-linejoin",
        }
    ),
}
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_PATH_DATA = re.compile(r"[MmLlHhVvZzAaCcSsQqTt0-9eE.,+\-\s]*")
_PAINT = re.compile(r"none|#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?")


class TraceSvgError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class _Frame:
    name: str
    forbidden: bool = False


def validate_trace_svg(svg: bytes, *, width_px: int, height_px: int) -> None:
    if b"<!DOCTYPE" in svg[:256] or svg.lstrip().startswith(b"<?"):
        if svg.lstrip().startswith(b"<?") and not svg.lstrip().startswith(
            b"<?xml"
        ):
            raise TraceSvgError("processing instructions are forbidden")
    issues: list[str] = []
    stack: list[_Frame] = []

    def start(name: str, attrs: list[str]) -> None:
        if name.startswith("{"):
            local = name.split("}", 1)[1]
        elif " " in name:
            local = name.split(" ", 1)[1]
        else:
            local = name
        if local not in _TRACE_ELEMENTS:
            issues.append(f"forbidden element: {local}")
            stack.append(_Frame(local, forbidden=True))
            return
        allowed = _TRACE_ATTRS[local]
        if isinstance(attrs, dict):
            attr_map = attrs
        else:
            attr_map = dict(zip(attrs[0::2], attrs[1::2], strict=True))
        for key, value in attr_map.items():
            if key not in allowed:
                issues.append(f"forbidden attribute {key} on {local}")
                continue
            if key in {"width", "height", "stroke-width"}:
                _check_number(value, key, non_negative=True)
            if key == "d":
                if not _PATH_DATA.fullmatch(value):
                    issues.append("invalid path data")
                _check_path_bounds(value, width_px, height_px, issues)
            if key in {"fill", "stroke"} and not _PAINT.fullmatch(value):
                issues.append(f"invalid paint on {key}")
        stack.append(_Frame(local))

    def end(name: str) -> None:
        if stack:
            stack.pop()

    parser = expat.ParserCreate(namespace_separator=" ")
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = lambda *_: (_ for _ in ()).throw(
        TraceSvgError("DOCTYPE is forbidden")
    )
    try:
        parser.Parse(svg, True)
    except TraceSvgError:
        raise
    except expat.ExpatError as exc:
        raise TraceSvgError(f"XML parse error: {exc}") from exc

    if issues:
        raise TraceSvgError("; ".join(issues[:8]))


def _check_number(value: str, name: str, *, non_negative: bool) -> None:
    if not _NUMBER.fullmatch(value):
        raise TraceSvgError(f"invalid number for {name}")
    num = float(value)
    if not math.isfinite(num):
        raise TraceSvgError(f"non-finite number for {name}")
    if non_negative and num < 0:
        raise TraceSvgError(f"negative number for {name}")


def _check_path_bounds(
    d: str, width_px: int, height_px: int, issues: list[str]
) -> None:
    nums = [float(x) for x in _NUMBER.findall(d)]
    if len(nums) < 2:
        return
    xs = nums[0::2]
    ys = nums[1::2]
    pad = max(width_px, height_px) * 0.05 + 4.0
    if min(xs) < -pad or max(xs) > width_px + pad:
        issues.append("path x out of bounds")
    if min(ys) < -pad or max(ys) > height_px + pad:
        issues.append("path y out of bounds")
