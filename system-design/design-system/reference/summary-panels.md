# Screenshot feature, chart and metrics

**Read when:** Matching the green financial panel, hatched mini-chart or four Today metric tiles.  
**Requires:** [Source, evidence and measurement conventions](evidence.md)  
**Related (optional; do not automatically load):** None.  
**Evidence:** Observed [O], measured [M], with explicitly marked interpretations/extensions.  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Financial feature anatomy

1. **Outer green wrapper:** `116,340,731,346`, mid-green, ≈36px radius.
2. **Header label:** white pill `134,362,157,36`, black circled-currency icon ≈16px; **Revenue at risk** at ≈14px, medium.
3. **Navigation utility:** white circular button `784,358,45,45`; black diagonal northeast arrow, no surrounding square or label.
4. **Inner well:** deep-green rectangle `125,415,713,263`, ≈28px radius; ≈9px side/bottom inset.
5. **Value:** `$184,500` in near-white, very large regular weight. Ink approximately spans x≈143–619 and y≈465–553. Keep the dollar sign same scale and baseline; comma included; no decimal places.
6. **Context sentence:** `across 8 cases that may miss their procedure date`, soft mint, one line at x≈143/y≈568; around 14px. Not bold.
7. **Mini column chart:** right of the value, described below.
8. **Bottom fact strip:** outlined rounded rectangle `143,599,677,61`; no fill different from inner well. Two fine vertical dividers divide three equal-ish cells; each cell has ≈14px horizontal padding.

## Feature facts

| Cell | Label | Value |
|---|---|---|
| Left, x≈156 | Recoverable this week | `$121,300` |
| Middle, x≈382 | Largest case | `$48,200 · Spinal fusion` |
| Right, x≈608 | Earliest procedure | `Sep 24` |

Labels are smaller/dimmer than values. Values are white, ≈14px, medium. The enclosing stroke and dividers are low-opacity light green, roughly 1px; use `rgb(200 232 212 / 0.25)` as an [E] reconstruction starting point. There are no icons in this strip.

## Mini chart

- Six bars labelled **Apr, May, Jun, Jul, Aug, Sep**; no title, y-axis, scale marks, legend, baseline stroke, gridlines, or tooltip visible.
- Bars occupy approximately x≈649–820 and share bottom **y≈557**.
- Each bar ≈23–24px wide; gap ≈6–7px; both top and bottom rounded into capsule ends.
- Approximate heights: **72, 52, 86, 62, 98, 124px**, respectively. These are visual heights, **not recovered financial values**.
- First five bars are muted medium green with clipped diagonal darker hatching. Stripes rise from lower left to upper right, spaced around 5–7px with a fine 1px-ish stroke.
- September is solid lime `--feature-highlight`, the tallest bar, with no hatching.
- Month labels below each bar are muted gray-green, ≈13px, centered; historic bars do not each have unique colors.
- **[E]** For real data, use honest proportional scaling, a text alternative, explicit units and a defined time period. Preserve the visual treatment; do not reuse these arbitrary heights as data. Hover/focus can reveal a compact white tooltip; only actual supplied data belongs in it.

## Today metric group

- White parent `864,340,810,346`, ≈36px radius.
- **Today** heading at x≈887/y≈371, ≈22px medium.
- Two top-right pale circular utility buttons: sliders/filter icon at ≈1559/358, then vertical ellipsis at ≈1612/358; each ≈44px.
- Four equally tall warm inset metric tiles start at y≈415 and end at y≈677. Approximate x/widths: `873/192`, `1073/192`, `1274/191`, `1473/193`; ≈9–10px gutters. Corners ≈28px.
- Each tile has label in upper left, a colored circular icon in upper right, a large value near bottom, and a trend/support row beneath.
- Tile horizontal content inset ≈18px; icon disk ≈36px diameter at y≈433. First label wraps into two lines, other labels remain one line. Preserve available text width to avoid label/icon collisions.
- Large blank middle areas are a deliberate part of the visual rhythm; do not vertically center labels and values together.

| Tile | Label | Icon / disk | Value and unit | Exact trend copy |
|---|---|---|---|---|
| 1 | Pending authorizations | Hourglass / yellow | `42` | red-orange northeast arrow + `6`, muted `vs last week` |
| 2 | Approval rate | Double check / green | `87.4` + small `%` | green northeast arrow + `2.1 pts`, muted `last 30 days` |
| 3 | At risk | Rounded warning triangle with exclamation / orange | `8` + small `cases` | green southeast arrow + `3`, muted `vs last week` |
| 4 | Avg. turnaround | Stopwatch with motion lines / lavender | `3.2` + small `days` | green southeast arrow + `0.4 d`, muted `to decision` |

The large digits share a baseline near y≈627; change lines are near y≈649. Units sit on the value baseline, not as superscripts. Arrow direction denotes numerical movement; color denotes favorability. An increase can be bad, a decrease can be good. **Do not infer business direction solely from a mathematical sign.** No sparkline is present in these four tiles.
