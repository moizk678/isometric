# Calendars, schedules, boards and timelines

**Read when:** Scheduling calendars, agenda, timeline, kanban, checklist, Gantt or reordering; not date input.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** [Date and time pickers](date-time.md), [Tables, filters and bulk actions](tables.md)  
**Load only for this variant:** Editing a schedule item through date/time fields → [Date and time pickers](date-time.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Calendars, scheduling, timelines, and task boards [E]

**Calendar view.** Outer white panel with 32 px radius; header has 18 px month/week title, 44 px previous/next circles, and a local view switch. A month grid has 7 equal columns, **32 px** weekday header, **112 px minimum** day cells on desktop, 1 px neutral grid lines, and **8 px** cell padding. Date numbers sit in a 28 px circle at the upper logical end. Today uses a 1 px black outline around its 28 px date circle; selected date uses a black circle/white numeral and selection adds a separate outline around the cell or event. Out-of-month dates use muted text, not disabled semantics unless interaction is actually unavailable.

- Calendar events are **24–28 px** high, 12 px text, 8 px radius, neutral fill, with a **3 px** semantic color stripe when status needs emphasis. Event titles truncate with a full readable detail affordance. Show at most 3 short events in a small day cell before `+N more`; overflow opens that day's list.
- For narrow layouts, use agenda/day view instead of shrinking a seven-column month until labels become unreadable. Preserve the selected date and active filters when changing view.
- Week/day schedule uses a **56 px** time gutter and a shared vertical time grid, **64 px per hour** as the comfortable default. Work-hours shading remains a subtle neutral change. The current-time line may use the coral semantic accent only if explained; include a time label. Overlapping events divide available columns with **4 px** gaps and never cover each other's title entirely.
- Event drag/drop has a clear 1 px black outline/ghost, snap interval visible in the interface, live preview of time/date, and an undo path. Provide an equivalent edit action with date/time controls. Time zone, locale, first day of week, and working days are configuration, not inferred from the original image.

**Timeline/activity feed.** Shared warm-neutral inset block, 24 px radius, **16 px** padding; rows use a 36 px signal disc, 12 px gap to text, 14 px event title, 12 px secondary context, 12 px time at the trailing edge, and **16 px** vertical rhythm. Dividers are 1 px neutral and align with the content body. For chronological process timelines, add a **1 px** connector behind the disc centers with **8 px** gaps around discs. Group by readable day headings. Exact timestamps remain available when relative dates are used.

**Kanban.** White or shell-neutral board containing warm-neutral columns, **280–320 px width**, 24 px radius, 16 px padding, 16 px gaps. Column header uses 14 px medium title plus neutral count and a 36 px add/overflow action. Cards are white, **20 px radius**, 16 px padding, with 12 px content gaps; title 14 px, metadata 12 px, one clear status marker, and optional 28 px avatars. Do not color every column/card by category. Dragged card uses a thin black outline and one temporary floating shadow; drop target uses a neutral placeholder of equal height. Provide `Move to…` keyboard/menu control. Board scrolls horizontally on narrow screens, with an alternative list view for linear reading and accessible editing.

**Task/checklist.** A row has 44 px minimum height, 20 px completion control within a 44 px target, 12 px text gap, and optional 12 px due/owner metadata. Completed text uses secondary ink and an optional restrained strike-through; don't reduce contrast so far that completed items disappear. Keep expansion, navigation, and completion as distinct controls.

**Gantt/project schedule:** adapt the table+timeline split with a min 280px label pane,56px rows,1px subtle time grid,24px-high capsule task bars, and black selected outlines. Use green for a consistent thematic series, not “success” without status evidence. Milestones are small outlined diamonds; progress is a darker inset fill with numeric alternative. Dependencies get thin neutral connectors. Horizontal timeline scrolling is local; dates remain available in row details. Drag resize/move always has date/duration form equivalents.

**Reorderable list.** Use ordinary inset rows plus a 20 px grip inside a 44 px target. Resting grip is secondary ink. During drag, reserve the exact row height and show a 2 px black insertion line. Offer `Move up`, `Move down`, or `Move to…` controls for keyboard and assistive technology. Announce the new position after a move. Do not make the entire text row draggable if it also contains selectable text or links.
