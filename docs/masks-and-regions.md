# Masks and regions (Run 07)

Stages `separate_masks` and `detect_regions` operate in **page pixel space** (rectified page from Run 06). All mask PNGs are single-channel (`0` background, `255` foreground) with the same width and height as `documents/{id}/page.png`.

## Stages

| Stage | Producer | Stage-run artifact | Document artifacts |
|---|---|---|---|
| `separate_masks` | `separate_masks@1.0.0` | job `.../stages/separate_masks/{hash}/overlay.png` | `masks/grid.png`, `retained-ink.png`, `black-ink.png`, `unclassified-ink.png`, color layer PNGs |
| `detect_regions` | `detect_regions@1.0.0` | `documents/{id}/regions.json` | `masks.json` (final metadata), `masks/protection.png`, `masks/geometry-ink.png`, `crops/*.png` |

`masks.json` is written once when `detect_regions` finishes (it includes mask URIs and warnings from both stages). The immutable artifact store does not allow overwriting mask PNGs mid-job, so `protection` and `geometry-ink` are persisted only in `detect_regions`.

## Mask semantics

| Mask file | Meaning |
|---|---|
| `masks/grid.png` | Pixels classified as background grid lines |
| `masks/retained-ink.png` | Ink kept for downstream processing (after optional grid removal) |
| `masks/black-ink.png` | Low-chroma ink (annotations, text-like strokes) |
| `masks/unclassified-ink.png` | Retained ink not assigned to a color layer or protection |
| `masks/protection.png` | Text/symbol/dimension/arrow regions excluded from centerline fitting |
| `masks/geometry-ink.png` | `retained_ink & ~protection` — input for Run 08 centerlines |
| `masks/color/{layer_id}.png` | Colored route layer candidate |

Boolean relationships (after `detect_regions`):

- `geometry_ink ⊆ retained_ink`
- `protection ∩ geometry_ink ∅` (morphological tolerance allowed in tests)
- Color layers ⊆ retained_ink; black ink and protection are disjoint from color layers

## Warning codes

- `grid_separation_low_confidence` — grid removal skipped or grid mask cleared; ink preserved.

## Regions

`regions.json` lists `RegionCandidate` entries with `id`, `kind` (`text`, `symbol`, `arrow`, `dimension`), page-space `bbox`, `score`, `crop_uri`, and `evidence`. Crops live at `documents/{id}/crops/{id}.png`.

Run 08 should read `geometry-ink.png`, color layer masks, `protection.png`, and region boxes from these artifacts.
