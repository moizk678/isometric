# Screenshot table and activity feed

**Read when:** Matching the source table/feed, exact sample records, columns, segmented meters and timestamps.  
**Requires:** [Source, evidence and measurement conventions](evidence.md)  
**Related (optional; do not automatically load):** None.  
**Evidence:** Observed [O], measured [M], and labeled interpretation [I]. Domain content is reference-only.  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Panel and header

- White panel at `116,703,1142,534`, radius≈36.
- **Attention required**, x≈138/y≈726, ≈22px medium.
- Subtitle: **Sorted by procedure date, then approval odds**, x≈138/y≈756, ≈16px secondary.
- Orange urgency badge near `1025,733,162,27`: small black dot followed by **8 cases need action**, black ≈13–14px text.
- Pale 44px northeast-arrow utility circle at ≈1197/724.
- Table headings around y≈800: **Case**, **Blocking issue**, **Payer**, **Approval odds**, **Due**. The last action column has no visible heading.
- There are **five visible rows**, even though the badge says eight cases. No visible footer, pagination, scrollbar, selection checkbox, sort chevron, or row menu. Do not claim these are present.

## Row geometry and columns

Rows are separate warm off-white rounded bands, not a contiguous grid. Each is ≈1124px wide and 70–72px tall, at x≈125. Top positions ≈825,907,989,1071,1153. White gutters between rows are ≈11–12px. The last row ends near y≈1223 with ≈14px white parent margin.

| Column / object | Approximate x span | Alignment / detail |
|---|---|---|
| Entity icon | `138–182` | 44px white disk centered vertically |
| Case title and metadata | `200–440` | Two lines; title≈16px black, metadata≈14px muted |
| Issue icon | `461–488` | 26px orange disk; black warning triangle |
| Issue text | `497–724` | ≈14px secondary; single line in reference |
| Payer logo capsule | begins≈736 | White pill, ≈36px tall; width varies ≈76–120px |
| Probability number | `881–933` | ≈26px black; `%` same size here |
| Probability segments | `943–1008` | 10 vertical pills, ≈4px wide ×16px tall, gap≈2.5px |
| Due date | `1036–1090` | ≈14px secondary, centered vertically |
| Row CTA | `1112–1236` | White pill ≈124×40; gray 1px border; `Review case` |

Entity disks are distinct from status disks. The issue icon repeats for every row and does not vary by procedure. Buttons do not use drop shadows. Some payer artwork has tiny words/symbols inside it; preserve the artwork's aspect ratio and padding if supplied.

## Complete visible records

| Row | Case | Secondary line | Entity icon | Blocking issue | Payer artwork | Odds / segments | Due |
|---|---|---|---|---|---|---|---|
| 1 | MRI · Lumbar Spine | James Carter · PA-48291 | X-ray/spine plate | Missing imaging report | United Healthcare, dark blue stacked mark | 78%; 8 green, 2 gray | Sep 24 |
| 2 | Knee Arthroscopy | Maria Gonzalez · PA-48277 | Medical bag with plus | Missing clinical notes | aetna, purple heart-like mark + wordmark | 61%; 6 yellow, 4 gray | Sep 25 |
| 3 | Spinal Fusion · L 4 to L 5 | Thomas Reed · PA-48102 | Heart outline with plus | Peer to peer review requested | United Healthcare | 47%; 5 orange, 5 gray | Sep 25 |
| 4 | CT · Abdomen and Pelvis | Emma Wilson · PA-48240 | X-ray/spine plate | Payer requested documents | The Cigna Group, green tree + blue wordmark | 66%; 7 yellow, 3 gray | Sep 26 |
| 5 | Sleep Study · In lab | David Kim · PA-48263 | Stethoscope | Treatment history missing | Anthem BlueCross BlueShield, blue wordmark + emblems | 54%; 5 orange, 5 gray | Sep 28 |

Every row action is **Review case**. The ten-segment fill counts visually fit rounding `percent / 10`, but the underlying rule is **[U]**. The orange/yellow/green thresholds are also **[U]**: the image establishes examples, not general cutoffs. For product extensions, define thresholds from domain requirements and preserve the exact percentage beside the coarse indicator. Do not equate “green” with guaranteed approval.

## Table UX interpretation

**[I]** The structure prioritizes “what,” “what blocks it,” “who owns payment,” “likelihood,” “when,” and “next action.” This is an adaptable operational row pattern. The sorting subtitle explains ordering without visible controls. **[E]** In a different product, map these slots to entity, blocker/status, owner/organization, progress or confidence, deadline, and action. Preserve column hierarchy; do not force irrelevant probability or payer fields into the new domain.

## Activity anatomy

- White outer card at ≈`1275,703,399,534`, ≈36px radius.
- **Recent activity** heading at x≈1297/y≈734; pale 44px ellipsis circle at ≈1612/721.
- A **single shared warm inset well**, `1284,778,382,450`, radius≈28. Do not render each activity entry as its own separate card.
- Six entries stacked at roughly 67–68px intervals. First icon begins x≈1302/y≈798. Icon disks are≈36px.
- Primary text starts x≈1351, ≈14–15px black, medium; secondary line≈14px muted directly beneath.
- Timestamps align right at x≈1646, ≈13px muted; positioned roughly between the two text baselines.
- Thin gray separators at y≈850,918,985,1052,1119; inset to the content edges, not full-bleed; no separator after the final entry.
- Bottom of the inset retains blank space after the last item. No scrolling affordance, “view all” link, or unread indicators are visible.

## Complete activity content

| Disk and icon | Primary line | Secondary line as visible | Time |
|---|---|---|---|
| Green / check | Authorization approved | MRI · Linda Park | 9:12 AM |
| Orange / warning triangle | More documentation requested | CT Scan · Emma Wilson | 8:47 AM |
| Coral / X | Authorization denied | Physical Therapy · Robert Smith | 8:05 AM |
| Lavender / two sparkle shapes | AI review completed | Knee Arthroscopy · Maria Gonzal... | Yesterday |
| Green / check | Appeal overturned | Epidural Injection · Noah Davis | Yesterday |
| Yellow / hourglass | Submitted to payer portal | PET Scan · Olivia Brown | Yesterday |

The fourth secondary line is visibly truncated. Preserve truncation behavior, not the literal truncated name, when displaying live data. The complete unseen string is **[U]**; other visible records do not prove which person this item refers to.
