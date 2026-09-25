"""Pipeline stage names and producer versions."""

from __future__ import annotations

STAGE_NORMALIZE_PAGE = "normalize_page"
STAGE_SEPARATE_MASKS = "separate_masks"
STAGE_DETECT_REGIONS = "detect_regions"
STAGE_EXTRACT_CENTERLINES = "extract_centerlines"
STAGE_FIT_PRIMITIVES = "fit_primitives"
STAGE_FIXTURE_PROCESS = "fixture_process"

NORMALIZE_PAGE_VERSION = "normalize_page@1.0.0"
SEPARATE_MASKS_VERSION = "separate_masks@1.0.0"
DETECT_REGIONS_VERSION = "detect_regions@1.0.0"
EXTRACT_CENTERLINES_VERSION = "extract_centerlines@1.0.0"
FIT_PRIMITIVES_VERSION = "fit_primitives@1.0.0"
FIXTURE_PROCESS_VERSION = "fixture@1.0.0"

STAGE_ORDER = (
    STAGE_NORMALIZE_PAGE,
    STAGE_SEPARATE_MASKS,
    STAGE_DETECT_REGIONS,
    STAGE_EXTRACT_CENTERLINES,
    STAGE_FIT_PRIMITIVES,
    STAGE_FIXTURE_PROCESS,
)
