# Page normalization (Run 06)

The `normalize_page` stage decodes immutable source bytes, applies EXIF orientation for analysis, optionally rectifies a page quadrilateral with OpenCV, and writes document-scoped artifacts plus a `stage_runs` record.

## Artifacts

| Key | Content |
|---|---|
| `documents/{id}/display.png` | Orientation-normalized RGB PNG (original viewer) |
| `documents/{id}/page.png` | Rectified or fallback page PNG (page pixel space) |
| `documents/{id}/normalize.json` | Transforms (including `displayToPage` / `pageToDisplay`), hashes, diagnostics, warning codes |
| `jobs/{job_id}/stages/normalize_page/{hash}/corner-overlay.png` | Corner overlay diagnostic |

## Warning codes

- `page_boundary_low_confidence` — rectification skipped; page equals display with identity `display→page` homography.

## Limits

Defaults match the API upload limits: 20 MiB, 40 M decoded pixels.

## Producer version

`normalize_page@1.0.0` (see `packages/pipeline/isometric_pipeline/normalize/artifact.py`).
