# Date and time pickers

**Read when:** Custom date, date-range, month/year, time, date-time and narrow-screen picker behavior.  
**Requires:** [Shared field contract](field-basics.md)  
**Related (optional; do not automatically load):** [Dialogs, drawers and sheets](dialogs.md), [Calendars, schedules, boards and timelines](work-views.md)  
**Load only for this variant:** Modal picker or mobile bottom sheet → [Dialogs, drawers and sheets](dialogs.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Custom date picker [E]

### Date trigger, formatting, and popup geometry [E]

- Trigger is a labeled 44px capsule field; value left, 18px calendar icon right. Empty state uses an example appropriate to locale, e.g. `Sep 24, 2026`; do not use an ambiguous numeric placeholder. Allow keyboard entry where feasible, with an explicit accepted-format helper and strict parse feedback. Expose an independently named `Choose date` button when the text portion is editable.
- Use one unambiguous display format per locale. Store calendar dates separately from timestamps; do not let timezone conversion move an all-day date to an adjacent day. Show timezone when selecting a time or comparing remote locations.
- Desktop single-month popup: **364px wide**, radius **24px**, padding **16px**, `--surface-panel`, 1px neutral boundary, overlay elevation, anchor gap **8px**. It has a 332px inner width; paint the 1px boundary inside the surface without consuming this layout width. Header height 40px; gap below 12px; weekday row height 24px; day grid has **7 × 44px columns** and **4px gaps**. Each day is a 44px square hit target; its painted circular state is 36px diameter centered within it. Keep six week rows to avoid popup-height jumps while navigating months.
- Header contains previous arrow, centered month/year label, next arrow. Arrow buttons are 40px desktop targets containing 16px icons and gain inset-neutral circular hover fill. On touch use 44px targets. The month/year label is a real button opening the month/year views, not decorative text; use 14px/20px medium type.
- Weekday labels: 11px/16px, `--ink-secondary`, centered. Day numbers: 13px/18px. Optional week numbers form a separately labeled narrow column only for products that use them; widen the calendar instead of squeezing day targets.
- Popup footer: 1px divider; 12px top margin and padding; left tertiary `Clear` when a value exists; right tertiary `Today` if today is selectable. Immediate single-date selection closes the popup and returns focus to its trigger. If extra settings require confirmation, use `Cancel` and black `Apply`; never mix immediate commit with an unlabeled draft state.

### Calendar visual states [E]

| Day state | Appearance | Interaction |
|---|---|---|
| Default | Transparent; `--ink-primary` numeral. | Selectable. |
| Hover | 36px inset-neutral circle. | Cursor/pointer affordance; no value commit. |
| Keyboard focus | Focus ring around the day target/state with offset that does not overlap neighboring numerals. | Focus is visible independently of selection/today. |
| Today, unselected | 36px circle with 1px `--ink-primary` outline; numeral medium weight. | Accessible label includes “today.” |
| Selected | 36px near-black circle; white numeral. | Accessible selected state; label includes full date. |
| Selected today | Black selected circle plus small contrasting 3px dot beneath numeral or accessible today text; do not add a green circle. | Expose both meanings. |
| Adjacent-month date | `--ink-muted`; retain clear legibility. | If selectable, selecting changes month and value. Otherwise use disabled semantics; choose one behavior for the product. Default: selectable. |
| Disabled / out of bounds | Muted numeral, no hover; optional explanatory tooltip for a domain-specific restriction. | Never selectable; min/max/availability explained before the grid when meaningful. |
| Unavailable with existing booking | Disabled day plus small neutral/danger marker only when the booking meaning is relevant. | Text alternative states unavailability; do not depend on the marker. |
| Range interior | Warm neutral horizontal band; primary numeral; no individual filled circle. | Announced as part of selected range. |
| Range start / end | Black circle with white number over the band; single-day range is one black circle. | Accessible full date plus start/end role. |
| Range draft preview | Lighter neutral band from start to hovered/keyboard-active end; endpoints distinct. | Preview only; never persist until committed. |

The range band connects day cells across horizontal gaps; start/end bands stop at the center of their endpoint circle. At week boundaries, terminate the band at the row edge and continue on the next row. Do not use the source's risk-green hero fill to indicate routine selected dates.

### Month, year, keyboard, and focus behavior [E]

- The calendar is a grid in a labeled dialog/popover; one day participates in roving tab focus. On open, focus the selected day, otherwise today if allowed, otherwise the nearest allowed day. Announce the visible month/year without repeatedly reading the entire grid.
- Left/Right move one day; Up/Down move one week; Home/End move to the first/last day of the displayed locale week. Page Up/Page Down move one month preserving the day when possible. Shift+Page Up/Page Down move one year. Enter/Space selects the focused enabled day. Escape cancels uncommitted changes, closes, and returns focus to the trigger. Preserve document navigation keys outside the calendar.
- Day labels include full weekday, month, day, year and any relevant selected/today/unavailable role. Week start and weekday labels follow locale. In right-to-left layouts, mirror layout and apply a consistent documented arrow-navigation convention.
- Month view replaces the day grid with 12 month buttons in **3 columns × 4 rows**; each minimum 44px high, 12px radius, gap 8px. The chosen month has black fill/white text; current month has neutral outline; disabled months outside date bounds are unavailable. Selecting a month returns to the day grid.
- Year view is a paged 12-year grid, **3 columns × 4 rows**, with the same cell sizes/states. Header announces the inclusive year range; arrows page by 12 years. Provide a direct year text entry for dates far from today, such as birthdays. Do not force dozens of next-month clicks. Clamp date when changing from a longer to shorter month and expose the resulting date before committing.
- Popup focus strategy is explicit: anchored desktop picker may be a nonmodal dialog with managed return focus; a mobile sheet is modal and traps focus within itself. The rest of the page is inert only for a modal sheet/dialog. Closing via outside pointer cancels draft values; if immediate selection already committed, closing does not reverse it.

### Date range picker [E]

- Trigger is one 44px capsule displaying `Start date – End date`, with calendar icon; optional separate start/end fields share one group label and a clear error location. Desktop picker uses two synchronized adjacent months: **712px width = 16 + 332 + 16 + 332 + 16**; 24px radius; 16px padding; same 44px day targets and 4px grid gaps. Show the previous/next navigation only on the outer edges to avoid contradictory month changes.
- First selection sets draft start; second sets draft end. If the second date precedes the first, reorder the endpoints predictably; never silently discard a selection. Moving the pointer or keyboard previews the prospective range. A third selection after a completed draft begins a new range.
- Use a persistent footer with summary (`Sep 24–30, 2026 · 7 days`) plus `Cancel` and black `Apply`. Apply is disabled until both endpoints form an allowed range. Draft selection remains local until Apply. Cancel/Escape restores previously committed dates. Reopening shows the committed range.
- Presets, if useful, occupy a wrapping top row that preserves the 712px width: `Today`, `Last 7 days`, `This month`, `Custom`. Selected preset is black with white text. Preset selection updates the draft; Apply still commits. Define whether ranges include today and whether dates are inclusive; default calendar-date ranges include both endpoints. Never rely on label alone for domain-specific reporting windows.
- Ranges must respect min/max dates and unavailable-date rules. If a range cannot cross an unavailable date, explain it and prevent Apply. If it can, differentiate omitted/unavailable days in text. Maximum duration rules show before submission.
- Below 760px available overlay width, show one month with start/end summary and navigation rather than shrinking two calendars. On touch, use a bottom sheet and clear start/end labels; hover preview is replaced by the focused/tapped endpoint state.

### Time and date-time picker [E]

- A time field follows the 44px capsule contract, has an 18px clock icon, and displays locale-appropriate 12/24-hour format. State timezone adjacent to the field or within a grouped header. The timezone is selectable only when the product needs it.
- Custom time popup uses hour and minute option columns with **44px rows**, **12px row radii**, 8px padding, selected black/white row, neutral hover, and visible column labels. Minutes default to 5-minute increments only where the workflow allows; otherwise permit every minute and typed entry. A 12-hour mode includes an AM/PM black-active segmented control, 36px high.
- Offer full text entry and list navigation; scrolling is not the only way to set a time. Up/Down step the focused segment; Home/End go to valid segment bounds; numeric typing replaces the segment; Left/Right moves between editable segments without intercepting standard text selection unnecessarily.
- Date-time uses calendar above, divider, then time controls in the same panel; a footer Apply commits both together. Validate nonexistent or duplicated local times around clock changes with an explicit disambiguation choice rather than silently changing the time.
- Time range names start and end; an end earlier than start is invalid unless overnight ranges are supported, in which case show `Ends next day`. Minimum duration and availability rules appear as helper text.

### Date picker on small screens [E]

At less than 600px viewport width, open as a bottom sheet with 24px top corner radii, white surface, 16px standard padding, named close action, header label, committed/draft summary, and safe-area bottom padding. Use full available width and seven equal day columns with **minimum 44px touch targets**. At 340–363px viewport width retain 16px side padding and reduce the column gap from 4px as needed: `gap = max(0, min(4px, (innerWidth - 308px) / 6))`. At 320–339px reduce only calendar horizontal padding to 6px and remove intercolumn gaps, retaining 44px targets. Below 320px, provide the labeled direct-entry alternative instead of compressing date targets. The sheet is at most 90dvh and scrolls internally. Keep the footer reachable and never obscure it behind the keyboard. Date ranges show one month at a time with explicit start/end status. Swipe navigation may supplement labeled previous/next buttons but must not replace them.
