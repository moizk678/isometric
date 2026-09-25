# Full component coverage

**Read when:** Checking completeness or finding whether an uncommon component is defined.  
**Requires:** None beyond the entry point.  
**Related (optional; do not automatically load):** None.  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Coverage index

| Family | Defined components | Owning modules |
|---|---|---|
| Source composition | Frame, app header, logo, primary nav, search, profile, scope selector, primary action, feature card, micro-chart, fact strip, KPI group, operational table, activity feed | [Screenshot layout and header](../reference/layout-header.md), [Screenshot feature, chart and metrics](../reference/summary-panels.md), [Screenshot table and activity feed](../reference/table-feed.md), [Screenshot iconography and assets](../reference/icons-assets.md) |
| Inputs | Text, email, URL, telephone, textarea, search, numeric, currency, percent, stepper, password, OTP, duration, structured segments | [Text, numeric, password and structured inputs](../components/text-inputs.md), [Search and command palette](../components/search.md) |
| Choice | Select-only, listbox, editable/remote combobox, multi-select, tag input, checkbox, radio, switch, choice card, slider/range, rating, color picker, transfer lists | [Selects, comboboxes and tag entry](../components/selects.md), [Choice, range and color controls](../components/choice-controls.md) |
| Date/time | Single date, date range, calendar grid, month picker, year picker, time, date-time, time range, presets, mobile sheet | [Date and time pickers](../components/date-time.md) |
| Navigation | Top nav, sidebar/rail, local tabs, segmented control, breadcrumbs, pagination, stepper, tree explorer | [Navigation and trees](../components/navigation.md) |
| Actions/identity | Primary/secondary/quiet/danger/icon/split/toggle buttons, links, badges, chips, status disks, counts, avatars/groups/presence, organization capsules | [Buttons, links and action groups](../components/buttons.md), [Badges, status and avatars](../components/identity.md) |
| Containers/data | Panels, metric tiles, lists, tables, sorting/filtering, facets, grouping, expansion, tree tables, bulk selection, key-value blocks, master-detail, split panes, accordions | [Panels, lists and detail layouts](../components/panels.md), [Tables, filters and bulk actions](../components/tables.md) |
| Overlays | Menus/submenus/context menus, check/radio menu items, popovers, tooltips, dialogs, confirmation, drawers, sheets, command palette | [Menus, popovers and tooltips](../components/menus.md), [Dialogs, drawers and sheets](../components/dialogs.md), [Search and command palette](../components/search.md) |
| Feedback | Toasts, inline banners, validation summary, empty/error/no-access states, skeleton, spinner, linear and segmented progress, optimistic/pending state | [Feedback, loading and progress](../components/feedback.md), [Form layout and validation](../components/forms.md) |
| Work views | Schedule/calendar, timeline, kanban, checklist, Gantt, notification center, conversations/comments, reorderable lists | [Calendars, schedules, boards and timelines](../components/work-views.md), [Notification center](../components/notifications.md), [Messages and comments](../components/messaging.md) |
| Media/content | Upload/dropzone, attachments, file list/grid, image/video viewer, lightbox, rich text, markdown, structured/code editor, code block, article content | [Uploads, attachments and file views](../components/uploads-files.md), [Image and video viewers](../components/media.md), [Rich text, markdown, code and code blocks](../components/editors.md), [Visual principles and domain translation](translation.md) |
| Visualization | Bar, line/area, stacked, donut, sparkline, heatmap, scatter/bubble/histogram, map, data tooltip, text/table alternatives | [Charts, analytics and maps](../components/charts-maps.md) |

This modular collection is the canonical specification; each topic has one owning file. The reference image is evidence; newly specified components inherit this visual language and the explicit interaction contracts. Unspecified domain behavior must come from the actual product brief, not from guesses about the screenshot.
