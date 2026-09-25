# Run handoff — 02 Deterministic SVG renderer

**Run file:** `implementation-phases/02-svg-renderer.md`
**Status:** complete locally; hosted CI not yet recorded (orchestrator will push after this handoff).
**Next run:** `03-supabase-persistence.md`

## Delivered

- **Renderer package** under `packages/pipeline/isometric_pipeline/render/`: `render_svg`, `validate_svg`, `rasterize_preview`, style profiles, symbol loader, SVG allowlist and safety validator, structured `RenderError` / `RenderIssue` codes, and pinned versions in `versions.py`.
- **Symbol library** `packages/symbol-library/piping-symbols-1.0.0.json` with contract note [packages/symbol-library/CONTRACT.md](../packages/symbol-library/CONTRACT.md) and bundled Liberation Sans for previews.
- **Golden exports:** every valid scene fixture under `packages/scene-schema/fixtures/valid/` renders to committed SVG and PNG under `packages/pipeline/tests/golden/render/`, checked by `isometric_pipeline.render.golden --check` (wired into `./scripts/check`).
- **Fixtures:** five additional valid scenes (`callout`, `crossing-connected`, `explicit-tee-fitting`, `structural-junctions`, `text-metacharacters`) plus updated `valve-inline`; render expectations in `packages/pipeline/tests/render_fixtures.py` and exit-check tests in `test_render_exit_checks.py`.
- **Contract note:** [docs/svg-renderer.md](../docs/svg-renderer.md), linked from [README.md](../README.md).

## Contract changes

- **`valve-inline` fixture:** `symbolId` changed from `fixture_two_port_valve` to **`ball_valve`** (same `inlet` / `outlet` ports and geometry intent).
- **Frozen export versions:** renderer **1.0.0**, symbol library **piping-symbols@1.0.0**, style **piping-default@1.0.0**, rasterizer **resvg-py@0.5.0**, preview font SHA-256 **`76d04c18ea243f426b7de1f3ad208e927008f961dc5945e5aad352d0dfde8ee8`** (`LiberationSans-Regular.ttf`).

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/check` | Pass | After Wave 2: Ruff lint/format, `./scripts/check-scene-schema`, `golden --check`, API/pipeline/evaluation/web tests; exit 0. |
| `PYTHONPATH=packages/pipeline .venv/bin/python -m isometric_pipeline.render.golden --check` | Pass | Byte-identical SVG goldens; PNG within channel tolerance 2. |
| `./scripts/test-pipeline` | Pass | **167** pipeline tests (render, safety, preview, symbols, scene contract). |
| Evaluation / web | Pass | **6** evaluation tests, **1** web test (via `./scripts/check`). |
| Run 02 exit checks (`02-svg-renderer.md`) | Pass | All valid fixtures render, `validate_svg`, and rasterize; deterministic checksums; disconnected crossing; no duplicate fitting at structural junctions; text metacharacters escaped; per-object SVG groups. |

## Data used

- **Synthetic scene fixtures only** under `packages/scene-schema/fixtures/valid/` (and inline builders in `packages/pipeline/tests/`). No real drawings were rendered or used for golden baselines.

## Remaining work and risks

- **Hosted CI:** this run’s commit is not yet recorded on `origin/main`; confirm the Check workflow after push.
- **Run 03:** persistence, artifact URLs, and preview delivery in the API/worker are still out of scope for Run 02.
- Synthetic goldens do not prove extraction or recognition quality on real sketches (Run 17).

## Next-run starting point

- Read [docs/svg-renderer.md](../docs/svg-renderer.md) and [packages/symbol-library/CONTRACT.md](../packages/symbol-library/CONTRACT.md).
- **Entry points for stored artifacts:** `render_svg`, `rasterize_preview`, and CI golden check `PYTHONPATH=packages/pipeline .venv/bin/python -m isometric_pipeline.render.golden --check`.
- **Supported symbol IDs:** `ball_valve`, `tee_fitting`, `elbow_fitting`, `endpoint`, `unknown` (ports per CONTRACT).
- **Preview:** `rasterize_preview(result.svg, scale=1.0)` with bundled Liberation Sans and system fonts disabled; export text uses `Arial, Helvetica, 'Liberation Sans', sans-serif`.
- **Regression gate:** `./scripts/check` (includes golden `--check`).

**Valid fixture IDs (11):** `annotation`, `callout`, `connected-route`, `crossing-connected`, `crossing-unconnected`, `dimension`, `explicit-tee-fitting`, `structural-junctions`, `text-metacharacters`, `unresolved-mark`, `valve-inline`.

**Testing note:** crossing pixel tests sample the **diagonal neighbors** of page point `(100, 100)`, not the intersection pixel itself, because both crossing fixtures paint the center with the 2 px pipe stroke; only the connected fixture’s degree-4 junction draws ink in those offset pixels.

## Commands

```sh
# Full repo gate (includes render golden --check)
./scripts/check

# Regenerate or verify render goldens only
PYTHONPATH=packages/pipeline .venv/bin/python -m isometric_pipeline.render.golden
PYTHONPATH=packages/pipeline .venv/bin/python -m isometric_pipeline.render.golden --check
```

**Rendering (Python):**

```python
from isometric_pipeline.render import (
    STYLE_PROFILE_VERSION,
    SYMBOL_LIBRARY_VERSION,
    render_svg,
    rasterize_preview,
)
```
