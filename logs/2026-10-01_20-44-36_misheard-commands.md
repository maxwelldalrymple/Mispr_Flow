# "tab left" heard as "Top left."

**Branch:** `additional-browser-feature`

**Report:** in Chrome, saying "tab left" gave "No app called tab left".

**Cause:** the Commands history's raw text showed Whisper heard **"Top left."** four times out of four (19:24, 19:24, 20:41, 20:42). Short commands have no context, and "tab" sounds like "top".

**Fixes:**
1. **A command hint for Whisper.** While the switch key is held, Whisper gets an initial prompt listing the expected words ("Voice commands: tab left, tab right, tab 3, new tab, … window 2 …"), plus the user's nicknames and the running apps' names.
   - Every other transcription passes an empty prompt. pywhispercpp keeps parameters between calls, so the hint would otherwise stick to the next dictation (tested).
2. **A safety net, `apps.fix_misheard`:**
   - "top/tap/tub/tob/tad/tabb/tam" becomes "tab", but only right before left, right, over, a number or "side by side";
   - after next, previous, new, close, reopen, last, move, split, mute and unmute, the same words become "tab";
   - "tableft"/"tabright" is split.
   - "top" anywhere else is unchanged: "scroll to the top" and plain "top" still scroll.

## Tests

`pytest tests/test_apps.py tests/test_widget.py tests/test_transcribe.py`: all passed.

- `TestMisheardCommands` (9):
  - "Top left." → previous tab; "tap right" → next tab; "Tub three" → tab 3; "close top" → close tab; "Tableft." → previous tab;
  - "top" elsewhere is untouched;
  - the hint lists the commands and nicknames.
- `test_a_command_hint_never_sticks_to_the_next_dictation`: the prompt is cleared on the following call.
