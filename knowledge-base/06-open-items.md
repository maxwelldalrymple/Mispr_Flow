# 6. Open items and roadmap

## Next (queued by the user)

1. **First-run tutorial** of every feature, for someone who just downloaded the app (after the UI work).
2. **Strict security audit** suitable for open-source distribution. Verify nothing is sent over the internet except the hash-checked model downloads, and write the audit into `logs/`.

## Known limits

- On Zoom-processed audio, similar voices (especially men) merge into one speaker.
- The echo gate needs a second or two to learn the speakers' leak.
- VS Code's integrated terminal isn't detected for terminal mode.
- "Mute app" works only for browser tabs.
- Seek uses arrow keys, 5 s per press (Netflix and others differ).
- If the app quits while the mic is muted, the mic stays muted.
- The click-filter test with the real Silero model is skipped, because the test setup redirects the models folder (a one-line fix).
- One Swift echo test uses random audio and failed once in many runs.

## Later

- Languages (Whisper supports ~99).
- A personal dictionary and snippets.
- An installable app for other Macs (DMG / `.pkg` with bundled Python).
