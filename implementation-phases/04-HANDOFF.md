# Run handoff — 04 Upload and jobs

**Run file:** `implementation-phases/04-upload-and-jobs.md`
**Status:** complete locally
**Next run:** `05-web-foundation.md`

## Delivered

- **API:** [`services/api/isometric_api/`](services/api/isometric_api/) — FastAPI `/api/v1` upload, documents, jobs, revisions, scene, review-items, exports, source download.
- **Worker:** [`services/worker/isometric_worker/`](services/worker/isometric_worker/) — outbox dispatch, local queue, fixture processor using `RevisionPublisher.publish` and `JobRepository.create_with_outbox` / `complete_with_revision`.
- **Migration:** [`supabase/migrations/20260925204703_job_control_plane.sql`](../supabase/migrations/20260925204703_job_control_plane.sql)
- **Docs:** [`docs/upload-and-jobs.md`](../docs/upload-and-jobs.md)
- **Scripts:** `./scripts/run-api`, `./scripts/run-worker-once`

## Contract changes

- API and worker version **0.1.0**.
- Dev auth: required `X-Owner-Id` header (`REQUIRE_OWNER_HEADER`, default true).
- Inline worker after upload unless `SKIP_INLINE_WORKER=1`.
- Pipeline version default `fixture@1.0.0`; fixture scene `annotation.json`.

## Verification

| Command or check | Result | Evidence/notes |
|---|---|---|
| `./scripts/test-api` | Pass | 21 integration tests: E2E upload, idempotency (bytes and options), cancel, duplicate delivery, lease recovery, crash/retry, error classes, JPEG/oversize, auth isolation, missing artifact, job progress/review_state. |
| `./scripts/check` | Pass | Full gate with persistence and pipeline (when `LOCAL_DATABASE_URL` is set). |

## Data used

- Synthetic 16×16 PNG generated in tests; fixture scene JSON only.

## Remaining work and risks

- **Production queue:** `ProductionJobQueue` not implemented; local deque only.
- **OCR/CV and UI:** Run 05+.
- **Auth:** Run 18 replaces header-based owner identity.

## Next-run starting point

- OpenAPI at `/docs` when API is running.
- Example curl in [`docs/upload-and-jobs.md`](../docs/upload-and-jobs.md).
