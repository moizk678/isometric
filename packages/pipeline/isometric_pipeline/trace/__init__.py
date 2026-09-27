"""Raster-faithful SVG trace export."""

from isometric_pipeline.trace.artifact import PRODUCER_VERSION, TRACE_VERSION
from isometric_pipeline.trace.stage import TraceInkResult, trace_ink
from isometric_pipeline.trace.validate import TraceSvgError, validate_trace_svg

__all__ = [
    "PRODUCER_VERSION",
    "TRACE_VERSION",
    "TraceInkResult",
    "TraceSvgError",
    "trace_ink",
    "validate_trace_svg",
]
