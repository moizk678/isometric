# Shared interaction contract

**Read when:** Implementing interactive controls, component states, overlays, focus, motion or shared behavior.  
**Requires:** [Design tokens](tokens.md)  
**Related (optional; do not automatically load):** None.  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

Every component module inherits this shared interaction contract. Local rules may specialize it but must not silently reverse it.

## Control states

| State | Visual treatment | Behavior |
|---|---|---|
| Rest | Neutral warm/white surface; primary text | Clearly communicates its role |
| Hover | Subtle `--surface-hover` or light darkening of black control | No movement or unsolicited enlargement; hover never substitutes for selection |
| Pressed | `--surface-pressed`; black controls brighten slightly to `#242424` | Optional static-safe `scale(0.96)` on standalone buttons only; no scale on rows, input fields or overlays |
| Focus-visible | 2px `--focus-ring` outline with 3px offset; inverse ring on dark surfaces | Always visible, unclipped; preserve ring when error/selection is also present |
| Selected | Black pill + white text for single-choice navigation; subtle selected row + explicit check for records | Selection persists independently of hover and focus |
| Disabled | Neutral low-emphasis fill/text; no hover/press | Explain cause when non-obvious; don't rely on opacity alone to communicate unavailable state |
| Read-only | Normal legible value; muted edit affordance removed | Focus/copy where appropriate; distinct from disabled |
| Loading | Reserved-size spinner/skeleton, stable label/width | Prevent duplicate submission; announce relevant progress without repeated noise |
| Error | `--ink-danger` text + explicit message + icon; field boundary uses dark danger ink | Preserve user input; explain recovery; not only a red border |
| Success | Positive disk or concise confirmation | Show only when useful; do not turn all valid fields green |
| Empty | Clear reason + one relevant next action | Distinguish no data, no matches, no access, and failure |

For validation, the focus ring stays outside the error border. For loading, the control remains identifiable and its accessible name continues to communicate the action and busy state. A visible progressive label such as “Saving…” must remain represented in that accessible name. Disabled should take precedence over hover/press; focus remains where needed for an operation in progress. Hover, focused option, selected option, checked, expanded, busy, invalid, and read-only are separate states, not synonyms.

## Sizes and hit targets

- Default field/action: **44px high**, horizontal padding **16px**, **22px radius**, 14px text/20px line-height.
- Compact action: **36px high**, horizontal padding **12px**, pill radius. Use for dense desktop contexts with at least a **40px** effective pointer region if space permits; avoid overlapping expanded hit regions.
- Large header action: **52px high**, horizontal padding **20px**; 16px text.
- Icon-only button: **44×44px**, circular; 20px icon. Large header utilities may use 52px/24px.
- Touch-first controls: target **44×44px minimum** including interactive calendar cells and check/radio labels. If a compact visual must stay smaller, enlarge its non-overlapping clickable container.
- Leading icon gap: **8px**; label to trailing chevron: **12px**. Adornments must not encroach on entered text.
- Field label sits **8px** above the field; helper/error sits **6px** below. Field stacks have **20px** gaps; grouped columns **16px** gaps; sections **32px** gaps.

## Overlay geometry and layering

Floating surfaces use white fill, 24px radius, 1px subtle border where necessary, and `--shadow-overlay`. Anchor gap 8px; minimum viewport inset 12px. Flip or shift placement to remain visible. Dropdown height normally max 320px with internal scroll; dialog body scrolls within the viewport. Do not clip overlays inside rounded parent panels.

Use a coherent overlay stack: page < sticky areas < popovers < modal < modal-owned popovers < toast. Token z-index values are base levels, not permission to put a background dropdown above a modal. A popover opened inside a dialog belongs to that dialog's layer and focus context. Only modal surfaces trap focus and make the background inert. Menus/listboxes/popovers normally do not trap focus.

## Motion

Use 120ms for hover/press, 180ms for dropdowns and selection changes, 240ms for drawers/dialogs. Standard easing is `cubic-bezier(0.2,0,0,1)`. Overlay entry: opacity 0→1 and translateY 4px→0; exit uses shorter opacity transition. Avoid spring bounce, parallax, animated gradients, delayed chart reveals, and layout-shifting count-up numbers. Use explicit transitioned properties, never `transition: all`. Reduced motion removes translation/scale and nonessential animation. No animation is required to understand a change.

