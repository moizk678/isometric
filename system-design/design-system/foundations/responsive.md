# Responsive composition

**Read when:** Building or changing page layouts, mobile behavior, breakpoint rules or content reflow.  
**Requires:** [Design tokens](tokens.md)  
**Related (optional; do not automatically load):** [Typography, geometry and rhythm](typography-geometry.md), [Visual principles and domain translation](../guides/translation.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Responsive screen contract

The screenshot supplies only a wide desktop state. The following breakpoints are new design rules. Use component/container pressure as the final signal; these viewport bands are defaults for the pictured composition, not original-source facts.

| Viewport / available space | Workspace and navigation | Content composition |
|---|---|---|
| Wide desktop, ≥1600px | Center max 1594px workspace; presentation margin may reproduce source at 1790px; 18–24px workspace inset; full nav/search/profile | Two unequal top columns; table +≈399px activity rail; four metrics in one row |
| Desktop, 1440–1599px | 24–32px outer margins; frame may fill available width; shorten search or move it to second row before nav crowds | Top split may remain if feature≥600px and metric area≥680px; bottom table gets full width and activity moves below if table would be<1100px |
| Small desktop/tablet landscape, 1024–1439px | 16–24px outer margins; menu/compact top nav, full-width search on second line as needed; profile name optional | Feature and metric group stack; metrics remain four across only with≥680px internal group width; table full width with controlled horizontal scroll when comparison needs it |
| Tablet, 768–1023px | 16px page padding; 52px header row with logo, menu, search action, profile; destination list opens in drawer | Single main column; metrics 2×2; activity below work queue; page controls wrap beneath title |
| Mobile, 360–767px | Workspace becomes page background, no taupe presentation mat; 12–16px page padding; 44px controls; no fixed-width nav rail | Single column; metrics 2×2 if each≥144px otherwise 1×4; task rows become labeled records; charts and tables adapt locally |
| Narrow, 320–359px | 12px page padding; long names/labels wrap; optional profile name and secondary header utilities move into menu | Metrics 1×4 if content demands; compact hero; all overlays fit; date picker uses its specific narrow-grid contract |

**Desktop panel minimums take precedence over preserving the two-column screenshot.** A full page should never scroll horizontally merely to retain a decorative layout. Intrinsically two-dimensional data such as a comparison table, code block, map, or kanban board may scroll in its own labeled region.

## Element-specific reflow

- **Greeting:** reference 44px; product desktop 36–44px, tablet 32px, mobile 28–32px; line-height≈1.15. Allow natural wrapping. Supporting sentence can break before the date; do not shrink it below 14px to stay on one line.
- **Hero value:** reference 108px; use a container-aware scale down to 56–64px on mobile. Preserve all digits. If a longer amount does not fit, wrap chart below the value and widen the value area first. Use abbreviated currency only when the product expressly permits it and exposes the full amount.
- **Hero chart:** desktop beside the value; narrow layouts below the caption in a dedicated row. Keep six labels readable or reduce tick frequency with a full data alternative; do not compress bars into indistinguishable slivers.
- **Hero facts:** three columns above 600px content width, then stacked labeled rows with horizontal separators; strip radius 16px. Keep labels with their values.
- **Metric tiles:** desktop source 263px high; new product defaults 200–240px; mobile 152–176px minimum. Preserve label/top icon and value/bottom support grouping but let content determine final height. Avoid a huge empty middle on a narrow phone.
- **Header controls:** date scope and primary action wrap as two separate groups with 12px gap. On mobile the primary action can fill a line; the scope pill remains horizontally usable. No disappearing primary action.
- **Attention records:** mobile anatomy is icon+title → metadata → labeled blocker → organization + deadline → metric + primary row action. Use 16px row padding and 12px gaps. Show “Due” and other formerly column-provided labels explicitly. Preserve every essential fact; put only secondary optional fields in details.
- **Activity:** keep icons 36px; move timestamp beneath context or align to the top-right when space is insufficient. Long primary events may wrap. Desktop truncation of secondary text should not force mobile clipping.
- **Header search:** compact magnifier opens the same search experience in a full-width row or dialog; it is not a different search scope. Preserve typed query across presentation changes.
- **Panels:** use 32px outer radius on spacious desktop,24px on mobile panels; inner radius 16–20px where needed to keep concentric geometry. Do not crowd a 320px screen with 36px padding/radii everywhere.
- **Zoom and text enlargement:** fixed screenshot card heights are reference-mode targets only. Product panels grow with text; actions and helpers remain reachable at 200% and 400% zoom. Test both content reflow and on-screen keyboard occlusion.
