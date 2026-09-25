# Rich text, markdown, code and code blocks

**Read when:** Editing rich/structured content, formatting toolbars, markdown preview or read-only code presentation.  
**Requires:** [Shared field contract](field-basics.md)  
**Related (optional; do not automatically load):** [Menus, popovers and tooltips](menus.md)  
**Evidence:** [E] designed extension unless marked otherwise  
**Entry point:** [design.md](../../design.md)

Required dependencies inherit their own prerequisites; read each file once while it remains available and unchanged. Optional links are navigation, not instructions to load everything.

## Rich text, markdown, and code-style editors [E]

- Rich-text editor: outer white/inset-contrast surface, 1px control boundary, 16px radius; minimum height 200px. Toolbar has 8px padding, a 1px bottom separator, 4px gaps, and 36px desktop icon buttons with 12px radius; use 44px targets on touch. Active formatting button is black with white icon, hover is neutral inset. Group separators are 1px strokes with 8px horizontal space. Buttons have explicit names and pressed states.
- Editing area: 16px padding, 14px/22px text, persistent field label above. Placeholder disappears on input; empty paragraphs are still editable. Toolbar actions preserve text selection and return focus to the editor. Common formatting shortcuts operate as expected. Use visible controls for links, lists, headings, undo and redo; hide uncommon tools in an accessible overflow menu when width is insufficient.
- Link insertion is a small form with labeled display-text and URL fields, 16px content padding, and explicit Apply/Cancel. Existing links expose edit/remove actions without navigating away during editing. Errors identify malformed links while retaining the selection and input.
- Markdown editor: labeled `Write`/`Preview` segmented control, black active segment, 36px high; shared outer panel and padding. Preview remains scrollable and readable, and returning to Write preserves caret and scroll where practical. Preview does not execute arbitrary embedded scripts.
- Code/structured-text editor: monospaced 13px/20px text, 16px padding, neutral 12px line-number gutter where useful, 16px radius, minimum height 200px. Syntax colors are a dedicated restrained functional palette, not arbitrary reuse of status meanings. Errors include line/column text and accessible navigation. A keyboard user must be able to leave the editor; Tab insertion behavior is explicit and has a discoverable escape route. Wrap long prose/config lines by default where useful; preserve exact whitespace in formats that require it.
- All editor variants support read-only, disabled, loading and error states using the shared field contract. Character/word count is secondary text outside or in a quiet footer. Pasting retains useful content and the product's allowed formatting; do not introduce arbitrary font families or sizes that break the system.

**Rich-text editor.** Use the canonical editor contract in [Rich text, markdown, code and code blocks](editors.md), including its 16px outer radius, 200px minimum height, toolbar, selection preservation and validation states. Document headings, lists, quotes and links preserve semantic structure.

**Read-only code block.** Use an approved monospace stack only for code, warm-neutral block, 16–20 px radius, 16 px padding, 12–13 px / 20 px code, and a 12 px language label. Copy action is a 36 px icon button with 44 px hit target. Long lines scroll inside the code region; line numbers are muted and not copied. Syntax color is limited and contrast-checked; do not import an unrelated dark IDE theme into the default light product. Editable code follows [Rich text, markdown, code and code blocks](editors.md). A full IDE additionally needs explicit requirements for completion, diagnostics, keyboard behavior and domain tooling; a styled code block is not an editor.
