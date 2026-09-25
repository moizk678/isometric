# DrawingScene contract (schema 1.0)

Run 01 defines the versioned **DrawingScene** wire format: camelCase JSON validated by Pydantic, cross-object invariants in `validate_scene`, canonical serialization via `load_scene` / `dump_scene`, and a generated JSON Schema plus TypeScript types under `packages/scene-schema`. This note summarizes behavior implemented in `packages/pipeline/isometric_pipeline/scene/`.

## Coordinate spaces and transforms

Each scene carries three pixel spaces and four row-major **3×3** homogeneous transforms on `page`:

| Space | Size fields | Point type | Role |
| --- | --- | --- | --- |
| **Raw source** | `sourceWidthPx`, `sourceHeightPx` | `SourcePoint` | Immutable input pixels **before** EXIF orientation; evidence polygons live here. |
| **Display** | `displayWidthPx`, `displayHeightPx` | (implicit via matrices) | **Orientation-normalized** view of the source after EXIF; not used directly on objects except through transforms. |
| **Rectified page** | `widthPx`, `heightPx` | `PagePoint` | The **rectified page** where geometry is edited and rendered (pipes, junctions, symbols, annotations, dimensions). |

The four transforms (each exactly nine finite numbers, row-major):

- **`sourceToDisplay` / `displayToSource`** — EXIF orientation between raw source and display.
- **`sourceToPage` / `pageToSource`** — homography (or identity pipeline step) from source into the rectified page.

Invariants require each matrix to be non-singular (non-zero determinant) and each forward/inverse pair to multiply to a scaled identity within **1e−9** after normalizing homogeneous scale. Page points must lie in `[0, widthPx] × [0, heightPx]`; source points in the source rectangle.

## Evidence and interpretation

Every object and relationship carries an **`interpretation`**: `state` (`machine` | `confirmed` | `rejected` | `unknown`), optional calibrated `score` in `[0, 1]`, and `evidence`.

**Evidence** entries require a `sourcePolygon` of at least three `SourcePoint`s, non-empty `stage` and `artifactId` (artifact IDs are opaque strings, not scene UUID references), and an `observations` map of string keys to number, string, or boolean values.

**Machine interpretations must have non-empty `evidence`.** Empty evidence on `state: "machine"` raises `MACHINE_EVIDENCE_MISSING`. Confirmed objects are allowed without extra invariant checks in Run 01; **review events for confirmed objects are deferred to Runs 03 and 15** (architecture §5 still describes the long-term rule).

**Text:** annotations store **`recognizedText`** (what was read from the drawing) and **`normalizedText`** (canonical form for matching and display). Both are validated for XML-safe character ranges (`TEXT_INVALID_CHARACTER`).

**Dimensions:** **`parsedValue`** and **`unit`** are optional parsed semantics; they are **independent** of the pixel **`witnessStart` / `witnessEnd`** span on the page. Relationships of type `measures` must align with `targetObjectIds` on the dimension (see issue codes below).

## Connectivity

Connectivity is expressed **only** by:

- pipe **`startNodeId` / `endNodeId`** referencing junction objects, with endpoints coinciding with junction **`position`** within tolerance (default **1e−6 px**, overridable via `endpoint_tolerance_px` on `validate_scene` / `load_scene`), and
- symbol **`portNodeIds`**: port name → junction ID, or **`null`** when a port is explicitly unresolved (see below).

**Relationships must not encode a second connectivity graph.** If both ends of a relationship resolve to a `pipe_segment`, `junction`, or `symbol`, validation raises `RELATIONSHIP_CONNECTIVITY_FORBIDDEN`. Semantic links use types `annotates`, `measures`, and `callout_targets` from annotations or dimensions to other objects.

A **geometric crossing** may remain **disconnected**: two pipes can intersect in page space while using **distinct** endpoint junction IDs and no connecting relationship (fixture `crossing-unconnected`).

## Versioning and migration

- **`schemaVersion`** is a `"major.minor"` string; the supported contract is **`1.0`** (`SCENE_SCHEMA_VERSION`).
- **`check_version`** rejects an unknown **major** (anything other than `1`) or a **minor greater than** the supported minor (`0`). Missing or malformed `schemaVersion` is `SCHEMA_INVALID`.
- **`MIGRATIONS`** is an empty registry at `1.0`. Future **meaning-changing** schema edits must register an explicit migration function keyed by `(major, minor)` rather than silently rewriting wire data.

