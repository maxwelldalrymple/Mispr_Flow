# Dictation

Hold a key, speak, let go: clean text appears in the app you're typing in. Everything runs on your Mac.

## Keys and gestures

| Do this | To |
|---|---|
| Hold `fn` (or your dictation key), speak, release | Push-to-talk: pastes when you let go |
| Double-tap the key (within 1 s) | Hands-free: keeps listening |
| `space` / `return` / `enter` while hands-free | Finish and paste |
| `delete` or the key while hands-free | Cancel ("Transcript cancelled · Undo" for 5 s) |
| `delete` on the Undo toast | Discard now |
| Click the widget's mic / long-press it | Hands-free / push-to-talk with the mouse |

- A quick tap does nothing, and `fn` + another key (fn + arrow) works as normal.
- **Choose any dictation key** in Settings → General: `fn`, one side of a modifier (Right ⌥), or a key (F5). Keys that would break hands-free (space, return, delete, Esc, Caps Lock) can't be picked.

## What happens to your words

1. **Transcription:** whisper.cpp, `large-v3-turbo` quantized, on the GPU. About 1.1 s for a 5–6 s clip.
   - **Nothing said, nothing typed.** Before transcribing, the Silero speech detector checks the recording (at an even volume, so a quiet mic still counts). Clicks, breathing and silence measure 0 s of speech and are dropped, so a button click never turns into "Thank you." or ".". Whisper's stock phrases for noise ("Captions by …", ". . .") and sound labels ("*Drums*", "[Music]") are removed too.
   - **Site names spelled right.** Whisper is primed with names like ChatGPT, GitHub, YouTube and LinkedIn, and common slips are fixed ("chat GBT" → ChatGPT, "git hub" → GitHub). Spoken web addresses are matched against the 1,000 most visited sites: "chat gbt dot com" → `chatgpt.com`. Unknown names ("bob dot com") are left as said.
   - **Long dictations appear as they're processed.** Past 20 s, the recording is cut at pauses into ~12 s pieces, and each piece is typed in as soon as it's ready, so the text grows while the rest is still being worked on. Auto-Enter presses Return once, after the last piece.
2. **Cleanup:** Gemma-3-4B removes "um/uh/like", repeats and retracted phrases ("Tuesday, no wait, Wednesday" → "Wednesday"), and fixes punctuation. A code-level guard rejects any output with a word you didn't say; then the raw transcript is pasted instead. Edit the cleanup instructions on the **Prompts** page. Hesitation sounds the model leaves in ("Uhh…", "um,", "erm") are always removed afterwards, however Whisper spells them.
3. **Where it goes:**
   - **A text box is focused:** it pastes, then restores your clipboard (the dictated text is marked private so clipboard managers skip it).
   - **No text box** (Finder, the desktop, a page with nothing focused): nothing is pasted. The error sound plays, and the text is left on the clipboard with "No text box · Copied to clipboard".
   - **Browsers:** if a browser says "no text box", it checks once more 0.15 s later (YouTube's comment box takes focus as it opens). The log records what was focused.
4. **History:** audio plus a JSON record is saved under `voice-recordings/YYYY-MM-DD/`, unless Incognito is on.

## Incognito

The switch in the window's top-right corner (it turns purple, and so does the widget's outline).

- Nothing is written to disk.
- The audio lives only in locked RAM and is wiped after transcription.
- Text is **typed** instead of pasted, so it never touches the clipboard. With no text box, nothing is copied at all.

## Auto-Enter

The ⏎ button left of Incognito. When on, Return is pressed 0.25 s after your text lands in a text box, so chat messages send themselves.

- It never presses Return if the text was copied rather than pasted.
- **In terminals it runs the command too**; turn it off to check commands first.
- **Cues:** a blue ⏎ badge on the widget's corner while it's on, and a chime with an "Auto-Enter on/off" notice when it changes.
- **Keyboard shortcut:** ⌃⌥↩ (Control-Option-Return) turns it on or off from anywhere. Change it, or turn it off, in **Settings → General → Auto-Enter key**.
- **⌘Return where Return is a new line:** on LinkedIn messages, Gmail and Outlook on the web, plain Return only starts a new line, so Auto-Enter presses ⌘Return there to send.

## Terminal mode

Dictating into Terminal, iTerm, Warp, Ghostty, kitty, Alacritty, WezTerm, Hyper, Tabby or Rio turns spoken syntax into shell syntax:

| Say | Typed |
|---|---|
| ls flag a | `ls -a` |
| LS dash L A | `ls -la` |
| cd tilde slash documents slash projects | `cd ~/documents/projects` |
| git commit dash m quote fix the login bug quote | `git commit -m "fix the login bug"` |
| grep dash r todo dot pipe head | `grep -r todo . \| head` |
| python three dash m pytest dash dash verbose | `python3 -m pytest --verbose` |
| npm run dev and and open localhost colon three thousand | `npm run dev && open localhost:3000` |

- The cleanup model gets terminal instructions, but its answer is used only if **every word in it was said**, so it can't add a command or flag (`rm`, `-rf`). Otherwise a plain word-for-symbol converter is used. Code: `mispr/terminal.py`.
- VS Code's built-in terminal isn't detected; its editor and terminal can't be told apart.

## The widget

The pill above the Dock:
- a live waveform while you talk, a spinner while it's working;
- hands-free ✓ / ✕ buttons and tooltips;
- on the first dictation after launch it names the mic in use;
- it follows the screen you're on and hides in fullscreen apps.

Hover it for the mic and ◉ (meeting note) buttons.

## Sounds

Every event has its own original sound: start, stop, lock, paste, cancel, alert, error, success, achievement. They're generated by `tools/make_sounds.py`. Turn them off in Settings → System → "Dictation and notification sounds".
