# Messages and comments

**Read when:** Conversation threads, chat bubbles, comments, replies, reactions or composer layout.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** [Text, numeric, password and structured inputs](text-inputs.md), [Uploads, attachments and file views](uploads-files.md)  
**Load only for this variant:** Editable message/comment composer → [Text, numeric, password and structured inputs](text-inputs.md); Attachments in the composer → [Uploads, attachments and file views](uploads-files.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

**Messages/comments:** white 32px-radius conversation panel; rows use 32px avatars,14px author text,12px muted timestamp, and 14/22px body text. Comments use normal document alignment, not arbitrary colored chat bubbles. When true two-party chat needs bubbles, incoming is inset-neutral; own message is black/white only for short messages, while long rich content stays white with a clear author label. Bubble radius 20px, padding 12px 16px, max 70% desktop/85% mobile width. Composer uses the multiline field contract, named 44px send/attach actions, clear draft state, and explicit send shortcut; Enter behavior must distinguish multiline editing from sending. Thread replies indent 24px desktop/12px mobile with a 1px neutral guide; reactions are 24px neutral pills with accessible selected state. Keep edit/delete/reply available on keyboard and touch.
