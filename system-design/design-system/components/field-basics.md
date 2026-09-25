# Shared field contract

**Read when:** Implementing any form field or input-like trigger.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** [Accessibility, contrast and internationalization](../foundations/accessibility.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

These form-component rules are **designed extensions**, not a control observed in the source image. The intention is to extend the source's soft capsule geometry, warm inset surfaces, restrained borders, black selection, and semantic color discs to arbitrary software. Use the canonical tokens in [Design tokens](../foundations/tokens.md); do not hard-code alternate shades in these components.

## Shared field contract [E]

| Property | Deterministic specification |
|---|---|
| Field anatomy | Persistent label → optional description → control → helper or error message. Optional supporting action aligns to label baseline. Required status is declared in text or an explained symbol; never by color alone. |
| Default control | Height 44px; radius 22px; horizontal padding 16px; gap 8px. Filled `--surface-inset`; text `--ink-primary`; 1px `--stroke-control` border. Controls on inset surfaces use `--surface-panel` to preserve separation. |
| Sizes | Compact 36px / radius 18px / horizontal padding 12px, only for dense desktop utilities. Default 44px / 22px / 16px. Large 52px / 26px / 20px. Do not mix heights within a form row. Touch layouts use default or large. |
| Type | Label 13px / 18px, medium. Value and placeholder 14px / 20px, regular. Helper/error 12px / 18px. Value uses `--ink-primary`; descriptive text `--ink-secondary`; placeholder `--ink-muted`. Never use placeholder as the sole label. |
| Icons | 18px, 1.5px stroke; trailing disclosure/clear/status icons 16–18px. Allocate a 20px icon slot. Search and password controls retain the same text baseline as plain inputs. |
| Field spacing | Label-to-description 4px; label/description-to-control 8px; control-to-helper 6px. Fields within a group: 20px vertical. Related inline controls: 12px horizontal. Group-to-group: 32px. |
| Width | Fill assigned layout track; short fields may use explicit widths, e.g. 96px quantity, 144px postal code, 180px date. Never size a required field narrower than its expected example value. |
| Focus | Keyboard focus uses 2px `--focus-ring` outside the control with 3px offset. Keep the ring fully visible and unclipped. Focus is separate from selected/value/error states; an invalid focused control shows both error border and focus ring. |
| Hover | Border advances to `--ink-muted`; surface stays within neutral palette. Do not recolor the whole form green. |
| Read-only | Value retains normal contrast; control is non-editable, lacks edit-affordance hover, and carries accessible read-only semantics. It can remain focusable for copying or inspection. |
| Disabled | `--surface-inset`, `--ink-muted`, 1px `--stroke-control`; remove hover and interactive shadow. Disable the actual control, not only its appearance. Preserve legibility; do not reduce the entire field/label to low-opacity gray. Add explanation when inability to proceed is otherwise unclear. |
| Invalid | 1px `--ink-danger` border, error text with 14px warning icon below. Preserve entered data. One field-level message names the problem and how to repair it. Do not encode the problem only in a red outline. |
| Loading | Keep dimensions and label stable. Show an 18px spinner in a trailing reserved slot; disable only conflicting actions. Announce asynchronous status without moving focus. |
| Success | Optional 16px positive icon after confirmed validation. Do not show success decoration on every untouched field or replace its value. |

In product mode, replace a pale field boundary with `--stroke-control-strong` wherever the fill difference does not make the control identifiable; [Accessibility, contrast and internationalization](../foundations/accessibility.md) defines the contrast target. Preserve the lighter source border only for reference reproduction or nonessential separation.

Use real form semantics underneath custom visuals. Label each control programmatically, associate descriptions/errors, preserve logical tab order, and retain native editing, selection, clipboard, and autofill behaviors. Icons that activate an action are real buttons with names. Decorative icons are hidden from assistive technology. An entire pill-shaped input is the click target for focusing; its trailing action must not block selecting the text.
