# Run 01 — Semantic scene contract

**Agent brief:** Implement the versioned scene format that every pipeline stage, editor command, and export will use. This is a contract run, not a renderer or database run.

**Depends on:** [Run 00](00-foundation-and-evidence.md). Read architecture sections 3 and 5.

## Build

1. Define `DrawingScene` v1.0 in Python Pydantic models under `packages/pipeline/scene` (or the established equivalent). Generate JSON Schema and TypeScript types into `packages/scene-schema`; make generation repeatable in `make check`.
2. Model immutable-input, orientation-normalized display, and rectified-page dimensions plus 3×3 source/display/page transforms; also model layers, source evidence, pipe segments, junctions, symbols, dimensions, annotations, unknown marks, and non-connectivity relationships. Use stable IDs. Label source points (before EXIF) separately from page points. Keep recognized and normalized text separately and parsed dimensions separate from pixel spans.
3. Implement validation for finite coordinates, invertible transforms, unique IDs, valid references, pipe-endpoint/node consistency, named symbol-port-to-node references, and non-empty evidence for machine interpretations. Pipe connectivity is encoded only by shared endpoint node IDs and symbol ports; a geometric crossing may remain disconnected.
4. Add canonical fixture scenes: one connected route, one crossing without connection, one valve, one annotation, one dimension, and one unresolved mark. Include invalid fixtures for broken references and impossible coordinates.
5. Define schema migration policy: reject unknown major versions, read older supported minor versions, and require an explicit migration function for changes that alter meaning. Document object ID stability across revisions.

## Deliverables

- Python models, generated JSON Schema and TypeScript types, deterministic serialization helpers, and fixtures.
- A short contract note covering coordinate space, evidence, versioning, and invariant errors.

## Exit checks

- A scene serialized in Python validates against generated JSON Schema and parses with the generated TypeScript type in a compile check.
- Every valid fixture passes and each invalid fixture fails with a specific error.
- An unconnected crossing stays unconnected through serialize/deserialize.
- A relationship cannot introduce a second, conflicting connectivity state.
- Generated files are reproducible; `make check` detects stale generated types.

## Out of scope and handoff

Do not render SVG or store scenes in PostgreSQL. Hand off exact schema path, fixture IDs, serialization command, and invariant error codes to [Run 02](02-svg-renderer.md).
