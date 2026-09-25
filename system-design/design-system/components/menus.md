# Menus, popovers and tooltips

**Read when:** Commands, context/submenus, checkbox/radio menu items, popovers or tooltips; not value selection.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** [Selects, comboboxes and tag entry](selects.md), [Dialogs, drawers and sheets](dialogs.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Dropdown menus, context menus, popovers, and tooltips [E]

- **Menu surface:** white, **24 px radius**; **8 px padding**; **1 px** subtle control stroke where contrast against white is needed; shared `--shadow-overlay`. Default width **240 px**, minimum **192 px**, maximum **320 px** unless the content is genuinely a popover form.
- **Menu item:** **36 px minimum visual height**, 12 px horizontal padding, 12 px internal radius, 14 px label, optional 16–20 px leading icon with 8 px gap. Touch menus increase item target height to **44 px**. Trailing shortcut text uses 11–12 px muted ink. A submenu chevron is 14 px.
- **Menu hierarchy:** group label is 11–12 px muted, with 8 px horizontal inset; separator is 1 px neutral with 8 px vertical margins. Keep groups small. Do not use a large colored menu header for ordinary actions.
- **Danger item:** explicit destructive verb and a coral icon/dot; label remains primary ink unless a contrast-checked dark danger-text color is available. Hover remains a subtle neutral treatment rather than abruptly flooding the row red.
- **Checkbox/radio menu:** allocate a consistent 20 px selection column. Selected checkmark is black. Menu selection is not the same as current hover/focus. For a single-choice list of values, use the custom select/listbox pattern, not an action-menu role.
- **Context menu:** same visual rules, anchored to the pointer or focused item's context-menu key. Always expose the same actions through a visible overflow button for touch and discoverability.
- **Popover:** default width **320 px**, range **240–400 px**; 24 px radius; 16 px content padding; optional 14–16 px title; 12 px heading/content gap. Keep short explanatory or filtering tasks here. Promote long forms and multi-step tasks to a drawer/dialog.
- **Positioning:** preferred edge is below the trigger, aligned to its logical start or end; **8 px** anchor gap; **12 px** viewport safe margin. Flip or shift to remain in view. Maximum height is `min(320px, viewport height − 24px)` for short menus, with internal scrolling. Never let a menu stretch beyond the usable visual viewport or sit behind the keyboard.
- **Tooltip:** primary-ink surface, white 12 px / 16 px text, **8 px vertical / 12 px horizontal padding**, **10 px radius**, maximum width **240 px**, 8 px anchor gap. No interactive contents. Reveal after approximately **500 ms** pointer dwell or immediately on keyboard focus; dismiss on Escape or after pointer/focus leaves both trigger and tooltip; allow pointer travel into the tooltip without closing it. Essential text is present in the control label or accompanying content, not only here.
- Menus open on click/Enter/Space, not hover alone. Up/Down traverse items; Home/End jump; typeahead matches labels; Enter/Space activates; Escape closes; focus returns to the trigger. Submenus support logical-forward to open and logical-back to close.
- A popover with interactive controls does not use tooltip semantics. Choose whether it is modal or nonmodal explicitly. Nonmodal popovers preserve a sensible Tab path; modal popovers constrain focus and restore it on close. Click-away closes only when doing so will not silently lose meaningful input.
- Only one sibling menu remains open at a time. Nested layers follow a controlled stack so Escape closes the uppermost surface first. Do not allow unrelated overlays to accumulate.
