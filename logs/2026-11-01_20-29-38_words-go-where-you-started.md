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

## Truly in the background (owner: "it should be very possible")

**More methods tested** with Chrome behind other windows, on a throwaway tab (closed afterwards):
- real key-down/up posted to Chrome's process: ignored;
- ⌘V posted to the process: ignored;
- `AXUIElementPostKeyboardEvent`: ignored;
- the earlier Accessibility inserts: ignored for rich editors.

Chrome came to the front when the tab was added (both `open -g` and AppleScript `make new tab`); the Claude window was put back in front each time, and the tests themselves ran with Chrome behind.

**Built: the browser tab route.**
- `target.browser_tab` notes the window and tab ids when dictation starts.
- `insert_in_tab` runs a page script in that tab through AppleScript `execute … javascript`, with no activation. The script focuses the box that had the cursor (else the biggest editable one) and types with `execCommand('insertText')`, which fires real input events. Enter (⌘Enter where needed) is dispatched with Auto-Enter.
- It needs Chrome's "Allow JavaScript from Apple Events", currently off. When it's off, the app shows how to turn it on once, and the text waits as before.
- The generated AppleScript was compiled with `osacompile`, and the page script syntax-checked with JavaScriptCore.

**Not built: a debugging connection into the Claude desktop app.**
- A second copy of Claude can't start (single instance, even with another profile), and restarting the real one would end this session, so it couldn't be tested live.
- Its code (`app.asar`) has a deliberate block list for `remote-debugging-port`, `remote-debugging-pipe`, `disable-web-security` and others, checked at launch. That's a security protection, and it isn't worked around. Claude desktop gets the text when you return; claude.ai in Chrome gets the full background route.

**Tests:**
- `test_target`: the tab route never activates, quotes are escaped, the setting-off result, not a browser, only scriptable browsers noted.
- `test_widget`: typed into the tab without switching, including Auto-Enter; setting off notifies and waits.
- All pass.
