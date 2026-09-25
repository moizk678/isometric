# Run handoff — 05 Upload and review shell

**Run file:** `implementation-phases/05-web-foundation.md`  
**Status:** complete locally (hosted CI pending)  
**Next run:** `06-page-normalization.md`

## Delivered

### Wave 1: API, worker fit, web scaffold

- **API follow-ups:** [`services/api/isometric_api/`](../services/api/isometric_api/). Document list and detail include `original_filename` and `profile_id`. Jobs expose `updated_at` and `review_item_count`. `GET /api/v1/documents/{id}/display` returns an EXIF-transposed PNG. Every error body is `{code, message, request_id}`, including validation (`invalid_request`, 400), unhandled errors (`internal_error`, 500), unknown paths, and concurrent same-key uploads. OpenAPI is exported to [`services/api/openapi.json`](../services/api/openapi.json), and [`scripts/check`](../scripts/check) fails on drift.
- **Worker fixture fit:** [`services/worker/isometric_worker/fixture_fit.py`](../services/worker/isometric_worker/fixture_fit.py) scales the 200×200 fixture to the uploaded image, sets page display size and `sourceToDisplay` / `sourceToPage`, and inserts one fixture review item per machine object in the publish transaction.
- **Web scaffold:** [`apps/web/`](../apps/web/): Next.js 16, React 19, Tailwind 4 tokens, `AppShell` (232 px sidebar, 72 px rail, drawer below 1024 px), UI primitives, the same-origin proxy ([`src/app/api/v1/[...path]/route.ts`](../apps/web/src/app/api/v1/[...path]/route.ts), [`src/lib/api-proxy.ts`](../apps/web/src/lib/api-proxy.ts)), `apiFetch` / `ApiError`, generated [`src/api/schema.d.ts`](../apps/web/src/api/schema.d.ts), and [`scripts/run-web`](../scripts/run-web) / [`scripts/test-web`](../scripts/test-web).

### Wave 2: screens and workbench

- **List, upload, jobs:** [`src/app/documents/page.tsx`](../apps/web/src/app/documents/page.tsx), [`src/app/upload/`](../apps/web/src/app/upload/), [`src/app/jobs/[jobId]/page.tsx`](../apps/web/src/app/jobs/[jobId]/page.tsx). Pagination, full wrapped filename and profile, separate job and review badges. Upload keeps the `File` and `Idempotency-Key` after a failure, and Retry reuses the key. Job polling backs off and stops at a terminal state, flags the job as stale when `updated_at` is unchanged for 30 s, supports cancel, and maps `error_code` to text.
- **Workbench:** [`src/app/documents/[documentId]/page.tsx`](../apps/web/src/app/documents/[documentId]/page.tsx), [`src/components/workbench/`](../apps/web/src/components/workbench/), [`src/lib/geometry.ts`](../apps/web/src/lib/geometry.ts), the viewers, and [`ReviewPane`](../apps/web/src/components/review/ReviewPane.tsx). `revision` and `object` live in the URL. The original viewer shows `/display` with evidence mapped through `sourceToDisplay`. The SVG viewer shows the export as an `<img>` under a page-space hit overlay. Zoom and pan are shared. Download SVG is named after `original_filename`. Below 900 px there is an Original/SVG switch and a review drawer.

### Wave 3: E2E, CI, fixes, docs

- **Playwright** ([`apps/web/playwright.config.ts`](../apps/web/playwright.config.ts), [`apps/web/e2e/`](../apps/web/e2e/)): Chromium against the real API. [`e2e/serve-api`](../apps/web/e2e/serve-api) creates and migrates `isometric_e2e`, then starts the API on port 8000; Playwright starts the web app on port 3000. Run with [`scripts/test-web-e2e`](../scripts/test-web-e2e), which `./scripts/check` now calls last.
- **CI:** [`.github/workflows/check.yml`](../.github/workflows/check.yml) caches and installs Chromium, sets `E2E_DATABASE_URL`, runs `./scripts/check`, and uploads screenshots and the Playwright report as the `playwright-e2e` artifact.
- **UI fixes found by E2E:** [`UploadZone.tsx`](../apps/web/src/components/upload/UploadZone.tsx) gives the hidden file input an accessible name and removes it from the tab order, since the Choose files button already opens it. [`DocumentList.tsx`](../apps/web/src/components/documents/DocumentList.tsx) lets the header wrap so the title and pagination fit at 320 px.
- **Docs:** [`docs/web.md`](../docs/web.md) (run commands, env, proxy, coordinates, responsive rules, E2E) and [`docs/web-design-mapping.md`](../docs/web-design-mapping.md) (design alignment and **[E]** extensions: Lucide icons, viewer zoom/pan, the 900 px review drawer).
- **Screenshots:** [`apps/web/e2e/screenshots/`](../apps/web/e2e/screenshots/), named `{documents,upload,job,workbench}-{1440,390,320,zoom-200}.png` (16 files). Each `./scripts/check` run regenerates them.

## Contract changes

- The browser calls only same-origin `/api/v1/*`. The proxy injects `X-Owner-Id` from the server env `DEV_OWNER_ID` and forwards to `API_ORIGIN` (default `http://127.0.0.1:8000`).
- `GET /documents/{id}/display` is an **EXIF stand-in until Run 06**. It recomputes an EXIF-transposed PNG from the stored source on each request. Run 06 page normalization owns the real normalized display artifact.
- Fixture revisions: `page.widthPx` / `heightPx` equal the display size, and `sourceToPage` equals `sourceToDisplay`. Evidence polygons stay in source space and the UI maps them through `page.sourceToDisplay`.
- New error codes `invalid_request` (400) and `internal_error` (500). FastAPI's 422 is no longer in the spec.
- Web types are generated from the committed OpenAPI (`pnpm gen:api`). Scene types come from `packages/scene-schema`.

