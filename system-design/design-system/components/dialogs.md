# Dialogs, drawers and sheets

**Read when:** Modal/confirmation flows, drawers, bottom sheets, nested overlays and dismissal/focus behavior.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** [Form layout and validation](forms.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Dialogs, confirmation flows, drawers, and bottom sheets [E]

| Surface | Geometry | Content rules |
|---|---|---|
| Small confirmation dialog | 400 px width; max viewport width minus 32 px; 24 px radius; 24 px padding | 20 px / 28 px title, 14 px body, 16 px title/body gap, 24 px body/actions gap |
| Standard dialog | 560 px width; max viewport width minus 32 px; 24 px radius; 24 px padding | Short forms, focused decisions, limited settings |
| Large dialog | 720–880 px width only when needed; same radius and padding; maximum height `viewport − 48px` | Complex but bounded task; scroll body rather than hiding header/footer |
| Side drawer | 440 px default width; 560 px for dense record detail; max 90vw on desktop; white; 24 px leading corners if inset | Header 72 px minimum; body 24 px padding; footer 72 px minimum when actions persist |
| Bottom sheet | viewport width; top corners 24 px; bottom corners follow viewport; body 16–24 px padding; max height 90dvh | Touch-friendly version of a menu, picker, or short detail task |

- Backdrop: `--overlay-scrim`, near-black at **32% opacity**. A dialog sits on white with `--shadow-dialog`. Do not heavily blur or recolor the entire product. Backdrop belongs to the overlay stack, not a card decoration.
- Use an 18–20 px medium heading and a close icon button with a 44 px target at the upper logical end. The text and close control must not overlap. Long titles wrap and increase header height.
- Dialog body scrolls when necessary; footer actions remain visible with a white background and a 1 px top divider only when the scroll region needs separation. Use **12 px** between actions.
- A confirmation explains the concrete object, consequence, and reversibility in one or two short sentences. Primary action names the consequence (`Delete 8 records`, `Discard changes`), not a vague `OK`.
- Initial focus goes to the first meaningful input for an ordinary form, the least destructive action for a risky confirmation, or the heading when reading context is necessary. Do not focus a destructive submit button by default.
- Constrain focus within a modal, mark the background inert, lock background scrolling without horizontal layout jump, support Escape where cancellation is allowed, and restore focus to the opening control or a logical surviving neighbor.
- Backdrop click may dismiss an informational dialog; a dirty form or destructive workflow requires an explicit close/discard decision. Do not silently save on close unless the product clearly communicates autosave.
- Drawers use the same form and list primitives. Keep the title/header fixed and use one main scroll container; avoid several competing nested scroll regions. A drawer that exposes a complete page should offer a navigation action to its full detail view.
- Bottom sheets have an optional **32 × 4 px** muted drag handle, centered with 8 px top margin. The handle is supplemental; a visible close/back button remains available. Dragging is never the only dismissal method.
- Below **640 px viewport width**, standard dialogs become near-full-width panels with 16 px safe margins or full-height task sheets for substantial forms. Keep 44 px actions, respect safe-area insets, and scroll the focused field above the on-screen keyboard.
- For nested confirmation over a drawer, keep one modal backdrop and visually subordinate the drawer. Return focus to the exact action after canceling. Avoid nesting more than two interactive modal layers.
