# Drawing reading table (2026-09-27)

Standalone vision lane beside the geometry pipeline. Reading never writes scene objects, OCR candidates, review items, or SVG.

## Jobs

Upload and reprocess create two jobs in one transaction: a `pipeline` job (existing behavior), then a `drawing_reading` job. HTTP responses return only the pipeline job id.

Column `drawing.jobs.kind` is `text NOT NULL DEFAULT 'pipeline'`. Reading jobs use `kind = 'drawing_reading'` and leave `result_revision_id` null.

`process_job` branches on `kind` immediately after claim, before `revision_id_for_job` and scene stages.

## Page wait

Reading jobs read `documents/{documentId}/page.png`. If missing:

- While any `pipeline` job for the document is `queued` or `running`, release the claim and requeue without counting a failure attempt (undo the claim attempt increment).
- If every pipeline job is terminal and the page is still missing, or the reading job is older than ten minutes and the page is still missing, fail with `missing_page`.

Pipeline outbox rows are inserted before reading outbox rows so a single-pass worker tends to produce `page.png` before the reading job runs.

## Provider chain

Module: `services/worker/isometric_worker/drawing_reading/`.

- `VISION_ENABLED` unset or off: succeed with artifact status `disabled`. No outbound HTTP.
- Enabled: Cloudflare Workers AI (`POST /accounts/{account_id}/ai/run/{model}`) using `CLOUDFLARE_ACCOUNT_ID`, `VISION_API_KEY`, `VISION_MODEL`.
- One retry on timeout, HTTP 429, or HTTP 5xx for Workers AI.
- Any other Workers AI failure, including JSON that fails table schema validation, calls Gemini once (`GEMINI_API_KEY`, `GEMINI_MODEL`, `generateContent` with inline image).
- Both fail: reading job `failed`. Scene revision unchanged.
- Per-attempt timeout budget ~30s inside the 120s lease.
- Logs: provider, model, latency, status, job id. Never log image bytes, raw provider bodies, or API keys.
- Tests use `ISOMETRIC_FAKE_DRAWING_READING` instead of live providers.

Artifact: `documents/{documentId}/readings/{jobId}.json` with `prompt_version` `drawing-reading@1`, provider, model, and schema version metadata.

## Table schema

Four groups in order, each with `id`, `title`, and `rows`:

| id | title |
| --- | --- |
| dimensions | Dimensions |
| connections | Connections |
| components | Components |
| handwriting | Other handwriting |

Each row: `location` and `reading`, non-empty strings. Location is a spatial phrase. Reading is transcribed text including units and inch marks.

Classification: measured length or offset → dimensions; join, nozzle, or branch note → connections; valve, fitting, or equipment label → components; other handwriting → handwriting.

Empty row lists are valid. Repeated rows are kept. Reject extra fields, coordinates, missing groups, and non-string cells. Do not persist rejected provider payloads.

## API

`GET /api/v1/documents/{id}/drawing-reading` (owner check) returns the newest reading job for the document:

| status | meaning |
| --- | --- |
| absent | no reading job |
| pending | newest reading job queued or running |
| ready | succeeded artifact validates with groups |
| disabled | succeeded with vision disabled |
| unavailable | newest reading job failed; includes `error_code` |

## Configuration

`.env.example` and API settings: `VISION_ENABLED`, `CLOUDFLARE_ACCOUNT_ID`, `VISION_API_KEY`, `VISION_MODEL`, `GEMINI_API_KEY`, `GEMINI_MODEL`. CI keeps `VISION_ENABLED` off.

## Tests (backend)

Fake provider only. Cover valid table, Workers AI invalid → Gemini, both fail (scene unchanged), vision disabled, missing page, upload/reprocess enqueue reading job, idempotent upload does not duplicate pairs, and existing single-job processor tests still pass.
