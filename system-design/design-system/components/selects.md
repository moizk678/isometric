# Selects, comboboxes and tag entry

**Read when:** Single/multi select, listbox, editable or async combobox, tags or transfer lists; not command menus.  
**Requires:** [Shared field contract](field-basics.md)  
**Related (optional; do not automatically load):** [Menus, popovers and tooltips](menus.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Custom select, listbox, and combobox: choose the correct primitive [E]

| Primitive | Use | Keyboard / semantic contract |
|---|---|---|
| Select-only control | Choosing one value from a known list with no text entry. | Trigger exposes its label, current value, expanded state, and associated listbox. Enter/Space opens; arrows move through enabled options; Home/End move to bounds; typeahead jumps by label; Enter commits; Escape closes without committing the highlighted draft. Follow the applicable accessible select-only combobox/listbox pattern consistently. |
| Editable combobox | Querying/filtering options with a text input. | Input keeps text-editing behavior. Down Arrow opens/moves into options; Up/Down move active option; Enter selects only the active option; Escape closes suggestions while preserving typed text; Tab proceeds without silently committing an unrelated option. Announce active option and result count appropriately. |
| Persistent listbox | Options are the visible control rather than a transient popup. | Accessible label is outside. Arrow keys move among options. Selection behavior is explicit; multi-selection provides a discoverable model and does not require a modifier key for ordinary pointer use. |
| Action menu | Commands such as edit, duplicate, archive. | Use [the menu contract](menus.md). Do not implement an action menu as a value select. |

**Select trigger:** default field dimensions; value left; 16px downward chevron right. Placeholder uses `--ink-muted`. When open, chevron may rotate 180° over 120ms; avoid layout movement. The entire trigger activates. Do not use a browser-styled select popup when a visually custom dropdown is required; retain the corresponding semantic form behavior.

**Select overlay:** match the trigger width by default. A wider content-driven popup normally caps at 480px, but a trigger wider than 480px keeps a matching popup when space permits. The final width always caps at the visual viewport width minus 24px; this viewport cap takes precedence over trigger matching. Use maximum height `min(320px, available viewport height − 24px)`; open 8px below, flip above when necessary, then shift within 12px viewport margins. Radius 24px; padding 8px; white panel surface; shared 1px overlay boundary; overlay elevation. Scroll only the option area, leaving any search header and footer accessible. Never clip the popup in a scrolling card.

**Options:** minimum height 44px; radius 16px; padding 10px 12px; gap 10px. Optional 18px leading icon; label 14px/20px; optional description 12px/18px underneath; reserved 18px trailing check slot. Hovered or keyboard-active unselected option uses `--surface-inset`. Selected single option uses near-black fill with white text and checkmark; selected and active simultaneously keeps black fill plus visible focus indication. For persistent multi-select lists, use neutral row fill with an explicit checked checkbox; do not turn the whole list black. Disabled rows are visibly subdued, announced disabled, skipped by ordinary selection, and never receive misleading hover affordances. Group separators are 1px neutral strokes with 8px vertical margins; headers have 8px 12px padding. Long labels wrap to two lines when needed, with descriptions below; never hide the only distinguishing text.

**Multi-select:** input minimum height 44px, auto-expands to accommodate chips, radius 22px. Padding 6px 8px; chips 28px high/radius 14px, gap 6px, neutral inset fill on white or white on inset. Chip text 12px/18px; remove icon 12px inside a named 24px desktop target. On touch, removal is offered by an accessible 44px action or a full-size selection-management panel. Label each removal action `Remove [value]`. Backspace removes the last chip only when the text input is empty and that chip is intentionally targeted; announce removal and retain focus. Show the full selection in expanded edit state; collapsed summaries may show two chips plus `+N` but that summary opens the full list. Optional `Clear all` appears only after selection and affects only this field. In a multi-select listbox, Space toggles the active option while arrows navigate; Escape closes without resetting committed selections. State whether selection is immediate or requires Apply; default is immediate.

**Editable/remote combobox states:**

1. Idle, before query: useful recent options or a brief minimum-character instruction.
2. Querying: spinner with `Searching…`; keep previous results only if clearly marked stale and never select them accidentally.
3. Results: expose active option and count; selected values remain visible.
4. No matches: `No matches for “[query]”`; optional create action only if the domain permits creating that entity.
5. Request failure: compact error plus `Retry`, without losing query or selection.
6. Loading additional results: footer spinner; maintain scroll and active item. Paginate or virtualize large lists without losing announced position, active-option visibility, or selected values.
7. Cleared: return to placeholder, retain focus, and communicate changed selection.

## Tag input and structured token entry [E]

Tag entry uses the multi-select capsule/chip geometry, but may accept user-created strings. State accepted delimiters and any uniqueness/length rules before entry. Enter commits the current valid token; comma commits only when commas are not valid token content. Pasted lists are parsed predictably and duplicate tokens are reported or merged without data loss. Invalid draft text stays editable; a chip becomes invalid only if a previously accepted value later fails validation. `Remove [tag]` actions are named. Long tokens use a maximum chip width that leaves room for removal and an accessible full-value inspection. Email-recipient variants validate each address, keep display name and address distinguishable, and never silently send or submit when committing a token.

**Transfer/dual-list control:** two equal white or inset panels,24px radius,16px padding; searchable 44px option rows with checkboxes; central 44px named Add/Remove arrow controls. Show selected and available counts. On mobile stack lists and replace direction-dependent arrows with explicit verbs. Preserve ordering and provide move controls if order matters; no drag-only transfer.
