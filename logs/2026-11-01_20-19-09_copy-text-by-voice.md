# Copy text on screen by voice

**Asked for:** copy text you can see by saying its first part, or "copy <first words> … to <last words>" (screenshot: a TextEdit line).

**How:**
- `pointer.visible_text` reads the front window's text depth first: static text, text areas and fields, cells, links and headings, up to 20,000 characters. Editable elements aren't searched twice.
- `copy_span` joins the text and finds the spoken words. The start uses the best-matching window of on-screen words (word count n−1 to n+1, minimum 0.72). The end is searched after the start; with no end phrase, the span runs to the end of that line or paragraph.
- Each "to/through/until" split is tried. The best reading wins, so "to" inside the text works.
- The text goes on the clipboard (a normal copy). If it sits inside one editable element, it's also highlighted with `AXSelectedTextRange`. Incognito refuses to copy.
- "copy" and "copy that" stay ⌘C; "copy all" is ⌘A ⌘C.

**Live check:** the front app (Finder) was read in 0.07 s. TextEdit reported no windows to Accessibility at the time, so the owner tests the real flow.

**Tests (affected files):** `test_pointer` (spans, misheard words, "to" in the text, nothing found, highlight range), `test_control` (copy parsing), `test_widget` (copies and highlights, not found, Incognito), `test_command_catalog` (the 3 new page phrases). All pass.
