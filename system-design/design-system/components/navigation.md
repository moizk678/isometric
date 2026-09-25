# Navigation and trees

**Read when:** Top nav, tabs, segmented controls, sidebar, breadcrumb, pagination, stepper or tree explorer.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** None.  
**Load only for this variant:** Collapsed navigation presented as a drawer → [Dialogs, drawers and sheets](dialogs.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Navigation systems [E]

**Primary horizontal navigation.** Use a white pill track, **52 px** high, **4 px** internal padding, with 44 px items. The active destination is a black pill; inactive items are transparent with primary or secondary ink. Use **16–20 px** horizontal padding per item, **14 px** text, and no underline. Keep the track as a cohesive group rather than separate bordered buttons. Active-page state is independent of pointer hover.

**Local tabs.** Use a neutral inset pill track at **44 px** height with **4 px** inset and **36 px** child pills, 14 px labels, and black selected state. Default tab lists contain **2–6** choices. Tabs that change a local panel expose the tab/tablist relationship; navigation between URLs uses links and current-page state. Do not interchange these semantics because their visual treatment matches.

**Time-range/segmented controls.** Use the same 44/36 px nested pill geometry. Equal widths are appropriate for short comparable labels. Content-sized widths are appropriate for longer localized labels. Selection must be visible without a sliding animation. If a change would discard unsubmitted input, use explicit activation instead of silently changing the view on arrow-key focus.

**Sidebar extension.** This is a new layout option, not a detected screenshot feature. Use a **232 px** expanded width or **72 px** rail, white or shell-neutral surface, **16 px** outer padding, and **44 px** nav items with **12 px** horizontal padding and 12 px icon/label gap. Active item: black pill. Group labels: 11–12 px muted, with **24 px** space above a group. Limit a group to a coherent set of destinations rather than compressing rows below 44 px. A rail must give each icon a tooltip and accessible name. Use a drawer below the width where both content and sidebar cannot fit; do not reserve an empty narrow strip.

**Breadcrumbs.** 12–13 px text, 16 px line height, 8 px gap around a 12 px chevron separator. Ancestors use secondary ink and hover underline; current location uses primary ink. Place **12 px** above the local title. On narrow screens, retain a back link and current item; hide the middle trail behind an explicit overflow menu if needed. Do not truncate all levels into identical ellipses.

**Pagination.** 36 px circular number buttons, **4 px** gaps; selected page black/white; previous/next use 36 px icon buttons. In touch layouts, use 44 px targets. Place totals/results range in 12 px muted text at the logical start, page controls at the logical end, with a **16 px** gap. Large page sets use one ellipsis per omitted contiguous range; an ellipsis is not an enabled page unless it opens a documented jump control. Preserve search, sort, and filters across page changes.

**Stepper.** 28 px numbered circles with 12 px labels and 8 px circle/label gap; 1 px neutral connecting lines; current circle black/white; completed circle green with a check; future steps neutral. On narrow screens show `Step N of M`, the active label, and the local progress bar. A visual stepper does not imply that future steps can be clicked.

- Nav icons are 20 px; keep icon style and alignment constant. Optional counts use small neutral count pills. Do not add bright counts to every destination.
- Keyboard: primary links follow normal Tab order. Tabs use one tab stop in the active set; Left/Right move within the tab list, Home/End go to first/last; Enter/Space activates when manual activation is appropriate. Vertical tabs use Up/Down. Focused and selected tabs must be independently discernible.
- Preserve a stable back path in detail screens. Browser back behavior and unsaved-state handling must remain coherent when a menu, drawer, or overlay closes.
- A long top-level navigation must collapse or deliberately scroll as a navigation region before labels collide with search/profile controls. Never squeeze labels into unreadable abbreviations.

**Tree explorer.** 36–44 px rows, 16 px per-level indentation, 16 px chevron, 20 px optional file/folder icon, 8 px gaps, selected row neutral with a 1 px black inset outline. Use logical-forward/back to expand/collapse, Up/Down for visible rows, Home/End for endpoints, and typeahead. Multi-selection and drag reordering are separate explicit modes with non-drag alternatives.
