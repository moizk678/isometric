# Web app (Run 05)

Next.js product UI for upload, job progress, and fixture-backed review. The browser talks only to same-origin `/api/v1/*`; it never sends `X-Owner-Id` and never connects to PostgreSQL.

## Run locally

### Prerequisites

Same persistence setup as the API ([upload-and-jobs.md](./upload-and-jobs.md)):

```sh
export LOCAL_DATABASE_URL=postgresql://isometric:isometric@localhost:5432/isometric
export ARTIFACT_ROOT=.private/artifacts
./scripts/migrate-replay
```

Copy `.env.example` to `.env` (or export the web variables below). Next.js loads `.env` from the repo root when present.

### API

```sh
./scripts/run-api
```

Uvicorn binds `0.0.0.0` on port **8000** (override with `PORT`). After each upload the API runs an inline worker in development unless `SKIP_INLINE_WORKER=1`; use `./scripts/run-worker-once` when processing is deferred.

### Web

```sh
./scripts/run-web
```

This runs `pnpm --filter @isometric/web dev` (Next.js 16 with Turbopack). Default URL: **http://localhost:3000**.

Open **Documents**, **Upload**, follow a job to `/jobs/[jobId]`, then open the workbench at `/documents/[documentId]` (optional query: `?revision=` and `?object=`).

### Tests

```sh
./scripts/test-web    # or: pnpm test:web
pnpm gen:api          # regenerate apps/web/src/api/schema.d.ts from services/api/openapi.json
```

End-to-end (Playwright, Chromium):

```sh
./scripts/test-web-e2e
```

Playwright starts its own API on port 8000 against `E2E_DATABASE_URL` (default `isometric_e2e`, created and migrated on first run) and the web app on port 3000, so stop any dev servers on those ports first. Set `PLAYWRIGHT_REUSE_SERVERS=1` to reuse running servers instead. Screenshots at 1440, 390, and 320 px and 200% zoom are written to `apps/web/e2e/screenshots/`.

Full repo gate: `./scripts/check` (ends with `./scripts/test-web` and `./scripts/test-web-e2e`).

## Environment variables (web)

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `API_ORIGIN` | Server only (Next route handler) | `http://127.0.0.1:8000` | Upstream FastAPI base URL for the proxy |
| `DEV_OWNER_ID` | Server only | `dev-owner` | Value injected as `X-Owner-Id` on every proxied request |

The API still requires `X-Owner-Id` for direct curl access; the web app adds it in [`apps/web/src/lib/api-proxy.ts`](../apps/web/src/lib/api-proxy.ts) inside [`apps/web/src/app/api/v1/[...path]/route.ts`](../apps/web/src/app/api/v1/[...path]/route.ts). Client code uses [`apiFetch`](../apps/web/src/api/http.ts), which calls relative paths under `/api/v1`.

Other variables (`LOCAL_DATABASE_URL`, `ARTIFACT_ROOT`, etc.) are for the API and worker only; they are not read by the Next.js client bundle.

**Owner consistency:** uploads and list/detail are scoped to the owner id the proxy sends. Use the same `DEV_OWNER_ID` for the lifetime of a dev database, or you will not see documents created under a different owner header.

## Same-origin API proxy

```
Browser  --fetch /api/v1/...-->  Next.js route handler
                                      |
                                      |  fetch(API_ORIGIN/api/v1/...)
                                      |  + X-Owner-Id: DEV_OWNER_ID
                                      v
                                 FastAPI + Postgres (server-side)
```

Why:

- **Security:** owner identity and database credentials stay on the server.
- **CORS:** the UI and API share one origin in the browser (`localhost:3000`), while the API process remains on `8000`.
- **Cookies / auth later:** a single origin simplifies future session cookies without exposing the API host to the client.

The proxy forwards method, query string, body, and most headers; it strips `host` / `connection`, sets `X-Owner-Id`, and streams the upstream response back unchanged (including binary image/SVG bodies).

## Routes

| Path | Role |
|---|---|
| `/documents` | Paginated document list with job and review badges |
| `/upload` | File input + drag-and-drop; `Idempotency-Key` retained on retry |
| `/jobs/[jobId]` | Job polling, stale detection, cancel, link to workbench |
| `/documents/[documentId]` | Review workbench; `revision` and `object` in the URL |

## API surface used by the UI

All paths are requested as `/api/v1/...` from the browser (proxied to FastAPI).

