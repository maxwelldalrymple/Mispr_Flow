# Plan

## Decisions

| Area | Choice | Notes |
|---|---|---|
| Language | Python | Fast to prototype. Uses PyObjC for native macOS APIs. |
| Speech-to-text | whisper.cpp | Via `pywhispercpp`, Metal-accelerated. `ggml-large-v3-turbo-q5_0` (574 MB), downloaded on first run to `~/Library/Application Support/WhisprClone/models` and SHA-256 verified. Reduced `audio_ctx` breaks turbo, so default settings are used. |
| Cleanup | Small local LLM | `llama-cpp-python` with a ~1.5B instruct model (e.g. Qwen2.5-1.5B-Instruct, Q4). |
| v1 extras | Floating widget | See "Floating Widget" below. |

## Components

| Component | Implementation |
|---|---|
| Hotkey | Quartz `CGEventTap` (PyObjC) on `flagsChanged`, watching the `SecondaryFn` flag. Hold means push-to-talk. Two taps within 1 s toggle recording. `pynput` cannot reliably see `fn`. |
| Audio | `sounddevice` capturing 16 kHz mono float32 into a preallocated NumPy buffer. |
| STT | whisper.cpp reads the NumPy buffer directly, so no WAV file is ever written. |
| Cleanup | A local LLM with a strict "fix, don't rewrite" system prompt. |
| Paste | Save the clipboard, set the text on `NSPasteboard` (marked transient/concealed so clipboard managers skip it), post ⌘V via `CGEvent`, restore the clipboard 0.5 s later unless the user copied something new. |
| Widget | Borderless, non-activating `NSPanel` drawn with AppKit (PyObjC), so it never steals focus. |
| Menu bar | `NSStatusItem` for status and quit. |

## Secure Audio Handling (Python caveats)

- Audio lives in a single preallocated, mutable NumPy array and is never converted to `bytes`, because immutable copies cannot be wiped.
- The buffer's pages are locked with `mlock` (via `ctypes`) to keep them out of swap.
- After transcription the buffer is zeroed in place with `arr.fill(0)`, then released with `munlock`.
- Known limitation: intermediate copies inside libraries (for example audio callback chunks) may briefly exist, so keep those paths minimal and reuse buffers.

## macOS Permissions Required

- Microphone
- Accessibility: swallow `fn` presses so macOS doesn't open the emoji picker (like Wispr Flow), and post the paste keystroke
- Input Monitoring: fallback listen-only `fn` tap when Accessibility isn't granted (macOS's own fn action then still fires)

## Milestones

1. ✅ Floating widget, all states, UI only (fake waveform, click-driven).
2. ✅ Detect the `fn` key (hold and double-tap) and drive the widget from it.
3. ✅ Record the microphone into an in-memory buffer (real waveform), then zero it.
4. ✅ Transcribe with whisper.cpp (large-v3-turbo q5, Metal): ~1.1 s for a 5-6 s clip, ~690 MB RAM.
5. ✅ Paste into the focused app, with clipboard restore.
6. Add the LLM cleanup pass.
7. Meeting notetaker: system audio capture, diarization, summary to `~/Documents/meeting-recordings`.
8. Package as an unsigned `.app` (py2app) in a drag-to-Applications DMG (`create-dmg`), built by one script. Starts once dictation works end to end.

## Floating Widget

A transparent, non-activating panel centred just above the Dock on the screen that holds the focused window. It never steals focus from the app being dictated into.

| State | Appearance | Entered by |
|---|---|---|
| Idle | Tiny outlined pill | App running |
| Hover | Mic button + ◉ note button; tooltips "Dictate **fn**" / "New note **⌥M**" | Pointer over the pill |
| Hold | Compact black pill with live waveform | Hold `fn`, or long-press the mic |
| Hands-free | ✕ · waveform · ✓; tooltips "Cancel", "Finish and paste", "**space** to paste · **fn** to cancel" | Double-tap `fn`, or click the mic |
| Processing | Dim waveform + spinner | Release `fn` (hold), space/return (hands-free), or click ✓ |
| Cancelled | "Transcript cancelled · Undo" toast with a 5 s draining progress bar. Undo processes the recording; otherwise the audio (held in locked RAM) is wiped when the bar runs out | Click ✕, press delete, or press `fn` during hands-free |
| Meeting | Outlined pill: small waveform + ■ stop | Click ◉ or press ⌥M |
| Started by mistake? | Card with Discard / Keep | Stopping a meeting that captured almost nothing |

