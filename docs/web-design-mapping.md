# Web UI — design system mapping (Run 05)

This note records how the Run 05 web app maps to [`system-design/design-system/`](../system-design/design-system/) and where the implementation extends contracts that the design system does not fully specify. Extensions are marked **[E]**.

## Foundations

| Design source | Implementation |
|---|---|
| [`foundations/tokens.md`](../system-design/design-system/foundations/tokens.md) | Tailwind 4 `@theme` in `apps/web/src/app/globals.css` (warm neutrals, spacing, radii, motion) |
| Typography | Inter via `next/font` |
| Responsive / shell | Sidebar widths 232px / 72px; nav drawer below 1024px — see [`docs/web.md`](./web.md) |

## Components (aligned)

| Design doc | Web component / usage |
|---|---|
| Shell / navigation patterns | `AppShell`, primary links Documents + Upload |
| Buttons, panels, badges | `Button`, `IconButton`, `Panel`, `StatusBadge` (`JobStateBadge`, `ReviewStateBadge`) |
| Drawer | `Drawer` (focus trap, Escape, focus restore) — shell nav and workbench review |
| Uploads | `UploadZone` per [`components/uploads-files.md`](../system-design/design-system/components/uploads-files.md) |
| Feedback / empty / error | `EmptyState`, `ErrorState` (shows API `request_id` when present) |
| Progress | `ProgressBar` (indeterminate job loading) |
| Segmented control | `SegmentedControl` (narrow workbench canvas switch) |

## **[E] Extensions** (not specified by the design system)

These are deliberate product/engineering choices. They are **not** claims that the linked design files required them.

### **[E] Lucide outline icons**

The design system does not prescribe a concrete icon set for the web shell and controls. The app uses **`lucide-react`** outline icons (20px, stroke 1.5) in navigation, status badges, upload, workbench actions, and viewport controls instead of an unspecified glyph package.

### **[E] Viewer zoom and pan**

[`components/media.md`](../system-design/design-system/components/media.md) does not define zoom, pan, wheel behavior, or keyboard shortcuts for drawing viewers. Run 05 adds:

- Shared `useViewport` (contain fit baseline, zoom clamp, pan, fit reset)
- `ViewportControls` and pointer/wheel/keyboard handlers on `ViewerFrame`
- Synchronized viewport between Original and SVG panes on wide layouts

Document this as an **[E]** extension until media.md or a viewer spec absorbs it.

### **[E] Workbench review drawer below 900px**

Product responsive guidance describes narrow review patterns generically; it does not specify a **900px** breakpoint, an Original/SVG single-canvas switch, or moving the review pane into a drawer. The workbench implements:

- `NARROW_WORKBENCH_PX = 900` in `Workbench.tsx`
- Segmented **Original / SVG** + **Review (n)** drawer
- Preserved `object` URL selection and shared zoom across canvas changes

Treat the **1024px** shell drawer as shell-level responsive behavior; the **900px** workbench layout is a separate **[E]** extension.

## Media / viewers (contract alignment)

| Topic | Design intent | Run 05 behavior |
|---|---|---|
| Show source vs export | Separate surfaces for original and SVG | Side-by-side on wide; one at a time on narrow **[E]** switch |
| SVG safety | Do not treat export as editable DOM | `<img>` for `/exports/svg`; overlays from scene JSON only |
| Evidence on original | Map source evidence to displayed orientation | `sourcePolygon` → `sourceToDisplay` before draw |
| Status vs pipe color | UI tokens ≠ drawing semantics | Highlights use UI tokens; pipes keep scene colors in the rasterized SVG |

## Gaps for later runs

- Keyboard, touch, and responsive evidence lives in `apps/web/e2e/` and `apps/web/e2e/screenshots/`, not in this note.
- Normalized display artifact vs on-the-fly EXIF transpose: Run 06 (`06-page-normalization.md`).
- Semantic editing, auth UI, and production deployment: out of Run 05 scope.
