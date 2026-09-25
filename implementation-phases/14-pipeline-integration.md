# Run 14 — Pipeline orchestration and scene assembly

**Agent brief:** Replace the fixture job path with the deterministic image/OCR pipeline and publish a validated semantic revision.

**Depends on:** [Runs 03–04 and 06–13](13-dimensions-associations.md). Read architecture sections 2, 5, 8, and 9.

## Build

1. Orchestrate stages in dependency order with immutable input/output artifact manifests and pinned producer/profile/model versions. A failed later stage must not overwrite earlier artifacts or the current reviewed revision.
2. Assemble pipe segments, junctions, symbols, annotations, dimensions, unknown marks, layers, and relationships into the Run 01 schema. Preserve source evidence and pre-snap geometry.
3. Resolve only nonconflicting candidates with sufficient evidence. Before Run 17 calibration, every engineering-critical interpretation remains review-required even when its provisional score is high. Keep ambiguous topology, text, symbol, and associations as review items with alternatives and source crops.
4. Validate the scene, render SVG/preview through Run 02, write immutable artifacts, then publish the new revision with one conditional PostgreSQL transaction through Run 03. Object storage is outside that transaction; orphan artifacts are reconciled later.
5. Expose job state and revision review state separately through Run 04. Reprocessing creates a separate machine candidate branch and leaves a reviewed current revision untouched; adoption/merge is an explicit reviewer action in Run 15.
6. Add an end-to-end diagnostic command for one image that emits the stage manifest, scene, SVG, preview, and unresolved list.

## Deliverables

- Real pipeline worker path, scene assembler, review planner, reprocess behavior, and a one-image diagnostic run.

## Exit checks

- A synthetic end-to-end sketch reaches a validated scene and editable SVG; available real images are used for observational checks, with no accuracy claim unless labeled.
- Forced stage or database-publication failure preserves original and prior revision; retry resumes or reruns deterministically without duplicate revisions, and orphan artifacts are discoverable for cleanup.
- Every machine scene object has source evidence; all references validate; unresolved crossings remain unresolved.
- Export XML and raster preview pass renderer checks; job reports true terminal state and warnings.

## Out of scope and handoff

Do not add provider vision calls or production calibration. Hand off end-to-end command, sample artifacts, unresolved-item types, and known regressions to [Run 15](15-review-editor.md).
