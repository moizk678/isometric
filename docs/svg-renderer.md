# SVG renderer (export 1.0.0)

Run 02 turns a validated **DrawingScene** into safe, editable SVG and an optional PNG preview. Implementation lives in `packages/pipeline/isometric_pipeline/render/`. The renderer never infers connectivity: pipes meet only at shared junction IDs and symbol ports declared in the scene.

## Entry points

```python
from isometric_pipeline.render import (
    STYLE_PROFILE_VERSION,
    SYMBOL_LIBRARY_VERSION,
    render_svg,
    validate_svg,
    rasterize_preview,
    get_style_profile,
    load_symbol_library,
)
```

### `render_svg(scene, symbol_library_version, style_profile_version) -> RenderResult`

Renders `scene` to UTF-8 SVG bytes with LF line endings. The scene is validated with `validate_scene` and the loaded symbol library as catalog before drawing. Identical inputs produce identical bytes and the same `sha256` on `RenderResult`.

`RenderResult` carries `svg`, `sha256`, `metadata` (`ExportMetadata`), and `unresolved` items drawn in the `unresolved` group (unknown junctions, unresolved symbol ports, unknown marks). `render_svg` calls `validate_svg` on the output before returning.

Default versions (see `versions.py`): renderer **1.0.0**, symbol library **piping-symbols@1.0.0**, style **piping-default@1.0.0**.

### `validate_svg(svg, scene, style) -> None`

Parses `svg` with a restricted expat handler (no DOCTYPE, entities, notations, or processing instructions). Checks element and attribute allowlists, numeric bounds, local `href` / `url(#…)` targets, and semantic consistency with `scene` and `style`. Raises `RenderError` with structured `RenderIssue` entries if anything fails.

### `rasterize_preview(svg, *, scale=1.0, overlay_svg=None) -> PreviewResult`

Rasterizes export SVG to PNG with **resvg-py@0.5.0**. Uses only the bundled **Liberation Sans** font file and `skip_system_fonts=True`, so preview pixels do not depend on host fonts; a missing font file raises `RASTERIZE_FAILED` instead of dropping text. Optional `overlay_svg` is composited for review or paper overlays in previews only; overlays are not part of the exported SVG and are rejected by `validate_svg` on exports.

Both documents must be self-contained: a DOCTYPE or processing instruction raises `SVG_XML_INVALID`, and any `href` other than a local `#id` or a `data:image/{png,jpeg,gif,webp}` URI raises `SVG_EXTERNAL_REFERENCE`, because resvg would otherwise read image files from the host by path.

`PreviewResult` includes `png`, `sha256`, `rasterizer`, and `font` (`LiberationSans-Regular.ttf@sha256:…`).

## Version metadata block

The root `<svg>` contains a `<metadata>` child with compact JSON (fixed key order, no URIs):

| JSON key | Meaning |
| --- | --- |
| `schemaVersion` | Scene `schemaVersion` |
| `documentId` | Scene `documentId` |
| `revisionId` | Scene `revisionId` |
| `rendererVersion` | Renderer semver (`1.0.0`) |
| `symbolLibraryVersion` | Loaded symbol library version string |
| `styleProfileVersion` | Resolved style profile version |
| `unresolvedCount` | Count of items in the `unresolved` group |

Pinned toolchain versions: symbol library **piping-symbols@1.0.0**, style **piping-default@1.0.0**, rasterizer **resvg-py@0.5.0**. Bundled preview font SHA-256: `76d04c18ea243f426b7de1f3ad208e927008f961dc5945e5aad352d0dfde8ee8`.

## Symbol library and ports

Scenes reference symbols by `symbolId` against `packages/symbol-library/piping-symbols-1.0.0.json`. Port names and geometry are frozen in [packages/symbol-library/CONTRACT.md](../packages/symbol-library/CONTRACT.md).

| Symbol ID | Ports | Required |
| --- | --- | --- |
| `ball_valve` | `inlet`, `outlet` | both |
| `tee_fitting` | `run_a`, `run_b`, `branch` | all three |
| `elbow_fitting` | `a`, `b` | both |
| `endpoint` | `pipe` | yes |
| `unknown` | `port_1` … `port_4` | none (all optional) |

Only symbols used by the scene are defined under `<defs>`. Each is `<symbol id="sym-{id}" overflow="visible">`; instances are `<use href="#sym-{id}">` in the `symbols` group.