| Method | Path | Use |
|---|---|---|
| `GET` | `/documents` | List (`limit`, `offset`) |
| `POST` | `/documents` | Multipart upload (`file`, `profile_id`, `Idempotency-Key`) |
| `GET` | `/documents/{id}` | Workbench header, revision selection |
| `GET` | `/documents/{id}/display` | Orientation-normalized source **PNG** for the original viewer |
| `GET` | `/documents/{id}/revisions/{revision_id}/scene` | Drawing scene JSON |
| `GET` | `/documents/{id}/revisions/{revision_id}/review-items` | Review pane |
| `GET` | `/documents/{id}/revisions/{revision_id}/exports/svg` | SVG export (`<img>` only) |
| `GET` | `/jobs/{job_id}` | Progress (`updated_at`, `review_item_count`, terminal states) |
| `POST` | `/jobs/{job_id}/cancel` | Cancel in-flight job |

`GET /documents/{id}/source` returns raw stored bytes; the workbench uses **`/display`** instead.

### Display image

`GET /documents/{id}/display` returns the worker-produced **display** PNG at `documents/{id}/display.png` when normalization has run (same bytes as EXIF-oriented display for typical uploads). If that artifact is missing (legacy jobs or partial failures), the API falls back to transposing the stored source with `ImageOps.exif_transpose` and encoding PNG on the fly.

The response matches **display** pixel dimensions in the scene (`page.displayWidthPx` / `displayHeightPx`) and the `page.sourceToDisplay` matrix used by the original viewer.

## Coordinate mapping and viewers

Scene types live in [`packages/scene-schema/src/drawing-scene.ts`](../packages/scene-schema/src/drawing-scene.ts). Geometry helpers are in [`apps/web/src/lib/geometry.ts`](../apps/web/src/lib/geometry.ts).

### Frames

- **Source (stored file):** evidence polygons in scene JSON are in **source** pixels (before EXIF).
- **Display:** pixels after EXIF orientation; the original viewer image matches this size.
- **Page:** SVG export coordinate system; `page.widthPx` / `heightPx` match display size; `page.sourceToPage` equals `sourceToDisplay` for fixture revisions.

### Original viewer (`SourceViewer`)

- Loads `/display` in an `<img>` sized to `displayWidthPx` × `displayHeightPx`.
- Maps each evidence `sourcePolygon` with `sourcePolygonToDisplay(page, polygon)` → apply `page.sourceToDisplay`.
- Overlays are drawn in **display** space, aligned with the image via shared `containFit` / `viewerStage` math from `useViewport`.

### SVG viewer (`SvgViewer`)

- Loads the export with `<img src=".../exports/svg">` — **never** inline SVG markup (XSS and styling isolation).
- Hit targets and highlights use **page** geometry from scene objects (`objectHitGeometry`), on an SVG overlay with `viewBox="0 0 {widthPx} {heightPx}"`.
- Pipe colors in the export remain source/scene data, not UI status tokens.

### Fit, zoom, and pan

Both viewers share one `useViewport` instance on the workbench so zoom and selection stay aligned. Default framing is **object-fit: contain** (`containFit`), then zoom and pan adjust `viewerStage`. Pointer drag, wheel, and keyboard (`+`, `-`, `0`, arrows) are implemented in the viewer stack; see [web-design-mapping.md](./web-design-mapping.md) for design-system notes.

## Responsive layout

### App shell (sidebar)

- Expanded sidebar **232px**, collapsed rail **72px** (`--sidebar-expanded` / `--sidebar-rail` in `globals.css`).
- Below **1024px** width: primary nav moves into an end **Drawer**; a menu control opens it (`AppShell` + `useMediaQuery('(min-width: 1024px)')`).

### Workbench

- **≥ 900px:** two viewer panels (original + SVG) beside a fixed **Review** column (~320–380px). At ~720px container width within the grid, the two viewers stack in two columns.
- **&lt; 900px** (`NARROW_WORKBENCH_PX`): one canvas at a time via **Original / SVG** segmented control; **Review** opens in a drawer. Zoom and selected `object` query param persist across canvas switches.
- Interactive controls target at least **44px** touch height where the workbench narrows (e.g. segmented control buttons).

## Types and clients

- OpenAPI-derived types: `apps/web/src/api/schema.d.ts` (`pnpm gen:api`).
- Thin clients: `src/api/documents.ts`, `jobs.ts`, `revisions.ts`.
- Errors: `ApiError` with `code`, `message`, `requestId` from the API envelope.

## Related docs

- [upload-and-jobs.md](./upload-and-jobs.md) — API and worker
- [web-design-mapping.md](./web-design-mapping.md) — design system alignment and `[E]` extensions
