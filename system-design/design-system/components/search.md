# Search and command palette

**Read when:** Search fields, predictive/remote search, result overlays or a command palette.  
**Requires:** [Shared field contract](field-basics.md)  
**Related (optional; do not automatically load):** [Selects, comboboxes and tag entry](selects.md), [Dialogs, drawers and sheets](dialogs.md)  
**Load only for this variant:** Predictive or suggestion search → [Selects, comboboxes and tag entry](selects.md); Command palette dialog → [Dialogs, drawers and sheets](dialogs.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Search and search results [E]

A standalone search field is 44px high, radius 22px, white when on the app canvas and inset-neutral when inside a white panel. Leading magnifier is 18px; left padding 16px; text begins after a 12px gap. Search value is 14px. Clear control is trailing. A desktop keyboard shortcut hint is optional: 24px high, 6px radius, 11px text, neutral border; omit on touch and do not reserve empty space for it.

For simple list filtering, change results in place after a 250ms typing pause; Enter executes immediately. For remote search, cancel or ignore stale requests, retain the query, and expose loading, success count, empty, and failure states. Do not announce the entire result list after every keystroke.

For predictive search, load and apply [the select/combobox contract](selects.md). Result overlay: anchor gap 8px; match or exceed trigger width when space permits, capped at the visual viewport width minus 24px; radius 24px; `--surface-panel`; 1px `--stroke-control`; subtle overlay elevation token. Padding 8px; row minimum 44px; row radius 16px; row padding 10px 12px. Primary result text 14px/20px; secondary text 12px/18px. Highlight matching query text by weight, not fluorescent fill. Group labels use 11px/16px secondary text, medium, normal letter spacing. A useful empty state echoes the query, offers correction, and does not invent results.

**Command palette.** Standard 560 px dialog shell, 24 px radius; search row 56 px high; results use 44 px rows, 16–20 px icons, 14 px labels, 12 px contextual text/shortcuts; groups use 12 px muted labels. Active keyboard result gets a neutral highlighted row and black focus marker. Up/Down move results, Enter executes, Escape closes, and focus restores. Discoverability needs a visible launch action; a keyboard shortcut alone is insufficient. Searchable entities and commands are visually labeled as different result types when both appear.
