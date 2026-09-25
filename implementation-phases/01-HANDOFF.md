# Run handoff — 01 Semantic scene contract

**Run file:** `implementation-phases/01-scene-contract.md`
**Status:** complete locally and on hosted CI after gate push to `origin/main`.
**Next run:** `02-svg-renderer.md`

## Delivered

- **DrawingScene v1.0** Pydantic models under `packages/pipeline/isometric_pipeline/scene/` with cross-object invariants in `validate_scene`, version checks in `check_version`, and stable issue codes in `errors.py`.
- **Generated contract artifacts:** JSON Schema at `packages/scene-schema/drawing-scene.schema.json`, TypeScript types at `packages/scene-schema/src/drawing-scene.ts`, and exported fixture JSON under `packages/scene-schema/fixtures/`. Regeneration is deterministic via `isometric_pipeline.scene.generate`.
- **Serialization:** `load_scene` and `dump_scene` in `isometric_pipeline.scene` (canonical JSON, byte-stable round trips on valid fixtures).
- **Fixtures:** six valid scenes and ten invalid stems (expected primary codes in `packages/scene-schema/fixtures/expected.json`).
- **Contract note:** [docs/scene-contract.md](../docs/scene-contract.md), linked from [README.md](../README.md).
- **Tests:** schema validation of Python-serialized output, invalid-fixture coverage, unconnected crossing round-trip, relationship connectivity forbiddance, stale-generated-artifact detection in `./scripts/check-scene-schema`.

## Contract changes

- **DrawingScene schema version `1.0`** (`SCENE_SCHEMA_VERSION`): camelCase wire JSON with raw source, orientation-normalized display, and rectified page spaces; four row-major 3×3 transforms; layers, objects (pipes, junctions, symbols, dimensions, annotations, unknown marks), and semantic relationships (`annotates`, `measures`, `callout_targets` only—no connectivity graph on relationships).
- **Connectivity** is encoded only by shared pipe endpoint junction IDs and symbol `portNodeIds`; geometric crossings may remain disconnected (fixture `crossing-unconnected`).
- **Nullable `portNodeIds` values:** architecture §5 shows port name → junction ID; Run 01 extends this to **`Record<portName, junctionId | null>`** where **`null` means explicitly unresolved** (required catalog ports may appear with a `null` value without referencing a junction).
- **Migration policy:** reject unknown major versions and unsupported newer minors; `MIGRATIONS` registry is empty at 1.0—meaning-changing edits require an explicit migration function later.
- **Deferred (documented, not implemented):** review events for confirmed interpretations (Runs 03 and 15); profile-specific endpoint tolerances beyond validator default **1e−6 px** (Run 12); external SVG/script rejection (Run 02 renderer—wire text is already XML-safe).

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `PYTHONPATH=packages/pipeline .venv/bin/python -m isometric_pipeline.scene.generate` | Pass | Regenerated schema, types, and fixture exports; exit 0. |
| `./scripts/check-scene-schema` | Pass | `--check` on generate plus `tsc --noEmit` for `@isometric/scene-schema`; exit 0. |
| `./scripts/test-pipeline` | Pass | 82 pipeline tests including fixtures, invariants, serialization, and generation staleness; exit 0. |
| `./scripts/check` | Pass | Ruff, scene-schema check, API/pipeline/evaluation/web tests; exit 0. |
| Run 01 exit checks (`01-scene-contract.md`) | Pass | Python output validates against JSON Schema and TS compile check; valid/invalid fixtures; unconnected crossing serialize/deserialize; relationships cannot imply connectivity; generated files reproducible. |

## Data used

- **Synthetic scene fixtures only** under `packages/scene-schema/fixtures/` (and Python builders in `packages/pipeline/isometric_pipeline/scene/fixtures/`). These establish contract behavior, not real-sketch accuracy.
- Run 00 synthetic PNG evidence fixtures unchanged; no real drawings were used in scene tests.

## Schema paths and fixture IDs

| Artifact | Path |
|---|---|
| JSON Schema | `packages/scene-schema/drawing-scene.schema.json` |
| TypeScript types | `packages/scene-schema/src/drawing-scene.ts` |

**Valid fixture IDs:** `connected-route`, `crossing-unconnected`, `valve-inline`, `annotation`, `dimension`, `unresolved-mark`.

**Invalid fixture stems** (primary expected code in `packages/scene-schema/fixtures/expected.json`): `broken-reference`, `non-finite-coordinate`, `out-of-bounds-coordinate`, `singular-transform`, `duplicate-id`, `missing-machine-evidence`, `pipe-endpoint-mismatch`, `relationship-connectivity`, `unknown-major-version`, `unknown-object-type`.

## Issue codes (`packages/pipeline/isometric_pipeline/scene/errors.py`)

`SceneValidationError` raises one or more `SceneIssue` entries with these `IssueCode` values:

- **Structure and version:** `SCHEMA_INVALID`, `VERSION_UNSUPPORTED`
- **Numbers and coordinates:** `NON_FINITE_NUMBER`, `COORDINATE_OUT_OF_BOUNDS`
- **Transforms:** `TRANSFORM_SINGULAR`, `TRANSFORM_INVERSE_MISMATCH`
- **IDs and references:** `DUPLICATE_ID`, `UNKNOWN_REFERENCE`, `WRONG_REFERENCE_TYPE`
- **Pipes:** `PIPE_ENDPOINT_MISMATCH`, `PIPE_DEGENERATE`
- **Symbols:** `SYMBOL_PORT_UNKNOWN_NAME`, `SYMBOL_REQUIRED_PORT_MISSING`
- **Evidence and text:** `MACHINE_EVIDENCE_MISSING`, `TEXT_INVALID_CHARACTER`
- **Relationships:** `RELATIONSHIP_CONNECTIVITY_FORBIDDEN`, `RELATIONSHIP_INVALID_ENDPOINTS`, `DIMENSION_TARGET_MISMATCH`

## Commands

```sh
# Regenerate schema, types, and fixture JSON
PYTHONPATH=packages/pipeline .venv/bin/python -m isometric_pipeline.scene.generate

# CI gate for generated artifacts + TypeScript compile
./scripts/check-scene-schema

# Full repo gate (includes the above)
./scripts/check
```

**Serialization (Python):**

```python
from isometric_pipeline.scene import load_scene, dump_scene
```

## Remaining work and risks

- **Run 02:** SVG renderer must consume validated scenes only; no PostgreSQL persistence yet.
- **Runs 03 / 15:** confirmed-interpretation review events and revision/tombstone modeling remain out of scope for Run 01.
- **Run 12:** piping-profile endpoint tolerances; until then use validator default **1e−6 px** (`endpoint_tolerance_px` on `load_scene` / `validate_scene`).
- Synthetic fixtures do not prove extraction quality on real sketches; Run 17 remains the accuracy gate.

## Next-run starting point

- Read [docs/scene-contract.md](../docs/scene-contract.md) and load valid fixtures from `packages/scene-schema/fixtures/valid/`.
- Implement Run 02 per [02-svg-renderer.md](02-svg-renderer.md): render page-space geometry from `DrawingScene` without inventing connectivity; reject or ignore out-of-contract external scripts per that run’s scope.
- Use `./scripts/check-scene-schema` and `./scripts/check` after changes; keep generation deterministic with `isometric_pipeline.scene.generate`.
