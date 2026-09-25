# Notification center

**Read when:** Bell-adjacent notification popover, unread behavior or notification sheet.  
**Requires:** [Design tokens](../foundations/tokens.md), [Shared interaction contract](../foundations/interaction.md)  
**Related (optional; do not automatically load):** [Menus, popovers and tooltips](menus.md), [Badges, status and avatars](identity.md)  
**Load only for this variant:** Floating notification popover → [Menus, popovers and tooltips](menus.md); Modal notification sheet → [Dialogs, drawers and sheets](dialogs.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

**Notification center:** profile/bell-adjacent popover width 400px, white 24px radius, header with title/unread count and “Mark all read” when supported. Reuse the shared activity well with 64–72px rows; unread items have a black 6px dot plus explicit unread state, not an unexplained new bright color. Provide All/Unread local pills and a full-page link if the list becomes long. Opening a notification and marking it read are separate documented behaviors. On mobile, use a full-width sheet.
