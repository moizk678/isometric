# Run 05 — Upload and review shell

**Agent brief:** Build the product UI around fixture-backed results so users can navigate the workflow before CV is available.

**Depends on:** [Runs 02 and 04](04-upload-and-jobs.md). Read [system-design/design.md](../system-design/design.md) in product mode, then its routed upload, panels, media, feedback, tokens, responsive, and accessibility files.

## Build

1. Create Next.js routes for document list, upload, job progress, and a document review workbench. Use the API from Run 04; do not read Supabase PostgreSQL from the browser.
2. Build a warm-neutral application shell, upload zone with a real file input, validation and retry states, document cards/rows, and status with text/icons. Show processing job state separately from a revision's review state. Keep the full filename and profile visible.
3. Show the orientation-normalized source display image and fixture SVG in synchronized viewers with fit, zoom, pan, object highlighting, and a basic review-item pane. Map raw source evidence through `source_to_display` before drawing source overlays. Use `object-fit: contain` semantics for full drawings and keep pipe colors as source data, not UI status tokens.
4. On narrow widths, show one canvas at a time with an obvious switch and a review drawer or separate pane; preserve selection and zoom context. Provide keyboard paths for evidence selection and 44 px touch targets.
5. Cover loading, empty, failure, long labels, and stale job states. Use actual API contracts and a fake server only in tests.

## Deliverables

- Working upload/list/status/review pages and reusable viewer components.
- Screen-level test fixtures and a short design-system mapping note if the implementation deviates from a component contract.

## Exit checks

- A local user can upload a valid image, wait for the fixture job, inspect original/SVG, identify the selected object, and download SVG.
- Keyboard and touch can select an object and open its evidence; focus remains visible.
- Screens work at wide desktop, 390 px, 320 px, and 200% zoom without losing primary actions or causing page-level horizontal scrolling.
- Upload failure retains the selected file and offers a clear retry; `make test-web` passes.

## Out of scope and handoff

Do not implement semantic editing or change the design system source files. Hand off viewer coordinate mapping, API client, responsive decisions, and screenshot evidence to [Run 06](06-page-normalization.md).