## Content resilience and component API contract

All components support stable IDs, accessible names, controlled/uncontrolled value where appropriate, disabled/read-only/busy/invalid states where meaningful, empty/loading/error data, long/localized text, and arbitrary container width. Expose semantic variants such as `primary`, `secondary`, `quiet`, `danger`, `size`, `density`; do not expose arbitrary per-instance colors that dissolve the design system.

Use CSS logical padding/margins. Allow labels and errors to wrap. Truncate only secondary compact-list content with a full-detail route; don't truncate important action names or validation. Never create nested interactive elements such as a button inside a link. Maintain semantic order when visual grids collapse.

**Evidence boundary:** Each reusable component specification is an **extension [E]**: a deliberate rule for components or interactions that the static reference does not demonstrate. It translates the reference's visual vocabulary into a reusable web design system; it is not a claim that hidden screens, keyboard behavior, or responsive layouts were observed. Observed measurements and tokens in [Design tokens](tokens.md) take precedence when reproducing the reference itself.

## Component implementation contract [E]

Inherit [Design tokens](tokens.md) tokens and [Shared interaction contract](interaction.md) states, sizes, focus, motion, overlays and semantics. Component-specific geometry in component modules is an explicit variant of that contract. Body/control text is 14/20px; secondary component text is 12/18px; local headings are 18/24px unless a larger composition specifies otherwise. Use semantic tokens rather than attaching colors to business nouns. All static panels stay flat. Menus, popovers and toasts use `--shadow-overlay`; modal dialogs/sheets use `--shadow-dialog` and `--overlay-scrim`. Tooltips may use the small overlay shadow without inventing another elevation scale. There is no opacity-only disabled style or separate component-specific focus/motion system.

## Global behavioral and quality rules [E]

1. **Responsive behavior is component-driven.** Use available width and content pressure, not an assumed original device. Preserve 44 px touch targets, wrap text/actions deliberately, collapse navigation, stack metric tiles, and switch tables/calendars to suitable alternatives before shrinking type below readable sizes.
2. **Maintain reading order.** The DOM/accessible order follows title → summary → controls → content → supplemental detail. Responsive visual reordering must not make keyboard traversal jump across the page unpredictably.
3. **Use logical positioning.** Prefer logical start/end over hardcoded left/right for padding, actions, chevrons, and badges. Localize labels, dates, numbers, plural counts, and currency. Allow labels to grow by at least **30%** without clipping controls.
4. **Support zoom.** At 200% text/viewport zoom, navigation and toolbars reflow; overlays remain operable; long content scrolls in a controlled region. Do not fix card heights where translated or enlarged text can overflow.
5. **Keep user work.** Search, sorting, selection, expanded state, and scroll position persist through ordinary detail/back navigation when appropriate. Loading, failures, and validation must not clear entered values.
6. **Separate loading from emptiness.** Unknown data, zero results, unavailable data, and confirmed errors have distinct states. Never render `0` as a fallback for an unknown measurement.
7. **Use one overlay stack.** Suggested relative layers: base content 0, sticky content 10, popover/menu 30, modal backdrop 40, modal 50, nested modal/popover 60, toast 70, tooltip 80. These are extension defaults; centralize them and account for native top-layer elements.
8. **Do not encode meaning in color alone.** Add labels/icons/patterns; verify contrast for every text/surface pairing, especially muted captions, green values, and colored chips. Focus and selection remain identifiable in high-contrast modes.
9. **Honor system preferences.** Reduced motion disables nonessential animation. Forced-color/high-contrast modes retain outlines and labels. A dark theme is a separate design effort; do not create one by mechanically inverting this light reference.
10. **Keep the visual grammar stable.** Reuse the same pill proportions, round icon controls, neutral inset rows, restrained borders, black selected states, semantic signal discs, and large card radii across all modules. A custom component should look related before its label is read.
