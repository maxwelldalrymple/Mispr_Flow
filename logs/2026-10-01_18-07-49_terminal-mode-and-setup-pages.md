# Terminal dictation mode, and setup permissions on two pages

**Branch:** `speaker-id`

## Terminal mode (`mispr/terminal.py`)

**When:** dictation that started in a terminal: Terminal, iTerm, Warp, Ghostty, kitty, Alacritty, WezTerm, Hyper, Tabby or Rio. VS Code's built-in terminal can't be told apart from its editor, so it isn't included.

**How:**
- The cleanup model gets terminal instructions plus examples. Spoken symbols become characters, flags are written as typed, everything is lowercase, there's no trailing period, and words inside quotes stay as said. It must never add anything that wasn't said.
- **Safety check:** every 2+ letter word in the output must have been said, alone or as said letters run together ("l a" → `-la`). This is what blocks the model from adding a command or flag. An earlier version checked only 3+ letter words and would have passed `rm -rf /` for "ls flag a"; caught while testing.
- If the check fails, or the model is unavailable, or cleanup is off, a plain word-for-symbol converter is used:

| Said | Typed |
|---|---|
| ls flag a | `ls -a` |
| LS dash L A. | `ls -la` |
| cd tilde slash documents slash projects | `cd ~/documents/projects` |
| git commit dash m quote fix the login bug quote | `git commit -m "fix the login bug"` |
| grep dash r todo dot pipe head | `grep -r todo . \| head` |
| cat readme dot md | `cat readme.md` |
| python three dash m pytest dash dash verbose | `python3 -m pytest --verbose` |
| npm run dev and and open localhost colon three thousand | `npm run dev && open localhost:3000` |

- **Auto-Enter never presses Enter in a terminal**, so a misheard command can't run on its own.

## Setup: two permission pages

The user found the 5-row permissions page cramped. Setup is now:

1. Welcome
2. **Allow access** (required: Microphone, Accessibility)
3. **Optional features** (Screen & System Audio, Full Disk Access, Control Finder; never blocks Continue)
4. Models
5. Ready

The window is back to 520 px, the step counter reads "of 5", and all golden screenshots were regenerated and checked visually.

## Tests

The full Python suite ran: **1215 passed, 10 skipped**.

- `tests/test_terminal.py` (15):
  - the converter cases above;
  - "rm -rf /" and "&& rm x" are rejected;
  - the model is used with terminal instructions (backticks stripped);
  - unfaithful, failed, or cleanup-off falls back to the converter;
  - which apps count as terminals.
- `TestTerminalDictation` (2): terminal versus normal cleanup chosen by app; Auto-Enter skipped in terminals.
- Setup:
  - navigation through the optional page (back and forward);
  - a new golden screenshot for the optional page;
  - window size.
