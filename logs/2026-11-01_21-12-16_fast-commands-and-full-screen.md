# Faster voice commands, and "expand" as real full screen

## Faster commands (owner: "processing on computer commands must be a lot faster")

**Measured:**
- The log showed 1.3–1.8 s from switch-key up to "switch heard".
- On 4 of the owner's saved commands:

| Model | Time | Transcripts |
|---|---|---|
| Whisper turbo | 1378–1528 ms | all right |
| base.en | 84–109 ms | 2 of 4 wrong ("Click the link in the logo", "Move mouse to bottom here") |

- Shrinking turbo's `audio_ctx` made it slower (1.7–7.4 s) and garbled, so it was dropped.

**Built:**
- `fast_transcriber` (base.en, loaded at start, shared with meeting previews) hears every command first.
- `quick_command` trusts it for fixed commands: system, keys, modes, media, scroll, volume, mic, layout, desktops, Mission Control, switches, again, numbers, grid, custom; tab, shortcut and window commands with no app named; bare "click"; and an app name that is exactly an open app or a nickname.
- Anything with free words (click X, copy, type, search, go to, folders, site tabs, other names) is re-heard by turbo.
- Before the fast model is loaded, turbo is used directly.

## "expand not expanding to full screen"

- "expand" now sets `AXFullScreen` (macOS full screen, as the green button does), falling back to filling the screen for apps without full screen.
- "maximize"/"fill" fill the screen. "exit/leave full screen"/"shrink" turn full screen off; they're parsed before the ⌃⌘F "full screen" shortcut so they never toggle it on.

## Tests

- `test_widget`: a fixed command runs from the fast model alone; precise words go to the accurate model; an exact open app is fast; the `quick_command` rules; full screen, maximize and exit; the fallback for apps without full screen.
- `test_apps`: maximize and exit full screen.
- `test_command_catalog`: the page phrases.
- Also run: `test_host`, `test_entrypoints`.
- All pass.
