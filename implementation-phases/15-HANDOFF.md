# Run handoff — 15 Review editor

**Run file:** `implementation-phases/15-review-editor.md`  
**Status:** complete (local verification via targeted tests; run full `./scripts/check` before release)  
**Next run:** `16-vision-ambiguity.md`

## Delivered

- **Scene edits:** `packages/pipeline/isometric_pipeline/scene/edits/` — command models and `apply_edits`.
- **Review policy:** `packages/pipeline/isometric_pipeline/review/` — carry-forward, readiness, confirmed overlay on reprocess.
- **API:** `POST .../edits`, `.../review-items/{id}/resolve`, `.../adopt`; enriched review-items payload; [`human_revision.py`](../services/api/isometric_api/human_revision.py).
- **Persistence:** `insert_review_event`, `promote_revision_to_current`, full review-item insert fields.
- **Worker:** confirmed-object overlay when `advance_current_revision=false`.
- **Web:** properties panel, review confirm/unknown, If-Match mutations, draft SVG label.
- **Docs:** [`docs/review-editor.md`](../docs/review-editor.md).

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/test-pipeline` | Pass | Includes `test_scene_edits`, `test_review_policy`, `test_review_overlay` |
| `discover test_revision_edits.py` | Pass | If-Match 428, edit revision, stale 409 (requires local Postgres) |
| `./scripts/test-web` | Pass | Vitest 64 tests |

## Remaining work and risks

- Adopt/compare UI is minimal; expand candidate diff in a follow-up if needed.
- Graph connect tool in the browser is limited to disconnect via properties; full connect mode can be added later.
- Playwright E2E not re-run in this session; `./scripts/check` runs the full suite.

## Next-run starting point

- Read `16-vision-ambiguity.md` and keep edit commands the single source of scene changes.
