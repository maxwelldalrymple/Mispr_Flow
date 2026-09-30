# Troubleshooting

Run with the debug trace to see what's happening:

```bash
MHISPR_DEBUG=1 .venv/bin/python -m mhispr
```

It logs every fn press, state change, transcription and cleanup timing, and each recording's length, peak, and wipe check (never audio content).

## fn opens the Emoji & Symbols window

Mhispr_Flow swallows fn and the 🌐 key's own key event, but only with **Accessibility** permission. Without it, it can only listen, so macOS acts on fn too.

- Allow the launching app in **System Settings → Privacy & Security → Accessibility**. If fn is already working in listen-only mode, it takes effect within about 2 s (the log prints `Accessibility granted`); otherwise restart the app.
- Or set **Keyboard → "Press 🌐 key to" → Do Nothing**.

## Pressing fn does nothing

- The startup log shows `fn dictation is off`: allow **Input Monitoring** (or Accessibility) and restart.
- The widget is in the setup state ("Downloading models"): dictation is locked until the models are installed.
- A quick tap (under 0.3 s) is ignored on purpose. Hold fn, or double-tap.
- fn is ignored while text is processing, during a meeting, or on the "Started by mistake?" card.

## Text doesn't appear after dictating

- Pasting uses ⌘V, which needs **Accessibility**.
- The clip was silent or under 0.3 s: those are skipped (Whisper invents text like "Thank you." on silence). The log shows `0 chars`.
- Non-QWERTY keyboard layouts (Dvorak, AZERTY): ⌘V is sent as the US "V" key. This is a known issue.
- The focused field doesn't accept pasting (some password fields, games).

## The text isn't cleaned up

The cleanup model's output is rejected whenever it contains a word you didn't say, and your raw transcript is pasted instead. That's the safety check working. Check the saved JSON's `cleanup.rejected` field, or the log (`cleanup ... rejected (invented words: ...)`). Also check `"cleanup"` isn't `false` in settings.

## The widget froze after releasing fn

Fixed on 2026-09-30. It was a PortAudio/CoreAudio deadlock; the microphone now uses AVAudioEngine and stopping can't block (see `logs/2026-09-30_14-34-34_mic-deadlock-fix.md`). If a freeze ever happens:

1. Capture evidence first: `sample $(pgrep -f "m mhispr") 3 -file ~/Desktop/mhispr-hang.txt`.
2. Force-quit: `kill -9 $(pgrep -f "m mhispr")`. A frozen app can't run its normal quit handler.
3. Relaunch.

## Two logo icons in the menu bar

A force-killed copy leaves a "ghost" icon until you hover over it; hovering clears it. Normal Quit and `kill` (SIGTERM) remove the icon properly. Also check that the real Wispr Flow isn't running: its icon looks similar and it also listens for fn.

## "Model download failed · Retry"

- Check your internet connection and click **Retry**.
- A download that fails the SHA-256 check is deleted automatically and never used.
- Check free disk space (3.1 GB needed).

## "mhispr: already running"

Only one copy may run (two would both react to fn). Quit the other one from the menu bar, or `kill $(pgrep -f "m mhispr")`.

## The mic is slow to start or clips the first word

About 0.1 s is lost at the start of each recording while the microphone starts. Start speaking a beat after pressing fn.

## "leaked function" messages when quitting

Harmless shutdown notices printed by the `soxr` resampling library. They don't affect anything.

## Permissions keep resetting

macOS ties permissions to the app's code signature. When running from source, grants belong to the launching app (Terminal / Claude). The packaged app will be ad-hoc signed with a stable identifier to reduce this.

## Resetting everything

```bash
kill $(pgrep -f "m mhispr")
rm ~/Library/Application\ Support/Mhispr_Flow/settings.json   # settings back to defaults
rm -rf voice-recordings/                                         # saved dictations (see privacy note)
```

Keep `models/` unless you want to re-download 3 GB. Deleting saved recordings doesn't reliably erase them from an SSD; use Incognito if a recording must never be recoverable.
