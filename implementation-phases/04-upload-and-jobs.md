# Run 04 — Upload, durable jobs, and processing API

**Agent brief:** Build the API/worker control plane and a deterministic fixture processor. Image interpretation arrives in later runs.

**Depends on:** [Runs 01–03](01-scene-contract.md). Read architecture sections 2 and 7.

## Build

1. Implement `POST /api/v1/documents` as multipart upload with profile/options, signature-based PNG/JPEG validation, bounded bytes/pixels, SHA-256, immutable original storage, document/job creation, and HTTP 202.
2. Implement `GET /api/v1/documents` with pagination, `GET /api/v1/jobs/{id}`, `POST /api/v1/jobs/{id}/cancel`, `GET /api/v1/documents/{id}`, authorized source-image retrieval, revision-history/scene/review-item reads, and revision export download. Return stable JSON error codes and request IDs. Restrict all reads to the authorized document owner or test identity until auth is finalized in Run 18. Keep job state (`queued/running/succeeded/failed/canceled`) separate from revision review state.
3. Add durable queue and worker adapters with local development implementation and production interface. An outbox dispatcher publishes queued jobs after the database commit. Worker writes stage runs and state transitions, honors leases/retries/cancellation, and uses a fixture scene to exercise render/validate/publish without CV.
4. Make creation idempotent for repeated upload requests with a unique `(owner, idempotency key)` mapping. Reuse with different bytes/options returns conflict. Record `(job ID, attempt number, input/options hashes, profile/pipeline versions)` for processing; at-least-once queue delivery must not duplicate a scene revision.
5. Expose stage progress without inventing percentages when work cannot be measured. Separate invalid input, transient worker error, and permanent processing failure.

## Deliverables

- API routes, worker lifecycle, queue adapter, fixture processing path, OpenAPI contract, and integration tests.

## Exit checks

- Valid image upload returns a job, and polling reaches a fixture-backed review/ready revision with SVG and preview.
- Invalid file, oversized decode, duplicate request, changed-payload key reuse, worker crash/retry, queue duplicate, cancellation, and missing artifact produce stable outcomes without duplicate revisions.
- A succeeded job may point to a `review_required` revision; canceling before publication cannot change the current revision.
- Document list, private source retrieval, and revision history expose only the caller's documents.
- Unauthorized document read is denied in the chosen development auth mode.
- `make test-api` and a local end-to-end upload demonstration pass.

## Out of scope and handoff

Do not add OCR/CV or a polished frontend. Hand off API examples, state/error enums, local run commands, and queue retry behavior to [Run 05](05-web-foundation.md).
