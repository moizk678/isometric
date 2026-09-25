# Run 06 — Safe image ingestion and page normalization

**Agent brief:** Produce a canonical rectified page and invertible source/page transforms, with a safe fallback for uncertain photographs.

**Depends on:** [Run 04](04-upload-and-jobs.md) and the scene coordinate contract in [Run 01](01-scene-contract.md). Read architecture sections 2–3.

## Build

1. Implement a stage that decodes PNG/JPEG under byte and decoded-pixel limits, preserves the immutable original and raw decoded dimensions, applies EXIF orientation for analysis, and emits RGB/LAB/grayscale images.
2. Emit an orientation-normalized display derivative and its source/display transform. Estimate page corners with OpenCV, order corners consistently, compose orientation and rectification into the 3×3 raw-source-to-page homography, and calculate all inverses. Rectify only when quality checks pass. Otherwise emit an unrectified page with an orientation-only source/page transform and a warning.
3. Record page-boundary confidence evidence, blur/contrast/shadow diagnostics, image hashes, stage version, and transform metadata. Coordinates in later stages must use rectified page pixels.
4. Expose diagnostics to local tests or stage artifacts: corner overlay, rectified image, and warnings. Never silently crop away source marks.
5. Wire this stage into the worker manifest and retry policy without yet changing fixture scene publication.

## Deliverables

- `normalize_page` stage and typed output artifact, transform utilities, diagnostic preview, and fixture images.

## Exit checks

- Round-trip raw-source→display→raw-source and raw-source→page→raw-source mappings stay within a defined pixel tolerance on synthetic perspective and EXIF-rotated fixtures.
- Rotated JPEG, clean scan, skewed page, no-visible-boundary photo, and corrupt image have deterministic outcomes.
- Low-confidence page detection preserves all image content and emits a review/quality warning.
- Original bytes and checksum never change; `make test-pipeline` passes.

## Out of scope and handoff

Do not remove grids or fit lines. Hand off page artifact schema, transform examples, warning codes, and limits to [Run 07](07-masks-and-regions.md).
