# Plan

## Decisions

| Area | Choice | Notes |
|---|---|---|
| Language | Python | Fast to prototype. Uses PyObjC for native macOS APIs. |
| Speech-to-text | whisper.cpp | Via `pywhispercpp`, Metal-accelerated. Start with `large-v3-turbo` and fall back to `small.en` if latency is too high. |
| Cleanup | Small local LLM | `llama-cpp-python` with a ~1.5B instruct model (e.g. Qwen2.5-1.5B-Instruct, Q4). |
| v1 extras | Recording HUD | Small floating indicator while recording. |

## Components

| Component | Implementation |
|---|---|
| Hotkey | Quartz `CGEventTap` (PyObjC) on `flagsChanged`, watching the `SecondaryFn` flag. Hold means push-to-talk. Two taps within 1 s toggle recording. `pynput` cannot reliably see `fn`. |
| Audio | `sounddevice` capturing 16 kHz mono float32 into a preallocated NumPy buffer. |
| STT | whisper.cpp reads the NumPy buffer directly, so no WAV file is ever written. |
| Cleanup | A local LLM with a strict "fix, don't rewrite" system prompt. |
| Paste | Save the clipboard, set the text on `NSPasteboard`, post Cmd+V via `CGEvent`, then restore the clipboard. |
| HUD | Borderless, non-activating `NSPanel` so it does not steal focus from the target app. |
| Menu bar | `rumps` for status, quit, and settings. |

## Secure Audio Handling (Python caveats)

- Audio lives in a single preallocated, mutable NumPy array and is never converted to `bytes`, because immutable copies cannot be wiped.
- The buffer's pages are locked with `mlock` (via `ctypes`) to keep them out of swap.
- After transcription the buffer is zeroed in place with `arr.fill(0)`, then released with `munlock`.
- Known limitation: intermediate copies inside libraries (for example audio callback chunks) may briefly exist, so keep those paths minimal and reuse buffers.

## macOS Permissions Required

- Microphone
- Accessibility (to post the paste keystroke)
- Input Monitoring (for the event tap)
- The `fn` key must not be set to trigger the Emoji picker or system Dictation (System Settings > Keyboard > "Press 🌐 key to" > Do Nothing)

## Milestones

1. Detect the `fn` key (hold and double-tap) and log the events.
2. Record audio to an in-memory buffer, then zero it.
3. Transcribe with whisper.cpp and print the text.
4. Paste into the focused app, with clipboard restore.
5. Add the LLM cleanup pass.
6. Add the HUD and menu bar app.
7. Package as a `.app` (py2app) with a stable code-signing identity so permissions persist.
