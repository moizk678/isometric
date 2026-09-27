# Run handoff — 14 Pipeline integration

**Run file:** `implementation-phases/14-pipeline-integration.md`  
**Status:** complete (local verification via `./scripts/check`)  
**Next run:** `15-review-editor.md`

## Delivered

- **Assembly:** `packages/pipeline/isometric_pipeline/scene_assembly/` — page/layers, topology, symbols, text, associations, review planner, `assemble_scene`, local diagnostic runner.
- **Profile:** `assembly` section in `profiles/piping_isometric@1.0.0.yaml`.
- **Worker:** `assemble_scene` stage in `services/worker/isometric_worker/processor.py`; `ISOMETRIC_WORKER_FIXTURE_ONLY=1` keeps fixture path for API tests.
- **Persistence:** `RevisionPublisher.advance_current_revision`; `job_pipeline_manifest_key`; publish policy for reprocess candidates.
- **API:** `POST /api/v1/documents/{id}/reprocess`.
- **CLI:** `scripts/run-pipeline-diagnostic`.
- **Docs:** `docs/pipeline-integration.md`.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/test-pipeline` | Pass | Includes `test_scene_assembly` and local pipeline smoke |
| `./scripts/test-persistence` | Pass | `advance_current_revision=False` test when DB available |
| `./scripts/check` | Pass | Full repo checks |

## Remaining work and risks

- End-to-end quality on real sketches unmeasured until Run 17.
- Job manifest currently summarizes assembly stage; extend with full stage_run replay in Run 19 if needed.
- Review editor adoption of reprocess candidates is Run 15.

## Next-run starting point

- Read `15-review-editor.md`, `docs/pipeline-integration.md`, and revision review item APIs.
