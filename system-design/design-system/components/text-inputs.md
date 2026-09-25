# Text, numeric, password and structured inputs

**Read when:** Text, textarea, email, URL, telephone, number, currency, percentage, stepper, password, OTP or duration entry.  
**Requires:** [Shared field contract](field-basics.md)  
**Related (optional; do not automatically load):** [Form layout and validation](forms.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Text, email, URL, telephone, and multiline inputs [E]

- **Text input:** follow the shared 44px contract. A filled value replaces placeholder in the same position. Optional prefix/suffix text uses `--ink-secondary`, does not become part of the user-editable value, and is included in the accessible description when semantically necessary. Error icons and clear buttons have distinct slots; do not overlap.
- **Email / URL / telephone:** use suitable input type, input mode, autocomplete metadata, and example-format guidance. Preserve user input while editing; normalize only when safe and explain any substantive transformation. Do not force case or remove valid international characters without domain rules.
- **Multiline textarea:** minimum height 120px, radius 16px, padding 14px 16px, 14px/22px text; start with four useful text lines. Resize vertically, minimum 120px, maximum visible editor height 320px before internal scrolling. Optional auto-grow has the same cap. Counter sits outside at the lower right; show remaining characters near the limit. Do not truncate saved text.
- **Clear button:** appears only for a nonempty editable field when clearing is useful; 16px `×` centered in a 32px desktop slot, 44px touch target. `Clear [field label]` is the accessible name. Clearing keeps input focus and triggers the same validation policy as ordinary editing.
- **Prefix / suffix chips:** 24px high neutral pill inside a field, radius 12px, 11px text; only use for an inseparable unit such as currency or domain suffix. If editable independently, give it a separate accessible control and enough room to operate.

## Number, currency, percentage, and quantity [E]

- Number fields use tabular digits, 14px/20px type, and the common capsule shape. Align right within compact data-entry tables; align left in ordinary forms. Declare decimal precision, min/max, and unit in the label/helper. Preserve incomplete intermediate values such as `-` or `1.` while the user is editing.
- Currency: leading currency symbol in `--ink-secondary`, optional currency code as a separate suffix; distinguish currencies sharing symbols. Apply grouping separators on blur when appropriate; do not move the caret unpredictably on each keystroke. Store numeric amount and currency separately. Negative amounts use a minus sign; semantic red only when the product meaning is loss/error.
- Percentage: trailing `%`; helper specifies whether the entered value is 0–100 or another range. Do not turn `12` into `1200%` through implicit conversion.
- Stepper: 44px high outer capsule containing **44px decrement target**, value area at least 48px, and **44px increment target**; neutral 1px border; 16px icons. Disable decrement/increment at bounds and announce the current value with units. Keyboard Up/Down steps only when the number control is focused. Do not capture the page's mouse wheel merely because the pointer passes over the field.
- Invalid numeric input remains visible and editable with a precise message; never silently replace it with zero. For precision-sensitive amounts, use a data model that avoids unintended binary rounding.

## Password, one-time code, and sensitive entry [E]

- Password input follows the default field; trailing eye button switches reveal state, has a stable 44px target, and accessible name `Show password` / `Hide password`. Toggling never clears input or moves the caret. Allow paste, autofill, and password-manager integration.
- Optional strength guidance sits below: neutral 4px segmented meter, text assessment, and a concise list of unmet requirements. It is guidance, not a substitute for an error message. Do not display success merely because minimum length is reached.
- One-time code: visually segmented **44px × 48px cells**, **12px radius**, **8px gap**, 20px centered tabular digits. Prefer one underlying labeled input styled as slots, with paste/autofill and a single predictable focus path. For six digits, width is 304px; fit narrower containers by reducing gap to 4px before cell width. Invalid state marks the group and provides one message. Resend has a real cooldown label and does not reset typed data without a reason. Never create six confusing screen-reader fields without clear position labels.

## Duration and segmented numeric entry [E]

Duration is distinct from a time of day: use labeled hour/minute/second segments as appropriate inside a 44px control or a small grouped row. Segments are at least 56px wide with tabular digits, units shown persistently, and a group label such as `Duration`. Set whether values normalize on blur (e.g. 90 minutes → 1 hour 30 minutes) and display the normalized result before submission. Do not apply timezone or AM/PM controls. Arrow steps, bounds, invalid values, and direct typing follow the number-field rules. Related segmented entries such as dimensions use explicit per-segment labels and a visible shared unit; an unlabeled sequence of small boxes is insufficient.
