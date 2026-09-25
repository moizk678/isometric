"""Versions stamped into exports and previews, and pinned rasterizer options."""

from __future__ import annotations

from typing import Final

RENDERER_VERSION: Final = "1.0.0"
SYMBOL_LIBRARY_VERSION: Final = "piping-symbols@1.0.0"
CLASSIFIER_SYMBOL_LIBRARY_VERSION: Final = "piping-symbols@1.1.0"
STYLE_PROFILE_VERSION: Final = "piping-default@1.0.0"
RASTERIZER: Final = "resvg-py@0.5.0"

# Keyword names of ``resvg_py.svg_to_bytes`` in resvg-py 0.5.0, read from the
# installed package's ``__init__.pyi``. ``svg_string`` takes ``str``, not bytes.
RESVG_SVG_STRING_KWARG: Final = "svg_string"
RESVG_FONT_FILES_KWARG: Final = "font_files"
RESVG_SKIP_SYSTEM_FONTS_KWARG: Final = "skip_system_fonts"
RESVG_ZOOM_KWARG: Final = "zoom"
RESVG_BACKGROUND_KWARG: Final = "background"
