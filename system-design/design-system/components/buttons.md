# Buttons, links and action groups

**Read when:** Primary/secondary/quiet/destructive buttons, icon/split/toggle controls or links.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** None.  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Buttons, links, action groups, and icon buttons [E]

| Variant | Geometry and appearance | Appropriate use |
|---|---|---|
| Primary | 44 px high; 20 px horizontal padding; 22 px radius; `--ink-primary` background; white label; optional leading 20 px icon with 8 px gap | One principal action in a local decision area |
| Secondary | 44 px high; 20 px horizontal padding; white; 1 px `--stroke-control` border; primary ink | Review, cancel, open detail, ordinary secondary actions |
| Quiet | 44 px high; 16 px horizontal padding; transparent; primary ink; neutral hover/pressed background | Tertiary actions where a full outline adds noise |
| Destructive confirmation | 44 px high; primary-ink label on `--state-danger` fill only when sufficient label contrast is verified; otherwise black primary button with explicit destructive verb and a coral warning elsewhere in the dialog | Final confirmation of a destructive action, not every delete menu item |
| Compact | 36 px high; 16 px horizontal padding; 18 px radius; 13–14 px label | Table row actions, toolbar controls on pointer-driven layouts |
| Icon button | 44 × 44 px; circular; 20 px icon centered; `--surface-inset` or white according to surrounding surface | Settings, overflow, close, next, back, filters |
| Floating directional action | 44 × 44 px; white disc on a colored or inset card; 20 px diagonal arrow | Navigate to the detail behind a highlighted card |
| Text link | 14 px; primary ink; underline in body prose, hover underline in clearly navigational lists; 2 px underline offset | Real navigation, not state mutations |

- Button anatomy: optional leading icon → label → optional trailing chevron. All content is vertically centered. Do not use both a leading and trailing decorative icon without a functional reason.
- Minimum text-button width is **88 px** for short action labels. Longer labels grow naturally. Avoid fixed widths that truncate important verbs. On mobile, a sole primary action may stretch to the content width; paired dialog actions may stack.
- Loading replaces a leading icon with a **16 px** spinner or reserves that slot. Keep the original label or change it to a specific progressive verb; ensure the accessible name still identifies the operation and includes the visible label. Preserve width to prevent layout shifts. Disable duplicate submission without removing focus from the action.
- Primary/secondary action groups use **12 px** internal gap. In a dialog footer, put the primary action at the logical end; cancel immediately before it. Keep destructive and safe actions verbally distinct.
- Split buttons have one pill envelope, a **44 px** main height, a main action region, and a **44 px** menu trigger region separated by a **1 px** vertical divider with **12 px** top/bottom insets. Both regions are independently focusable and named; the main action is never triggered by opening the menu.
- Toggle icon buttons change to a black background/white icon when active and expose pressed state. The focus ring remains separate from the selected treatment.
- For dark or colored cards, use a white secondary action with black content. Preserve the black-primary hierarchy elsewhere; do not proliferate unrelated inverse button variants.
- Keyboard: buttons activate with Enter or Space; anchors navigate with Enter. A link must have a meaningful destination. Do not implement all controls as nonsemantic clickable containers.
