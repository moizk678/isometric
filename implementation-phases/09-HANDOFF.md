# Run handoff — 09 Isometric axis inference and geometry snapping

**Run file:** `implementation-phases/09-axis-snapping.md`  
**Status:** complete (local verification via `./scripts/test-pipeline`)  
**Next run:** `10-topology.md`

## Delivered

- **Profile:** `snapping` thresholds in [`profiles/piping_isometric@1.0.0.yaml`](../profiles/piping_isometric@1.0.0.yaml); loader extended in [`profiles/loader.py`](../packages/pipeline/isometric_pipeline/profiles/loader.py).
- **Pipeline:** `snap_primitives` in [`snapping/`](../packages/pipeline/isometric_pipeline/snapping/) (`axes.py`, `snap.py`, `align.py`, `stage.py`, diagnostics).
- **Worker:** [`processor.py`](../services/worker/isometric_worker/processor.py) runs `snap_primitives` after `fit_primitives`; [`stages.py`](../services/worker/isometric_worker/stages.py) order updated. Fixture scene publication unchanged.
- **Persistence keys:** `axes.json`, `snapped-primitives.json` in [`keys.py`](../packages/persistence/isometric_persistence/keys.py).
- **Tests:** [`test_axis_snapping.py`](../packages/pipeline/tests/test_axis_snapping.py), fixtures under [`axis-snapping/`](../packages/pipeline/tests/fixtures/axis-snapping/).
- **Docs:** [`docs/axis-snapping.md`](../docs/axis-snapping.md).

## Contract changes

- New stage run: `snap_primitives` with artifacts `documents/{id}/axes.json` and `documents/{id}/snapped-primitives.json`.
- `primitives.json` stays immutable pre-snap; snapped geometry and decision log live in `snapped-primitives.json`.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/test-pipeline` | Pass | Includes `test_axis_snapping` (10 tests); 210 pipeline tests total |
| `./scripts/test-api` | Run locally | Worker runs `snap_primitives` before fixture publish |
| `./scripts/check` | Run locally | ruff + full suite when `SUPABASE_DATABASE_URL` set |

## Data used

- Synthetic axis-snapping PNG fixtures and programmatic rotated-triad primitives. No real drawings.

## Remaining work and risks

- Grid-assisted rotation uses Hough on `grid.png`; mask-only grid estimate from Run 07 may be noisy on sparse grids.
- Intersection-heavy skeletons can fragment into short edges before snapping; topology merge is Run 10.
- Snap thresholds are initial defaults; calibration deferred to Run 17.

## Next-run starting point

- Read [`10-topology.md`](10-topology.md), [`docs/axis-snapping.md`](../docs/axis-snapping.md).
- Consume `snapped-primitives.json` candidates with `status=snapped`; preserve uncertain endpoints and crossing alternatives.
