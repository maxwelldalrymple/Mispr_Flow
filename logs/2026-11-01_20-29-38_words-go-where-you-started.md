# Words go where you started

**Asked for** (the second queued idea, now built): if you switch windows while it transcribes, the text should still go to the window or text box you started in. "It's where you start."

**How:** `mispr/target.py`.
- `capture()` runs when recording starts. It notes the front app, its window, and the text box with the cursor (if any). About 80 ms, measured.
- At the end, `still_there()` compares where you are now with that. The same app, window and box, or no box at the start, means the usual paste.
- If you've moved, the target box is the one that had the cursor, else the main box of that window. If there's none, it copies as before.
- **Quiet:** `AXSelectedText` inserts at the cursor without switching. It's checked by reading the value back, because some boxes accept the call and change nothing.
- **Otherwise,** or with Auto-Enter (a key press needs the window): activate the app, raise the window, focus the box, paste/type, then Enter, then return to the window you'd switched to after 0.9 s.
- Long dictations in pieces: once you've switched, the remaining pieces are held and sent together the same way.

**Mistake during the work:** an edit script emptied `widget.py` (it opened the file for writing before reading it). It was restored from the previous commit and the edits reapplied; nothing was lost.

**Tests (affected files):**
- New `test_target.py`: still there, switched app/window/box, unknown, box choice.
- `test_widget`: inserted quietly, otherwise switch back plus paste plus return, Auto-Enter always switches back to send, still there pastes as usual.
- `test_entrypoints`, `test_host`.
- The shared fixture now stubs `capture()`, so tests never read the real front app.
- All pass.
