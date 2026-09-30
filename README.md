<p align="center"><img src="mispr/assets/icon.png" width="160" alt="Mispr Flow"></p>

# Mispr Flow

Private, fully local voice dictation for macOS. Hold **fn**, speak, and clean, punctuated text appears in whatever app you're typing in. Speech recognition and text cleanup both run on your Mac: your voice never leaves it.

Modeled on the Wispr Flow desktop experience, without the cloud.

**macOS · Apple Silicon · 100% on-device · free · [MIT licensed](LICENSE)**

```bash
python3.13 -m venv .venv && .venv/bin/pip install cmake
CMAKE_ARGS="-DGGML_METAL=on" .venv/bin/pip install -r requirements.txt
.venv/bin/python -m mispr        # then hold fn and speak
```

## Why

Mispr Flow is an open clone of [Wispr Flow](https://wisprflow.ai), built for four reasons:

1. **Open source.** MIT licensed. Every line (the hotkey, the audio pipeline, the prompts, the safety checks) is readable, auditable, and changeable.
2. **Free.** No subscription and no account. The models are free downloads that run on your own Mac.
3. **Your voice stays on your Mac.** Wispr Flow sends your audio to its servers for transcription and cleanup, where it may be retained by a third party. For code, credentials in context, or personal and business conversations, that's an unacceptable risk. Mispr Flow transcribes and cleans up entirely on-device.
4. **Full control and customization.** The icons, sounds, widget look, shortcuts, models, and cleanup prompt are all yours to change (see `mispr/assets/`, `settings.json`, and [plan.md](plan.md)). It's also multilingual by design: the Whisper model understands about 99 languages. Today the app transcribes English; a language setting is on the roadmap.

## What it does

- **Dictate anywhere with `fn`.** Hold for push-to-talk, or double-tap for hands-free.
- **Local transcription.** whisper.cpp (large-v3-turbo) on the Mac's GPU: about 1.1 s for a 5-6 s clip.
- **Local cleanup that never invents words.** A small LLM (Gemma-3-4B) removes "um/uh/like", repeated words, and retracted phrases ("Tuesday, no wait, Wednesday" becomes "Wednesday"), and fixes punctuation. A code-level check rejects any output containing a word you didn't say and pastes the raw transcript instead.
- **Pastes into the focused app,** then restores your clipboard. The pasted text is marked private so clipboard managers ignore it. If nothing you can type into is focused (Finder, the desktop, a page with no text box), it skips the paste, plays the error sound, and leaves the text on your clipboard with a "No text box · Copied to clipboard" notice.
- **Floating widget** above the Dock: live waveform, hands-free controls, a 5-second Undo after cancelling, and tooltips. On the first dictation after launch it names the mic in use ("Using Built-in mic (recommended)"). It follows the screen you're working on and hides in fullscreen apps.
- **Sound cues** for every event (start, stop, hands-free lock, paste, cancel, errors). All original, synthesized by the app's own generator script.
- **History on disk (on by default).** Each dictation is saved as audio plus a JSON record (transcript, timing, the app it went into, and the page URL for browsers). The Incognito setting turns this off completely.
- **Dock and menu-bar app.** The logo sits in the Dock while it runs (click it to open the app's window), with a menu-bar icon too. It captures fn itself so macOS's emoji picker doesn't open.
- **Guided setup.** A 4-step window on first launch (Welcome → Permissions → Models → Ready) explains each permission before asking for it. Reopen it anytime from the menu bar: **Setup Guide…**

End to end, text appears about 1.8 s after you stop talking.

## Requirements

- A Mac with Apple Silicon (M1 or newer). Developed on an M1 Pro, 16 GB, macOS 26.
- About 3.1 GB of disk for the two models (downloaded once, SHA-256 verified) and about 3.5 GB of RAM while running.
- Python 3.13 (for running from source).
- Permissions (the setup window asks for each, with an explanation):
  - **Microphone** (required).
  - **Accessibility** (required): captures fn (so the emoji picker stays closed), pastes, and reads the browser URL.
  - **Screen & System Audio** (optional): for the upcoming meeting notetaker.

## Install and run (from source)

```bash
python3.13 -m venv .venv
.venv/bin/pip install cmake
CMAKE_ARGS="-DGGML_METAL=on" .venv/bin/pip install -r requirements.txt
.venv/bin/python -m mispr
```

`llama-cpp-python` builds from source with Metal (GPU) support, which takes a few minutes. On first launch the **setup window** walks you through allowing the Microphone and Accessibility (and optionally Screen & System Audio for meeting notes), then downloads the models with a progress bar. Dictation unlocks once both models are verified. Quit from the logo in the menu bar.

## Using it

| Do this | To |
|---|---|
| Hold `fn`, speak, release | Push-to-talk: pastes when you let go |
| Double-tap `fn` (within 1 s) | Start hands-free dictation |
| `space`, `return`, or `enter` (hands-free) | Finish and paste |
| `delete` or `fn` (hands-free) | Cancel. A "Transcript cancelled · Undo" toast appears for 5 s |
| `delete` (on the Undo toast) | Discard immediately |
| Hover the pill above the Dock | Show the mic (dictate) and ◉ (meeting note; capture coming soon) buttons |
| Click the mic / long-press it | Hands-free / push-to-talk with the mouse |

A quick fn tap does nothing, and fn combined with another key (fn + arrow) works as normal.

### Sounds

| Sound | Plays when |
|---|---|
| start | Recording begins |
| stop | You release fn, or finish hands-free |
| lock | A double-tap locks hands-free on |
| paste | Your text lands in a text box |
| cancel | You cancel a recording |
| alert | You recorded, but no words came out |
| error | The mic won't open, there's no text box to paste into, or the model download fails |
| success | The models finish installing, or a permission turns green in the setup window |
| achievement | You finish the setup guide |

They're original cues synthesized by `tools/make_sounds.py` into `mispr/assets/sounds/` (a `notification` cue is reserved for the main window). Edit the script and re-run it, or drop in your own WAVs, to change them.

## Settings

`~/Library/Application Support/Mispr_Flow/settings.json` (a settings screen is planned):

| Key | Default | Meaning |
|---|---|---|
| `incognito` | `false` | When `true`, nothing is written to disk: audio lives only in locked RAM and is wiped right after transcription |
| `cleanup` | `true` | When `false`, pastes raw Whisper text with no LLM cleanup |
| `onboarded` | `false` | Set when you finish the setup window. The window also reappears automatically if a required permission is revoked or a model goes missing |

## Where things live

| What | Where |
|---|---|
| Models | `~/Library/Application Support/Mispr_Flow/models/` |
| Settings | `~/Library/Application Support/Mispr_Flow/settings.json` |
| Saved dictations | `voice-recordings/YYYY-MM-DD/` in the project folder (gitignored). Files are named by start time to the millisecond: `2026-09-30_12-28-33-123.wav` + `.json` |
| Meeting notes (planned) | `meeting-recordings/` in the project folder (gitignored) |
| Test and stress-test reports | `logs/` |

## Privacy

- **Local-only processing.** No audio or text is sent over the network. After the one-time model download, the app works offline.
- **Local-only storage.** Saved dictations stay in the project folder. Incognito mode stores nothing.
- **Incognito is the only guaranteed erase.** On SSDs and APFS, deleting or overwriting a file doesn't reliably destroy its data (copy-on-write, wear leveling, snapshots). So when you need a recording to be unrecoverable, it must never be written in the first place.
- **Memory hygiene.** The audio buffer is locked in RAM (`mlock`, never swapped to disk) and zeroed after every recording.
- **Clipboard hygiene.** Dictated text is marked transient/concealed and your previous clipboard is restored.

## Debugging

```bash
MISPR_DEBUG=1 .venv/bin/python -m mispr
```

Prints a timestamped trace of fn events, state changes, transcription and cleanup timings, and each recording's length, peak, and wipe check. It never prints audio content.

## Project layout

```
mispr/
  app.py         entry point: menu bar, single-instance lock, permissions, clean shutdown
  widget.py      floating widget: state machine, layout, rendering, mouse/keyboard handling
  hotkey.py      fn / globe-key event tap and hands-free shortcuts
  audio.py       microphone capture (AVAudioEngine) into a locked, wipeable buffer
  transcribe.py  whisper.cpp speech-to-text
  cleanup.py     Gemma cleanup + the zero-invented-words guard
  paste.py       clipboard paste and restore
  context.py     frontmost app and browser page lookup (Accessibility API)
  storage.py     saving recordings + JSON metadata
  models.py      model specs, download, SHA-256 verification
  setup.py       mandatory first-run model setup
  settings.py    settings file
  onboarding.py  first-run setup window (Welcome → Permissions → Models → Ready)
  screens.py     which screen to follow; fullscreen detection
  draw.py, sounds.py, levels.py, threads.py
  assets/        logo, app icon (.icns), menu-bar icon, GitHub social preview
tests/           pytest suite + golden files
tools/           stress test, mutation test, cleanup-model eval, state renderer, icon and sound generators
logs/            stress-test and bug-fix reports
```

## Testing

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

- **841 unit tests, about 15 s.** They never touch the real microphone, clipboard, keyboard, models, recordings, or settings: those are faked or redirected to temporary folders. Any warning fails the run.
- **Integration tests (opt-in).** Real Whisper, Gemma, and microphone:
  ```bash
  MISPR_INTEGRATION=1 .venv/bin/python -m pytest tests/test_integration.py
  ```
- **Golden files** (`tests/golden/`) pin the widget's layout and the rendered look of every state. After an intentional visual change, regenerate them, then review the new files:
  ```bash
  UPDATE_GOLDEN=1 .venv/bin/python -m pytest
  ```
- **Test-quality tools.** `tools/stress_test.py` runs repeated, random-order, and parallel runs; `tools/mutation_test.py` plants bugs and checks the tests catch them (current score: 97.6%); `tools/eval_cleanup.py` scores the cleanup model (invented words must be zero). `tools/make_sounds.py` and `tools/make_icon.py` regenerate the sound cues and `AppIcon.icns`.

## Status

Dictation works end to end, with original sound cues and a guided setup window. Next up: the main window (history, stats, settings), modeled screen by screen on Wispr Flow's; then languages, the meeting notetaker, and an installable app (DMG/`.pkg`). See [plan.md](plan.md) for the decisions and roadmap.

## Documentation

- [Getting started](docs/getting-started.md): install, permissions, first run
- [Troubleshooting](docs/troubleshooting.md): fixes for every problem we've hit
- [Architecture](docs/architecture.md): how the pipeline, threads, and widget state machine work
- [Development](docs/development.md): tests, golden files, tools, branches, releases
- [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Plan and roadmap](plan.md)

## License

Mispr Flow's code is [MIT licensed](LICENSE). The models are not part of this repository: they're downloaded on first run. Whisper models are MIT licensed; Gemma (`ggml-org/gemma-3-4b-it-GGUF`) is subject to Google's Gemma Terms of Use.

Mispr Flow is an independent project and is not affiliated with Wispr Flow.
