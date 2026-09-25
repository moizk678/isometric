# Run 07 — Grid, ink, color, and protected regions

**Agent brief:** Separate likely drawing ink from paper/grid and propose text/symbol/dimension regions without discarding ambiguous pixels.

**Depends on:** [Run 06](06-page-normalization.md). Read architecture stages for grid/color separation and region detection.

## Build

1. Implement background/grid estimates using lightness, color, line width/orientation, and periodicity. Emit a grid mask, retained-ink mask, and diagnostic overlay. If confidence is low, keep the original ink rather than erasing geometry.
2. Cluster colored strokes in LAB/HSV and form stable color-layer candidates with source and normalized colors. Keep grayscale/black ink and a residual unclassified-ink mask.
3. Propose text, symbol, arrow, and dimension regions with boxes/polygons and scores. Use heuristic or detector adapters; this run does not transcribe or classify them.
4. Generate a geometry-protection mask so handwriting and symbols do not become route centerlines, but preserve their original crops for later OCR/classification.
5. Emit typed artifacts with stage/provenance versions, mask dimensions, coordinate space, and quality warnings. Keep mask combinations reproducible.

## Deliverables

- Grid/ink/color/protection masks, candidate region list, visual diagnostics, and synthetic plus available real-image fixtures.

## Exit checks

- A faint grid fixture loses grid pixels while retaining overlapping strong route strokes; a dark-grid case falls back without destructive removal.
- Colored routes remain distinguishable from black annotations in fixture diagnostics.
- Every suppressed region has an accessible source crop/evidence reference; no pixel disappears without a recorded mask decision.
- Output masks match the rectified page dimensions and pass `make test-pipeline`.

## Out of scope and handoff

Do not claim production grid-removal accuracy without labeled pages. Do not read text or choose symbol types. Hand off exact mask semantics and crop IDs to [Run 08](08-centerlines-and-primitives.md).
