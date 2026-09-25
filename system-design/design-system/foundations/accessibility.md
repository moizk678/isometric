# Accessibility, contrast and internationalization

**Read when:** Auditing contrast/keyboard behavior, localization, RTL, zoom or time-zone/data interpretation.  
**Requires:** [Design tokens](tokens.md), [Shared interaction contract](interaction.md)  
**Related (optional; do not automatically load):** None.  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Contrast: fidelity versus usable product

The image deliberately uses light muted text and very subtle boundaries. Preserve that as evidence; do not confuse it with verified accessibility. The table below computes approximate contrast from this collection's sRGB tokens, not from every antialiased source glyph.

| Pair | Approximate contrast | Product rule |
|---|---:|---|
| Reference muted `#8B8B85` on inset `#F2F1ED` | 3.03:1 | Use the darker product muted token for ordinary small text |
| Product muted `#686963` on inset `#F2F1ED` | 4.90:1 | Default small metadata/placeholder color; verify final rendered pairing |
| Secondary `#50514D` on inset `#F2F1ED` | 7.08:1 | Normal secondary text |
| Feature support `#C8E8D4` on deep green `#2F6A4A` | 4.86:1 | Suitable starting point for product hero labels |
| Reference chart axis `#809080` on deep green | 1.90:1 | Product mode replaces with `--ink-on-feature` |
| Positive text `#167342` on inset | 5.21:1 | Use dark semantic ink for small trend text |
| Danger text `#B33624` on inset | 5.35:1 | Use dark semantic ink for errors/adverse deltas |
| Source-like border `#D2D2D2` on white | 1.51:1 | Decorative or supplementary only; don't rely on this as the only field boundary |
| Strong boundary `#777970` on inset | 3.91:1 | Use when the control shape must be independently identifiable |

**Design targets:** at least 4.5:1 for ordinary text,3:1 for large text and essential control/focus graphics; measure against the actual background. These are acceptance targets for the future implementation, **not a claim this screenshot or an unbuilt product passes a formal audit**. Use text/icons/patterns in addition to color. Product mode uses `--stroke-control-strong` for form boundaries when the neutral surface change alone does not provide the necessary distinction. Source-reproduction buttons may retain their measured pale border.

## Keyboard, focus and semantic requirements

- Use landmarks and meaningful heading order; one page heading. A label is not a placeholder, a pill is not inherently a button, and a visual table is not inherently a spreadsheet grid.
- Native semantic elements are preferred beneath custom styling. Use fully implemented composite patterns for custom comboboxes, listboxes, calendars, trees and menus. Styling alone does not supply keyboard or screen-reader behavior.
- Tab order follows logical content order. Only modal dialogs/sheets trap focus. Composite option/day lists use one managed focus stop plus documented arrows rather than hundreds of Tab stops.
- Escape closes the uppermost dismissible overlay; draft state cancels according to its contract. Returning focus is explicit. If the opener was deleted, focus a surviving adjacent action or the section heading.
- Pressing Tab in a menu closes it and proceeds logically; it must not strand focus in a portal. Editable combobox inputs keep ordinary text navigation shortcuts. Link and button behavior stay distinct.
- Add nonvisual names to icon-only actions, repeated row controls, and meters. “Review case, MRI · Lumbar Spine, James Carter” distinguishes a row action; an implementation should substitute the user's actual entity vocabulary.
- Announce async changes through an appropriately quiet status region. Do not announce all six activity entries whenever one new event arrives. Errors requiring immediate attention are exceptional.
- Forced-colors mode preserves outlines and selection with system colors; SVG icons use current color where appropriate. Transparent borders can become visible in that mode. Do not remove native outlines without providing an equivalent.
- Do not hide essential hints behind hover. Tooltips must be dismissible and remain available while the pointer is over the trigger or tooltip; moving directly between them should not instantly dismiss them. Interactive help belongs in a popover, not a tooltip.
- Respect reduced motion, localization, and text resizing. Screen-reader verification is a required implementation acceptance task, not something established by this markdown file.

## Internationalization and data integrity

Source is English LTR. New software should use logical start/end layout, locale-aware dates/numbers, pluralization, and enough room for at least 30% label expansion. Preserve meaningful medical/product identifiers and mixed-direction strings without reordering their characters. Mirror navigational chevrons for RTL where appropriate; do not mirror logos, charts' numeric truth, or non-directional status symbols blindly.

Calendar date and instant/timestamp are different data types. Display time zones when they affect interpretation. “Today,” “last 7 days,” and “week” require explicit boundaries, inclusion rules, and locale/week-start configuration. The source's Monday, Sep 21 does not establish the application's timezone or year. Never render unknown/failed metrics as 0. Use an em dash with an “Unavailable” explanation where appropriate, reserving 0 for a known zero.
