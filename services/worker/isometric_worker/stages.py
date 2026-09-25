"""Pipeline stage names and producer versions."""

from __future__ import annotations

STAGE_NORMALIZE_PAGE = "normalize_page"
STAGE_FIXTURE_PROCESS = "fixture_process"

NORMALIZE_PAGE_VERSION = "normalize_page@1.0.0"
FIXTURE_PROCESS_VERSION = "fixture@1.0.0"

STAGE_ORDER = (STAGE_NORMALIZE_PAGE, STAGE_FIXTURE_PROCESS)
