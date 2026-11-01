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

## Change: never switch windows (owner: "I don't want you to move the window back… do it in the background")

**Background test** in a throwaway Chrome tab (opened, tested, closed; Chrome came to the front on opening despite `open -g`, and the Claude window was put back in front):

| Box | AXSelectedText | AXValue set | Keystrokes posted to Chrome's process |
|---|---|---|---|
| `<textarea>` | no | **yes** (applied about 0.2 s later) | no |
| `contenteditable` (Claude, ChatGPT, Slack style) | no | no | no |

**Now:**
- `insert_quietly` tries `AXSelectedText`, then `AXValue` with the words placed at the cursor. Either is verified after 0.25 s.
- If neither works, or Auto-Enter is on, the text is **held**. Every 0.3 s it checks whether you're back in that window, and not dictating. Once you are, it focuses the box, pastes, and presses Enter with Auto-Enter.
- After 10 minutes it goes to the clipboard. One held text at a time (an older one is copied).
- `bring_back` and `return_to` are removed.

**Tests:** in the background when allowed; otherwise waits with nothing pasted while elsewhere, then pasted on return; Auto-Enter waits then sends; timeout copies; still there pastes as usual; `_landed` verification. Affected files pass.