Behaviour:
- Subtle system sounds on start, stop, and cancel.
- Follows the screen of the focused window (falls back to the screen under the pointer).
- The idle pill hides while the focused app is fullscreen, and still appears when recording starts.

## Meeting Notetaker (◉)

Records a Zoom / Google Meet call, transcribes everyone with speaker labels, and produces a business-style summary document.

- **Capture:** microphone ("You") plus system audio (other participants) via ScreenCaptureKit audio capture. Requires the Screen & System Audio Recording permission.
- **Transcription:** whisper.cpp in chunks for a live transcript; a speaker-diarization pass after the meeting to label speakers.
- **Summary:** a local LLM turns the transcript into a structured document (overview, decisions, action items with owners, open questions).
- **Output:** the transcript and summary are saved to `~/Documents/meeting-recordings`. Audio follows the same rule as dictation: RAM only, zeroed after processing, never written to disk.
- **Notes window (later):** My thoughts / Transcript / Summary tabs, plus "Ask anything about this meeting" backed by the local LLM.
- **Guard:** if a meeting captured only a few words, ask "Started by mistake?" (Discard / Keep).

## Distribution

- **Format:** DMG built from a py2app bundle, so others can download and install it.
- **Signing:** unsigned for now. Users must allow it via System Settings > Privacy & Security > Open Anyway. Revisit a Developer ID and notarization before any wide release.
- **Permissions caveat:** macOS ties Microphone, Accessibility, and Input Monitoring grants to the app's signature, so unsigned updates may require re-granting them. Ad-hoc sign with a consistent identifier to reduce this.
- **Models:** downloaded on first launch (not bundled) to keep the DMG small.
- **Timing:** after dictation works end to end (fn, record, transcribe, paste).

## fn Gestures

- **Hold** (≥ 0.3 s): push-to-talk. Recording starts on key-down so the first word isn't clipped; release finishes.
- **Tap** (< 0.3 s): discarded silently. A second press within 1 s of the first starts hands-free.
- **Press during hands-free:** cancel (shows the Undo toast).
- **fn + another key** (fn+arrow, fn+F-key): treated as a modifier combo, and the recording is discarded.
- fn is ignored while processing, during a meeting, or while the "Started by mistake?" card is open.
- The 🌐/fn key also emits its own key event (keycode 179); macOS opens Emoji & Symbols from it, so it is swallowed along with the fn flag.

## Keyboard Shortcuts

- **Hands-free:** space, return, or keypad enter = finish and paste; delete or fn = cancel.
- **Cancelled toast:** delete = discard immediately (skip the Undo countdown).
- These keys are swallowed only in those states; modified presses (e.g. ⌘Space) always pass through.

## Transcription Notes

- The model loads and warms up (Metal pipeline compile) in the background at launch, so the first dictation isn't slow.
- Clips under 0.3 s or with peak level under 0.01 are skipped, since Whisper hallucinates text ("Thank you.") on silence.
- Annotations like `[BLANK_AUDIO]` and `(music)` are stripped.
- Transcription runs on a worker thread; whisper.cpp releases the GIL, so the fn event tap and UI stay responsive.
- Known gaps: first-run download has no progress UI yet; ⌘V uses the ANSI V keycode (non-QWERTY layouts TODO).

## Recording Storage

- **Default:** every finished or cancelled dictation is saved to `~/Documents/voice-recordings/YYYY-MM-DD/`, named by its start time to the millisecond: `2026-09-30_12-28-33-123.wav` (16 kHz mono PCM) plus `2026-09-30_12-28-33-123.json`. The JSON holds `started_at`/`ended_at` (ms precision), duration, status (`pasted`/`cancelled`), transcript, word count, `recorded_in` (app), `pasted_into` (app, bundle id, and for browsers the page `url` and `page_title`), and the model. This feeds the future history and stats UI (and a "Recover" action for cancelled clips).
- **Browser page lookup:** via the Accessibility API (walk up from the focused element to the outermost `AXWebArea` and read `AXURL`, falling back to the window's `AXDocument`), so no per-browser Automation prompts. ~50 ms in Chrome; 0.3 s timeout.
- **Incognito toggle (future settings UI):** `incognito` in `~/Library/Application Support/WhisprClone/settings.json`. When on, nothing is written; audio is wiped from RAM immediately.
- **Not saved:** fn taps, fn+key combos, clips under 0.3 s, and silent clips.
- **Possible upgrade:** encrypt recordings at rest with a key in the macOS Keychain, so deleting the key crypto-shreds them (the only reliable "delete" on SSD/APFS).
