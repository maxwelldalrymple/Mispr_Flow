# Changelog

All notable changes to Mispr Flow. Dates are 2026.

## Unreleased

- **No text box, no paste:** if nothing typeable is focused, the text is left on the clipboard with an error sound and a "No text box · Copied to clipboard" notice instead of a ⌘V that goes nowhere. Saved with status `copied`.
- **Original sound cues** replace the macOS system sounds: start, stop, hands-free lock, cancel, and error, plus paste, notification, alert, success, and achievement cues for the upcoming main window. All synthesized from scratch by `tools/make_sounds.py` (a test checks the shipped WAVs match the generator byte for byte).
- **Mic name on first dictation:** "Using Built-in mic (recommended)" or "Using <device>" above the widget for 3 s.
- **App icon** redrawn on the macOS icon grid (`tools/make_icon.py`).
- **First-run setup window** (native macOS, light/dark): Welcome → Permissions → Models → Ready. Live permission checkmarks (Microphone and Accessibility required, Screen & System Audio optional), model download progress with Retry, and a quick fn guide. Reappears when something required is missing; reopen from the menu bar via **Setup Guide…**.
- Permissions are no longer requested on launch; fn starts working within a second of granting Accessibility (no restart).
- Tests: 769 unit tests; golden-image comparison now round-trips both sides through PNG (fixes false failures on text-heavy renders).

- Renamed to **Mispr Flow** (package `mispr`, data folder and repo `Mispr_Flow`), after briefly being "Mhispr_Flow".
- MIT license, CONTRIBUTING guide, this changelog.
- Documentation rewritten: README, `plan.md` (renamed from `PLAN.md`), and `docs/` (getting started, troubleshooting, architecture, development).
- Planned language support: auto-detect tested on English, French, and Spanish (see `plan.md` → Languages).

## Sep 30: Rebrand and freeze fix

- Rebrand from "Whispr Clone": new logo, app icon (`AppIcon.icns`), template menu-bar icon, and GitHub social preview.
- **Fixed:** the widget could freeze after releasing fn. PortAudio's macOS backend deadlocked in `Pa_StopStream`; the microphone now uses AVAudioEngine, and stopping can never block the UI (`logs/2026-09-30_14-34-34_mic-deadlock-fix.md`).

## Sep 30: Test suite

- 709 unit tests and 10 opt-in integration tests; any warning fails the run.
- Stress-tested (repetition, random order, parallel) and mutation-tested: score 63% → 97.6% (`logs/2026-09-30_13-25-55_stresstest.md`).
- **Fixed:** the cleanup safety check counted filler words on one side only, letting an obeyed instruction through.
- **Fixed:** a lock-file handle leaked when a second copy of the app exited.

## v0.2-llm-cleanup

- Local LLM cleanup (Gemma-3-4B) of fillers, repetitions, and self-corrections, with a code-level guarantee of zero invented words.
- Mandatory first-run model download with progress and Retry.

## v0.1-dictation

- Floating widget with every state, fn hold / double-tap, hands-free shortcuts, and the 5 s Undo toast.
- Microphone capture into a locked, wipeable buffer; local whisper.cpp transcription; paste with clipboard restore.
- Recordings saved as WAV + JSON (with app and browser-page context); Incognito setting.
- fn and the globe key swallowed so macOS's emoji picker doesn't open.
