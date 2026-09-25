# Upload and jobs API (Run 04)

FastAPI control plane for multipart upload, durable jobs, and fixture-backed processing. Image interpretation is not implemented yet.

## Run locally

```sh
export SUPABASE_DATABASE_URL='postgresql://...'
export ARTIFACT_ROOT=.private/artifacts
./scripts/migrate-replay
./scripts/run-api
```

The API runs an inline worker pass after each upload in development. For manual worker control:

```sh
export SKIP_INLINE_WORKER=1   # optional: defer processing
./scripts/run-worker-once
```

`./scripts/test-api` sets `SKIP_INLINE_WORKER=1` and `ISOMETRIC_WORKER_FIXTURE_ONLY=1` so integration tests validate upload/jobs/revisions without running the full CV pipeline against cloud Postgres. One follow-up test still runs the full worker for mask artifacts.

## Authentication (development)

Send `X-Owner-Id` on every request. Documents and jobs are scoped to that owner until Run 18 adds real auth.

## Upload

```sh
curl -sS -X POST http://localhost:8000/api/v1/documents \
  -H 'X-Owner-Id: demo-user' \
  -H 'Idempotency-Key: demo-upload-1' \
  -F 'file=@page.png' \
  -F 'profile_id=piping_isometric' \
  -F 'options_json={}'
```

Returns HTTP 202 with `document_id`, `job_id`, and `status`. Poll `GET /api/v1/jobs/{job_id}` until `state` is `succeeded` (fixture scene with `review_required` revision).

`GET /api/v1/jobs/{job_id}` also returns `progress` (`stage`, `attempt` only — no percentage), `warnings` from the latest stage run, and `review_state` for the result revision when present. Document list and document detail include `review_state` for the current revision.

## Job states

| State | Meaning |
|---|---|
| `queued` | Accepted, waiting for worker |
| `running` | Worker lease held |
| `succeeded` | `result_revision_id` set (unique per job) |
| `failed` | `error_code` set |
| `canceled` | Cancel requested before publication |

Job state is separate from revision `review_state` (`review_required`, `ready`, etc.).

## Errors

JSON body: `{ "code", "message", "request_id" }`.

| Code | Typical HTTP |
|---|---|
| `unauthorized` | 401 |
| `forbidden` | 403 |
| `unsupported_media_type` | 415 |
| `invalid_image` | 400 |
| `payload_too_large` | 413 |
| `image_too_large` | 413 |
| `idempotency_conflict` | 409 |
| `not_found` | 404 |
| `missing_artifact` | 404 |

Worker terminal `error_code` values on failed jobs: `processing_invalid`, `processing_failed`, `missing_artifact`, `worker_exhausted`.

## Queue and retries

`JobRepository.create_with_outbox` commits the job with an outbox row. `dispatch_outbox` publishes to `LocalJobQueue` (production `QUEUE_URL` adapter deferred to Run 19).

Workers claim jobs with a time-bounded lease. If a worker crashes, `recover_expired_leases` returns non-canceled jobs to `queued` (and the next worker pass re-enqueues them) or marks canceled jobs with an expired lease as `canceled`. Transient failures (`OSError`, database operational errors) requeue until `attempt` reaches 3, then the job fails with `worker_exhausted`. Each job publishes at most one revision using a deterministic revision id derived from the job id (`uuid5`), so at-least-once delivery does not create duplicate revisions.
