# Run handoff — 10 Junction and pipe topology hypotheses

**Run file:** `implementation-phases/10-topology.md`  
**Status:** complete (local verification via `./scripts/test-pipeline`)  
**Next run:** `11-handwriting-ocr.md`

## Delivered

- **Profile:** `topology` thresholds in [`profiles/piping_isometric@1.0.0.yaml`](../profiles/piping_isometric@1.0.0.yaml); `TopologyProfile` in [`profiles/loader.py`](../packages/pipeline/isometric_pipeline/profiles/loader.py).
- **Pipeline:** `infer_topology` in [`topology/`](../packages/pipeline/isometric_pipeline/topology/) (`segments`, `endpoints`, `intersections`, `merge`, `hypotheses`, `build`, `validate`, `stage`, diagnostics).
- **Worker:** [`processor.py`](../services/worker/isometric_worker/processor.py) runs `infer_topology` after `snap_primitives`; [`stages.py`](../services/worker/isometric_worker/stages.py) order updated. Fixture scene publication unchanged.
- **Persistence keys:** `topology.json` in [`keys.py`](../packages/persistence/isometric_persistence/keys.py).
- **Tests:** [`test_topology.py`](../packages/pipeline/tests/test_topology.py), fixtures under [`topology/`](../packages/pipeline/tests/fixtures/topology/).
- **Docs:** [`docs/topology.md`](../docs/topology.md).

## Contract changes

- New stage run: `infer_topology` with artifact `documents/{id}/topology.json`.
- Candidate graph with nodes, edges, intersection hypotheses, and topology review items; validated before write.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/test-pipeline` | Pass | Includes `test_topology` (9 tests) |
| `./scripts/test-api` | Run locally | Worker runs `infer_topology` before fixture publish |
| `./scripts/check` | Run locally | ruff + full suite when `SUPABASE_DATABASE_URL` set |

## Data used

- Synthetic topology PNG fixtures and programmatic snapped-primitive graphs. No real drawings.

## Remaining work and risks

- Gap-style crossings (broken ink at the intersection) rely on segment pairs that still produce an interior intersection; multi-segment routes may need route-level crossing detection in a follow-up.
- Topology thresholds are initial defaults; calibration deferred to Run 17.
- Review items are artifact-only until Run 14 publishes DB review rows.

## Next-run starting point

- Read [`11-handwriting-ocr.md`](11-handwriting-ocr.md), [`docs/topology.md`](../docs/topology.md).
- Use `topology.json` node/edge IDs and crossing review codes as context for OCR and symbol stages.