**Structural vs explicit fittings:** tee and elbow **junctions** formed only by meeting pipe endpoints render as pipe geometry. A `tee_fitting` or `elbow_fitting` **symbol object** appears only when the scene includes that symbol. The `structural-junctions` fixture has corners with no duplicate fitting symbol.

## Render order and groups

Top-level groups are emitted in this fixed order (see `GROUP_IDS` in `allowlist.py`):

1. **`pipes`** — For each layer sorted by layer ID, pipe segments on that layer (live objects sorted by object ID). One nested `<g id="layer-{layerId}">` per layer with stroke color from the layer.
2. **`connections`** — Junction markers. A filled connection dot is drawn only when the junction’s connection **degree** is at least 3 (pipe endpoints plus non-null symbol port attachments). Unknown junctions at degree ≥ 3 get a dot without duplicating the unresolved ring.
3. **`symbols`** — `<use>` elements for live symbol objects, in live object ID order.
4. **`dimensions`** — Witness lines, arrow markers, and dimension text.
5. **`callouts`** — Callout geometry and leader text.
6. **`annotations`** — Free text annotations.
7. **`unresolved`** — Unknown junction rings, unresolved port rings, and unknown marks.

Objects with `interpretation.state: "rejected"` are omitted. Each rendered object has `id="obj-{uuid}"`, `data-object-id`, and `data-state`. User text and metadata are XML-escaped; metacharacters cannot inject markup.

## Connectivity rules

Connectivity is **only** what the scene encodes:

- Pipe `startNodeId` / `endNodeId` sharing a junction, and symbol `portNodeIds` pointing at junctions (or `null` for explicitly unresolved ports).
- Geometric crossings without a shared junction remain disconnected: no connection dot at the crossing (`crossing-unconnected`). A junction at the crossing with degree 4 gets a dot (`crossing-connected`).
- Relationships never imply pipe connectivity (Run 01 invariant).
- A non-rejected pipe or symbol port attached to a **rejected** junction raises `SCENE_INVALID`. Omitting the junction would otherwise draw its pipes as disconnected.

The renderer does not add pipes, junctions, symbols, or ports to “complete” a drawing.

## Font substitution

Export SVG sets `font-family` on text from the style profile:

`Arial, Helvetica, 'Liberation Sans', sans-serif`

Editors on typical desktops resolve Arial or Helvetica. The PNG preview does not use system fonts: resvg loads only `packages/symbol-library/fonts/LiberationSans-Regular.ttf` with system font lookup disabled, so preview text uses Liberation Sans while staying aligned with the export family list.

## Commands

Render and check golden SVG/PNG pairs for every valid scene fixture:

```sh
# Regenerate committed goldens under packages/pipeline/tests/golden/render/
PYTHONPATH=packages/pipeline .venv/bin/python -m isometric_pipeline.render.golden

# CI gate: render to a temp dir and compare (also run by ./scripts/check)
PYTHONPATH=packages/pipeline .venv/bin/python -m isometric_pipeline.render.golden --check
```

SVG goldens must match **byte for byte**. PNG goldens allow per-channel drift up to **2** on each RGBA channel (`PNG_CHANNEL_TOLERANCE` in `golden.py`) so anti-aliasing differences between platforms do not churn goldens.

**Preview one fixture in Python** (after `load_scene` with the symbol catalog):

```python
from pathlib import Path
from isometric_pipeline.scene import load_scene
from isometric_pipeline.render import (
    SYMBOL_LIBRARY_VERSION,
    STYLE_PROFILE_VERSION,
    load_symbol_library,
    render_svg,
    rasterize_preview,
)

library = load_symbol_library(SYMBOL_LIBRARY_VERSION)
scene = load_scene(
    Path("packages/scene-schema/fixtures/valid/valve-inline.json").read_text(),
    catalog=library,
)
result = render_svg(scene, SYMBOL_LIBRARY_VERSION, STYLE_PROFILE_VERSION)
preview = rasterize_preview(result.svg, scale=1.0)
Path("preview.png").write_bytes(preview.png)
```

Full repo gate (Ruff, scene-schema check, golden `--check`, tests): `./scripts/check`.

## Deferred to later runs

| Topic | Run |
| --- | --- |
| Persisting exports and previews in object storage | 03 |
| Review overlays in the workbench (preview-only groups) | 03+ |
| Profile-specific rendering thresholds beyond validator defaults | 12 |
