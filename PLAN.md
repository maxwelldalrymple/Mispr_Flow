# Plan

## Decisions

| Area | Choice | Notes |
|---|---|---|
| Language | Python | Fast to prototype. Uses PyObjC for native macOS APIs. |
| Speech-to-text | whisper.cpp | Via `pywhispercpp`, Metal-accelerated. Start with `large-v3-turbo` and fall back to `small.en` if latency is too high. |
| Cleanup | Small local LLM | `llama-cpp-python` with a ~1.5B instruct model (e.g. Qwen2.5-1.5B-Instruct, Q4). |
| v1 extras | Floating widget | See "Floating Widget" below. |

## Components

| Component | Implementation |
|---|---|
| Hotkey | Quartz `CGEventTap` (PyObjC) on `flagsChanged`, watching the `SecondaryFn` flag. Hold means push-to-talk. Two taps within 1 s toggle recording. `pynput` cannot reliably see `fn`. |
| Audio | `sounddevice` capturing 16 kHz mono float32 into a preallocated NumPy buffer. |
| STT | whisper.cpp reads the NumPy buffer directly, so no WAV file is ever written. |
| Cleanup | A local LLM with a strict "fix, don't rewrite" system prompt. |
| Paste | Save the clipboard, set the text on `NSPasteboard`, post Cmd+V via `CGEvent`, then restore the clipboard. |
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
4. Transcribe with whisper.cpp.
5. Paste into the focused app, with clipboard restore.
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
| Hands-free | ✕ · waveform · ✓; tooltips "Cancel", "Finish and paste", "Press **fn** to finish and paste" | Double-tap `fn`, or click the mic |
| Processing | Dim waveform + spinner | Release `fn`, press `fn`, or click ✓ |
| Cancelled | "Transcript cancelled · Undo" toast with a 5 s draining progress bar. Undo processes the recording; otherwise the audio (held in locked RAM) is wiped when the bar runs out | Click ✕ |
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
- **Press during hands-free:** finish and paste.
- **fn + another key** (fn+arrow, fn+F-key): treated as a modifier combo, and the recording is discarded.
- fn is ignored while processing, during a meeting, or while the "Started by mistake?" card is open.
