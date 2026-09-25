# Tables, filters and bulk actions

**Read when:** Operational tables, sorting, facets, grouping, expansion, tree tables, selection or virtualization.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** [Selects, comboboxes and tag entry](selects.md), [Choice, range and color controls](choice-controls.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Data tables, filters, sorting, grouping, and bulk actions [E]

**Table hierarchy.** Outer panel: white, 32 px radius, **16–24 px** padding. Title/subtitle occupies the upper logical start. A compact status pill or count and one icon action may occupy the upper logical end. A filter toolbar sits **16 px** below the title; headers sit **16 px** below the toolbar. For a short dashboard preview, omit a redundant toolbar and preserve the lighter title → column labels → inset rows sequence.

| Table element | Default specification |
|---|---|
| Column header | 12 px / 16 px secondary text; 36 px minimum row height; 12–16 px horizontal insets |
| Comfortable data row | 72 px minimum height; 24 px radius if rows are visually separate; 8 px vertical gap |
| Compact data row | 48–56 px minimum height; 16 px radius for separated rows; 4–8 px gap; reserved for information-dense pointer workflows |
| Primary cell | 14 px / 20 px primary ink; optional 12 px / 16 px subtitle with 2–4 px gap |
| Numeric cell | Tabular numerals, logical-end aligned; comparable units aligned consistently |
| Row action | 36 px pill, 14 px label; 1 px control border; 12–16 px horizontal padding |
| Selection cell | 44 px wide; 20 px check control centered within a 44 px target |
| Sort affordance | 14 px chevron/arrow beside a header, with 4 px gap; active header primary ink |
| Inline status | 28 px signal disc plus 8 px label gap, or a labeled pill; never a full colored row by default |
| Small meter | 64 px width, 16 px height; segmented or continuous; 8 px from its numeric label |

- Preserve header/cell alignment through a real table or a shared grid definition. Do not independently distribute each row with `space-between`, because long values will break column alignment.
- Define columns as schema: label, data type, width/minimum width, alignment, priority, sorting capability, visibility, and formatter. Example proportional mix for a business table: primary entity **28%**, issue/context **25%**, organization **13%**, metric **14%**, date **8%**, action **12%**. These percentages are a starting configuration and must be adjusted to content length; do not carry them unchanged into unrelated domains.
- Reserve adequate action width instead of allowing long titles to push buttons outside the card. Wrap primary titles to two lines when necessary. Ellipsize low-priority subtitles after one line, with a complete accessible name or detail view; do not hide critical status or deadline text in a tooltip alone.
- A sortable header is a button within a header cell. Cycle explicitly through ascending → descending → unsorted only if the product allows unsorted order. Display an arrow and expose sort direction. Sorting does not reset filters or selection silently.
- Multi-column sorting, if supported, includes a small numbered order badge and a visible reset option. A table with only one sort priority must not imply multi-sort.
- Filter controls use compact neutral pills. Applied filters appear as removable chips below the toolbar, wrapping with **8 px** gaps. Show an explicit `Clear filters` action when any are active. Filter counts and query changes update a visible result count.
- Search results distinguish `No records yet` from `No matches for these filters`. Preserve the query and filters when no matches exist.
- Column-visibility menu: checkbox-style menu items, 36 px minimum row height, 8 px panel padding. Mark required columns as fixed and explain why. Reordering columns requires a non-drag alternative.
- For grouped data, group header uses a 36–44 px row, 12–14 px medium label, a small count, and a chevron. Group children indent **16 px per level**, maximum visual indent **48 px** before switching to breadcrumbs/flattening. Do not use both deeply nested padding and many nested card outlines.
- Expandable rows put detail in a full-width inset region immediately below the row, **16 px** padding, with an independent expanded state. The first-cell chevron controls disclosure; the row title may remain a separate navigation link.
- Tree tables must have explicit hierarchy, expansion, level, and selection semantics. Provide arrow-key tree navigation only when the full tree/grid behavior is implemented; ordinary tables should use normal Tab navigation through interactive controls rather than an incomplete spreadsheet keyboard model.
- Bulk selection reveals a **52 px** high neutral or white action bar above the table, with selected count at start, applicable actions at end, and a clear-selection control. Keep the bar in the layout or reserve space to prevent rows jumping. A black selected-count pill may emphasize the state; do not turn the entire table header black.
- The header checkbox shows none, all, or mixed selection. Distinguish `Select this page` from `Select all N filtered results`. Never imply that off-page items are selected without explicit feedback. Bulk destructive actions use a confirmation that names the count and scope.
- Row actions that repeat use one labeled primary action plus an overflow menu where needed. On touch, show the overflow trigger persistently. Do not reveal the only edit/delete action exclusively on hover.
- A sticky header uses an opaque parent-surface background, not a translucent blur that lets cell text bleed through. Sticky leading/trailing columns require a 1 px separator and enough scrolling room to leave at least 160 px of useful middle content.
- Large tabular datasets scroll horizontally within the table region. Preserve 12–16 px panel insets at the edges and label the scrollable region. Below **720 px component width**, an alternate stacked-record view is allowed when users do not need cross-row column comparison. Stacked rows preserve primary title, key status, metric/date, and action; secondary columns move into a labeled detail expansion.
- Virtualized tables preserve total row count, stable record identity, selection, focus, and accessibility semantics. Loading more rows must not throw focus to the page top. Use a skeleton or progress cue inside the table, not an unrelated global spinner.

**Result facets:** use accordions in a 232–280px facet column or a mobile filter sheet. Checkbox rows 44px, muted counts aligned end,12px gaps between groups, optional searchable facet input. Selected facets appear as neutral/black chips above results. Include explicit Clear filters; use Apply only if the filter model is a draft. Never mix immediate and draft updates without explaining the boundary.