`load_scene` runs: finite-number scan → `check_version` → Pydantic → `validate_scene`.

## ID stability

Object, layer, relationship, and node IDs are stable lowercase UUIDs. **Revisions may change fields without changing an object’s ID.** Deletion **tombstones** and revision event logs belong to **Run 03**, not Run 01; this run does not model tombstones on the wire.

## Nullable symbol ports (extension to architecture §5)

Architecture §5 shows `portNodeIds` as name → junction ID. Run 01 extends that map to **`Record<portName, junctionId | null>`**: **`null` means the port is explicitly unresolved** (required catalog ports may appear with a `null` value). When a **`SymbolCatalog`** is supplied to validation, unknown `symbolId` values, unknown port names, and missing required port keys are checked; unresolved ports do not require a junction reference.

## Validation issue codes

`SceneValidationError` lists every issue in a stable order. Codes are defined in `errors.py`:

| Code | When it is raised |
| --- | --- |
| `SCHEMA_INVALID` | Wire JSON is not an object, Pydantic schema violation, or invalid/missing `schemaVersion` shape (non-version cases). |
| `VERSION_UNSUPPORTED` | Unsupported `schemaVersion` major or minor newer than supported. |
| `NON_FINITE_NUMBER` | `NaN`, `Infinity`, or non-finite float anywhere in the document (including pre-Pydantic JSON parse). |
| `COORDINATE_OUT_OF_BOUNDS` | A `PagePoint` or `SourcePoint` lies outside its page or source rectangle. |
| `TRANSFORM_SINGULAR` | A page transform matrix has determinant zero. |
| `TRANSFORM_INVERSE_MISMATCH` | `sourceToDisplay`×`displayToSource` or `sourceToPage`×`pageToSource` is not identity within 1e−9 after scale normalization. |
| `DUPLICATE_ID` | The same ID appears on more than one layer, object, or relationship. |
| `UNKNOWN_REFERENCE` | A referenced layer, object, or junction ID does not exist, or `symbolId` is absent from the supplied catalog. |
| `WRONG_REFERENCE_TYPE` | A reference exists but points at the wrong kind (e.g. pipe endpoint not a junction). |
| `PIPE_ENDPOINT_MISMATCH` | A pipe endpoint `PagePoint` is farther than `endpoint_tolerance_px` from its junction position. |
| `PIPE_DEGENERATE` | Same start and end node, or zero geometric length within tolerance. |
| `SYMBOL_PORT_UNKNOWN_NAME` | A key in `portNodeIds` is not a catalog port name for that symbol. |
| `SYMBOL_REQUIRED_PORT_MISSING` | A catalog-required port name is missing from `portNodeIds`. |
| `MACHINE_EVIDENCE_MISSING` | `interpretation.state` is `machine` but `evidence` is empty. |
| `TEXT_INVALID_CHARACTER` | A string field contains a character outside XML-permitted ranges. |
| `RELATIONSHIP_CONNECTIVITY_FORBIDDEN` | Both relationship endpoints are pipe, junction, or symbol types. |
| `RELATIONSHIP_INVALID_ENDPOINTS` | `fromId` is not an annotation (for `annotates` / `callout_targets`) or dimension (for `measures`). |
| `DIMENSION_TARGET_MISMATCH` | A `measures` edge or a `targetObjectIds` entry lacks a matching paired relationship. |

**Profile-specific endpoint tolerances** (per piping profile) are **Run 12**; until then the validator default is **1e−6 px**.

## Commands

Regenerate JSON Schema, TypeScript types, and fixture exports (from repo root):

```sh
PYTHONPATH=packages/pipeline .venv/bin/python -m isometric_pipeline.scene.generate
```

Verify generated artifacts are fresh and TypeScript compiles:

```sh
./scripts/check-scene-schema
```

Full repo gate (includes the above after Ruff): `./scripts/check`.

## Deferred to later runs

| Topic | Run |
| --- | --- |
| Review events for **confirmed** interpretations | 03, 15 |
| Profile endpoint tolerances (beyond default 1e−6 px) | 12 |
| Deletion tombstones and revision event log | 03 |
