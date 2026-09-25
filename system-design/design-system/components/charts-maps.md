# Charts, analytics and maps

**Read when:** Bar/line/area/donut/sparkline/heatmap/scatter/bubble/histogram charts, maps or data tooltips.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** [Screenshot feature, chart and metrics](../reference/summary-panels.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Charts, visual analytics, and maps [E]

- Charts live in the same white cards and warm-neutral insets as other content. Default chart card padding **24 px**, title 18 px, supporting caption 12 px, plot gap 24 px. Avoid enclosing each axis/legend in its own rounded panel.
- Axis labels and legends: **11–12 px / 16 px**, secondary or muted ink after contrast checks; axes/grid: **1 px** low-contrast neutral; no decorative box border around the plot. Use at most **3–5 horizontal guides** in small charts. Keep real data ranges and units visible when comparison requires them.
- A single-series chart defaults to black or the system's thematic green. A highlighted current period may use the established lime accent if that token is defined in the measured palette. Do not introduce neon blue, magenta, or rainbow palettes merely because a charting library provides them.
- Multiple series use a deliberate, color-accessible palette derived from approved accent tokens, plus direct labels, dashes, or patterns. Semantic state colors must not be reassigned to arbitrary series when those same colors already carry success/warning/failure meanings on the page.
- **Bar chart:** 8–12 px top radius for medium bars, pill-ended bars for narrow miniature marks, 8–16 px gaps according to width. Historical/reference bars may use reduced-opacity fill or a restrained hatch; the active period is solid. Axis information should not disappear merely to imitate the decorative mini chart.
- **Line chart:** 2 px stroke, 4–6 px hover/focus points, optional area fill at **6–10% opacity**, no heavy gradient. Use straight or monotone interpolation suited to the data; smoothing must not imply unobserved extrema. Distinguish missing data from zero.
- **Stacked bar/area:** show a consistent series order, a concise legend, and total labels only when they improve comparison. Do not rely on color alone to identify segments.
- **Donut:** 20–28 px ring thickness for a 160–220 px chart; central total 28–36 px, 12 px label; maximum **5 slices** before grouping minor values with an explained `Other`. Include a textual category/value list, because angle alone is weak for precise comparison.
- **Sparkline:** approximately 96–144 px wide × 32–48 px high; 1.5–2 px stroke, no axes, no arbitrary dots at every point. Pair with an exact main value and textual trend/delta.
- **Heatmap:** cells 20–32 px, 4 px gaps, 6–8 px radius; sequential shades of one approved hue; explicit range legend and keyboard-visible value inspection. Zero, missing, and unavailable are distinct states.
- **Tooltip:** white, 16 px radius, 12 px padding, optional subtle border/shadow; 12 px labels, 14 px values, series swatch; pointer or keyboard focus anchors it to the data. A data point's value must remain accessible without pointer hover.
- Provide chart title, units, period, data description, legend, empty/error/loading state, and a tabular alternative or downloadable data when detailed analysis is expected. Respect number/date locale; preserve decimal precision appropriate to the measurement.
- **Maps:** keep base-map contrast quiet; use white 24 px-radius controls, 44 px circular zoom actions, and black selected markers with white labels. Signal-colored markers must have a legend and shape/label distinction. Cluster counts are neutral black/white pills. Location detail appears in a standard popover/drawer, not a novel visual style. Provide a synchronized accessible result list; the map cannot be the only way to find or select records.

**Scatter/bubble/histogram charts:** reuse [Charts, analytics and maps](charts-maps.md) chart card/axis contracts. Scatter markers default 6px, selected 10px with contrasting ring; shape/direct labels distinguish series. Bubble size requires a size legend and area-proportional encoding. Histogram bars touch or have 2px gap to communicate bins, with explicit bin ranges; use modest 2–4px rounding, not pill bars that obscure bin continuity. A value table remains available for exact inspection. Do not infer these plots from the source's miniature chart.