## Verification

All commands were run by the parent at Gate 3 on Sep 26, 2026 against the working tree that was committed.

| Command or check | Result | Evidence/notes |
|---|---|---|
| `LOCAL_DATABASE_URL=postgresql://isometric:isometric@localhost:5432/isometric ./scripts/check` | Pass (exit 0) | ruff check and format, migration replay, persistence 10 tests, scene-schema check, SVG goldens, OpenAPI drift check, API 43 tests, pipeline 174 + 6 tests, web `tsc` + Vitest 57 tests in 12 files, Playwright 26 tests in 17.9 s. |
| `./scripts/test-web` (the repo's `make test-web`; there is no Makefile) | Pass | 57 Vitest tests, run inside `./scripts/check`. |
| `./scripts/test-web-e2e` (Playwright, Chromium, `isometric_e2e`) | Pass | 26/26: `workflow.spec.ts` 2, `responsive.spec.ts` 16, `upload-retry.spec.ts` 2, `a11y.spec.ts` 6. |
| Exit check: upload a valid image, wait for the fixture job, inspect original and SVG, identify the selected object, download SVG | Pass | `workflow.spec.ts` "upload a PNG…": uploads through the real file input, waits for Succeeded, opens the workbench, checks that both `<img>`s load, selects objects, checks `data-selected-object` on both viewers and the SVG highlight, downloads the SVG, and checks the filename and `<svg` content. |
| Exit check: keyboard selects an object and opens its evidence, with visible focus | Pass | Same test: Tab reaches the Scene objects listbox, focus is `:focus-visible` with an outline of at least 2 px, then Home/ArrowDown/Enter selects the pipe. The URL `object`, the selected option, and the evidence stage and artifact IDs are asserted. |
| Exit check: touch selects an object and opens its evidence | Pass | `workflow.spec.ts` "touch selects…": 390 px mobile context with touch. Canvas tabs, Review, and Download are at least 44×44 px. Tapping an SVG hit target selects it, the Review drawer shows its evidence, and after switching to Original the selection and zoom are preserved. |
| Exit check: 1440, 390, 320 px and 200% zoom keep primary actions, with no page-level horizontal scroll | Pass | `responsive.spec.ts`: 4 layouts × 4 screens (documents, upload, job, workbench). 200% zoom is a 640×400 viewport at device scale 2. Asserts `scrollWidth <= clientWidth`, that headings fit their boxes, that primary actions are inside the viewport, and that Tab focus is visible. Writes the screenshots. |
| Exit check: upload failure keeps the file and offers a clear retry | Pass | `upload-retry.spec.ts`: a simulated 500 envelope and a network reset. The attachment row keeps the filename, an alert and request ID appear, and Retry sends the same `Idempotency-Key`, gets a 202, and reaches Succeeded. |
| Accessibility (axe, WCAG 2.2 AA tags) | Pass | `a11y.spec.ts`: documents, upload, and the workbench with a selected object at 1440 and 390 px. No violations. |
| Screenshots | Present | 16 PNGs in [`apps/web/e2e/screenshots/`](../apps/web/e2e/screenshots/), reviewed visually at 1440, 320, and 200% zoom. |
| Hosted CI (`Check`) | Pending | Recorded after push. |

## Data used

- Synthetic 800×600 PNGs generated per E2E test ([`e2e/support/png.ts`](../apps/web/e2e/support/png.ts)), synthetic images in API and worker tests, and the fixture scene. Web unit tests use MSW. **No real drawings were tested in this run.**

## Remaining work and risks

- **Display artifact:** `/display` is an EXIF stand-in recomputed per request. Run 06 owns normalization and caching.
- **Auth:** the owner is still a header set by the proxy. Run 18 replaces the `DEV_OWNER_ID` pattern.
- **E2E ports:** Playwright binds ports 8000 and 3000 and does not reuse running servers unless `PLAYWRIGHT_REUSE_SERVERS=1`, so stop local dev servers before `./scripts/check`.
- **Screenshot churn:** screenshots are committed as evidence and are rewritten by every `./scripts/check`, so they show up as modified afterwards.
- **Dev-generated files:** `next dev` writes `apps/web/AGENTS.md` and `apps/web/CLAUDE.md` (now gitignored) and may rewrite `apps/web/next-env.d.ts` to `.next/dev/types`. Restore the committed `next-env.d.ts` rather than committing that rewrite.

## Next-run starting point

- Read [`implementation-phases/06-page-normalization.md`](06-page-normalization.md), [`docs/web.md`](../docs/web.md), and [`docs/web-design-mapping.md`](../docs/web-design-mapping.md).
- Coordinate contracts: [`apps/web/src/lib/geometry.ts`](../apps/web/src/lib/geometry.ts), scene `page.sourceToDisplay`, and API `/display` (EXIF stand-in) vs `/source` (raw bytes).
- API client: [`apps/web/src/api/http.ts`](../apps/web/src/api/http.ts) and `documents.ts` / `jobs.ts` / `revisions.ts`. Regenerate types with `pnpm gen:api` after changing `services/api/openapi.json`.
- Commands that work (after setting `LOCAL_DATABASE_URL` and running `./scripts/migrate-replay`): `./scripts/run-api`, `./scripts/run-web`, `./scripts/test-web`, `./scripts/test-web-e2e`, `./scripts/check`.
