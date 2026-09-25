# Screenshot layout and header

**Read when:** Matching the original frame, grids, alignment, logo, navigation, greeting or top controls.  
**Requires:** [Source, evidence and measurement conventions](evidence.md)  
**Related (optional; do not automatically load):** None.  
**Evidence:** Observed [O], measured [M], with explicitly marked interpretations/extensions.  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Overall scene

| Region | Approximate RU bounds `(x, y, width, height)` | Geometry / relationship |
|---|---|---|
| Entire image | `0, 0, 1790, 1376` | Warm taupe presentation canvas |
| Workspace frame | `98, 120, 1594, 1134` | Radius ≈36; centered; ≈98 left/right and ≈120 top/bottom |
| Main content area | `116, 138, 1558, 1099` | ≈18 inset from workspace; right edge ≈1674 |
| Navigation band | `116, 138, 1558, 53` | All pills/circles vertically centered |
| Introductory text | `129, 222, 600, 98` | Left inset 13 greater than card edge |
| Page-level controls | `1218, 273, 452, 49` | Right aligned; sits beside bottom of introductory text |
| Top content row | `116, 340, 1558, 346` | Feature panel + metric group; ≈18 gap |
| Financial feature | `116, 340, 731, 346` | Green outer card; radius ≈36 |
| Metric group | `864, 340, 810, 346` | White; radius ≈36 |
| Bottom row | `116, 703, 1558, 534` | ≈17 vertical gap from top row |
| Work table panel | `116, 703, 1142, 534` | White; radius ≈36 |
| Activity panel | `1275, 703, 399, 534` | White; radius ≈36; ≈17 horizontal gap |

The top row allocates approximately **47.4% / 52.6% of space after its gutter**. The bottom row allocates approximately **74.1% / 25.9% after its gutter**. These are two different grids. Do not force a single equal-column dashboard grid.

## Alignment map

- The workspace's top-left logo, green feature card, and table panel share **x≈116**.
- Introductory text begins at **x≈129**; table title at **x≈138**; table rows at **x≈125**. These are intentional levels of inset, not one universal text edge.
- Top row cards share top and bottom edges. Bottom row panels share top and bottom edges.
- Metric tiles and dark-green inner panel both begin at **y≈415**, making the top row feel coordinated.
- Hero support strip and metric change lines sit near the bottom of their parent panels.
- Table rows share icon, text, issue, payer, probability, due-date, and button columns.
- Activity timestamps form their own right-aligned column; the text column yields before the timestamps do.

## Layout implementation targets [E]

Use CSS grid/flex with intrinsic sizing and `min-width: 0`. The RU bounds are for visual verification, not instructions to absolutely position the whole application. Keep a root max-width near **1594px** for the framed desktop presentation. Use the observed **18px** gutters in strict reference mode; normalize new layouts to **16 or 24px** in product mode. Keep consistent vertical rhythm within each mode.

Suggested reference grid: top `minmax(0, 0.474fr) minmax(0, 0.526fr)` with 18px gap; bottom `minmax(0, 1fr) 399px` with 18px gap. The bottom grid should switch layout before the table becomes unreadable.

## Brand mark

- Black circle at approximately `116,138,54,54`.
- White thick open ring/C-like mark inside, with a small lime disk on its right side. The white mark occupies roughly 29–31px; lime dot roughly 9px.
- No wordmark, app title, or separator line accompanies it.
- **[U]** Exact trademark identity/vector construction unknown. For another app, replace it with that app's real logo at the same visual footprint. Do not use the screenshot logo as an invented product identity.

## Primary navigation

- White pill approximately `183,138,717,54`; black logo separated by ≈13px.
- Active **Dashboard** appears as a black nested pill approximately `187,143,118,44`, with white centered text and ≈4–5px inset from its white rail.
- Remaining labels: **Pipeline**, **Cases**, **Payers**, **Documents**, **Denials**, **Analytics**.
- Non-active labels are dark neutral; no icons, bottom underline, badges, separators, or shadows.
- Text vertically centered; horizontal padding varies with label width; approximately 20px per side at this scale.
- **[E]** Implement as navigation links and mark the current route. This visible rail is not automatically an ARIA tablist: route navigation and in-page tabs have different semantics.

## Search and utilities

| Element | Approximate geometry | Observed details |
|---|---|---|
| Search | `1085,138,311,53` | White pill; gray search outline at x≈1105; placeholder `Search cases, patients, payers`; no visible shortcut hint |
| Notifications | `1405,138,54,54` | White circle; black outline bell; no unread badge |
| Settings | `1467,138,54,54` | White circle; black outline gear |
| Profile | `1530,138,144,54` | White pill; 44px circular portrait at ≈1534,143; `Sarah`; small gray down chevron |

The portrait shows a person with dark curly hair and a gray jacket against a warm orange background; crop fills the circle. It is not an illustration or initials avatar. **[U]** No original photograph provided. Use an authorized replacement or initials for a new product. Do not stretch the raster into a large asset.

Search, bell, settings, and profile have ≈9–10px gaps. There is substantial flexible blank space between navigation and search. Do not distribute all header items evenly across the full width.

## Page introduction

Three stacked text levels begin at x≈129:

1. Muted overline **Revenue Cycle Overview**, y≈222, ≈15px.
2. Large black greeting **Good morning, Sarah**, y≈248, ≈44px. One line.
3. Secondary text **42 active authorization cases · Monday, Sep 21**, y≈305, ≈16px. The separating dot is small and gray; it is not a line break.

Large quiet whitespace separates the navigation band from content. The greeting is personalized orientation, not a centered marketing hero.

## Date scope and creation action

- Segmented scope pill at roughly `1218,276,235,44`, white, fully rounded.
- **Today** is selected: black pill ≈74×36, 4px inset; **Week**, **Month** are unfilled.
- A separate black **New Authorization** pill at `1460,273,210,49`, with a thin plus icon followed by text. Approximately 8px gap to scope selector; slight height difference is visible.
- Plus icon is white/light, ≈18px, thin stroke; action label ≈16px.
- **[I]** Scope choices likely change the overview's period; new authorization likely opens a creation flow. The screenshot does not prove the mechanism, date boundaries, or what panels update.
- **[E]** For a new product, declare scope explicitly and use a concrete object-specific CTA such as “New project.” Preserve a single primary action in this header position.
