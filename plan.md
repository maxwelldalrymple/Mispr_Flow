# Plan

The engineering record for Mispr Flow: decisions, architecture, what's done, and what's next. For how to install and use the app, see the [README](README.md) and [docs/](docs/).

## Goals

Mispr Flow is a Wispr Flow clone built to be:

1. **Open source.** MIT licensed ([LICENSE](LICENSE)); every part is readable and changeable.
2. **Free.** No subscription or account; free models running locally.
3. **Private.** Voice audio is never sent to a cloud server; transcription and cleanup run on-device.
4. **Fully customizable and multilingual.** Icons, sounds, widget, shortcuts, models, and prompts are all under the user's control. Multilingual: Whisper large-v3-turbo supports ~99 languages; the app currently transcribes English (`LANGUAGE = "en"` in `transcribe.py`) and the cleanup prompt is English. A language setting (explicit or auto-detect) plus multilingual cleanup examples are on the roadmap.

## Decisions

| Area | Choice | Why / notes |
|---|---|---|
| Language | Python 3.13 + PyObjC | Fast to build. PyObjC gives direct access to AppKit, Quartz, AVFoundation, and Accessibility. v1 ships in Python; modules are split so parts can move to Swift later (the fn event tap first). |
| Speech-to-text | whisper.cpp via `pywhispercpp`, `ggml-large-v3-turbo-q5_0` (574 MB) | Near-best accuracy, Metal-accelerated, ~1.1 s for a 5-6 s clip, ~690 MB RAM. Reduced `audio_ctx` breaks turbo (gibberish), so default settings are used. |
| Text cleanup | `llama-cpp-python` (Metal) with `gemma-3-4b-it-Q4_K_M` (2.5 GB, `ggml-org/gemma-3-4b-it-GGUF`) | Won a 27-case eval: 0 invented words, 0 key words lost, most conservative on ambiguous corrections (~550 ms). Gemma Terms of Use apply. |
| Microphone | AVAudioEngine (PyObjC) + `soxr` resampling to 16 kHz | Replaced PortAudio (`sounddevice`), whose macOS backend deadlocked in `Pa_StopStream` and froze the widget. See [logs](logs/2026-09-30_14-34-34_mic-deadlock-fix.md). |
| Hotkey | Active Quartz event tap at the HID level | Swallows fn and the globe key (keycode 179) so macOS doesn't open Emoji & Symbols, as Wispr Flow does. Falls back to a listen-only tap without Accessibility. |
| Paste | Clipboard + synthetic ⌘V, then restore | Works in every app. Text is marked transient/concealed for clipboard managers. |
| Storage | Save recordings by default; Incognito turns it off | Needed for the future history and stats UI. |
| Distribution | Unsigned `.pkg` whose postinstall downloads the models; first-launch setup as fallback | Keeps the download small, fits GitHub Releases' 2 GB limit, and updates don't re-download 3 GB of models. |
| Branding | Mispr Flow, package `mispr`, logo in `mispr/assets/` | Renamed from "Whispr Clone". "Wispr Flow" refers only to the product this is modeled on. |

## Architecture

```
fn key ──► hotkey.FnMonitor (HID event tap) ──► widget.WidgetController (state machine, 60 fps)
                                                   │
             ┌─────────────────────────────────────┼──────────────────────────────┐
             ▼                                     ▼                              ▼
   audio.Recorder (AVAudioEngine        transcribe.Transcriber            widget rendering
   → soxr → mlock'ed buffer)            (whisper.cpp, worker thread)      (NSPanel, AppKit)
                                                   │
                                        cleanup.Cleaner (Gemma + guard)
                                                   │
                         paste.paste_text ◄────────┴────► storage.save_recording
                         (⌘V, restore clipboard)          (WAV + JSON, unless Incognito)
```

| Component | Implementation |
|---|---|
| Hotkey | `CGEventTap` on flagsChanged / keyDown / keyUp. Handlers are deferred with `AppHelper.callAfter`, so the tap never holds keystrokes system-wide while work runs. |
| Audio | `MicEngine` (the only AVFoundation code) taps input bus 0 at the native rate (44.1 kHz). `Recorder` resamples to 16 kHz into a preallocated, `mlock`ed NumPy buffer. |
| STT | whisper.cpp reads the buffer view directly (no copy, no WAV file). Runs on a daemon worker. |
| Cleanup | Gemma with a strict "minimal edit, never add words" prompt and few-shot examples; every output is checked by `cleanup.check()`. |
| Paste | `NSPasteboard` snapshot → set text + private types → post ⌘V (flags = ⌘ only) → restore after 0.5 s unless the user copied something new. |
| Context | Accessibility API: walks up from the focused element to the outermost `AXWebArea` for the page URL; falls back to the window's `AXDocument`. 0.3 s timeout. |
| Widget | Borderless, non-activating `NSPanel` at status-bar level, redrawn at 60 fps by an `NSTimer` in common run-loop modes. Click-through except over buttons. |
| Menu bar | `NSStatusItem` with the logo as an 18 pt template image (tints for light/dark); "Quit Mispr Flow". |
| Threads | `threads.start_daemon()` for model loads, transcription, downloads, and mic stops, so nothing can block quitting. |

See [docs/architecture.md](docs/architecture.md) for the full walkthrough.

## macOS Permissions

Requested from the setup window (`onboarding.py`), never on launch:

- **Microphone** (required): dictation.
- **Accessibility** (required): swallow fn and the globe key so macOS doesn't open the emoji picker, post the paste keystroke, and read the browser page. fn works within a second of granting it (`app.maintain_hotkey`).
- **Screen & System Audio** (optional): the meeting notetaker's system-audio capture; may require reopening the app.
- **Input Monitoring:** not requested. It's only a fallback for a listen-only fn tap when Accessibility is off.

## Milestones

1. ✅ Floating widget with every state (UI).
2. ✅ fn gestures (hold, double-tap, combos) drive the widget; fn and the globe key are swallowed.
3. ✅ Microphone into a locked, wipeable buffer; live waveform.
4. ✅ Local transcription with whisper.cpp (large-v3-turbo q5, Metal).
5. ✅ Paste into the focused app with clipboard restore.
6. ✅ LLM cleanup (Gemma-3-4B) with the zero-invented-words guard; mandatory first-run model setup.
7. ✅ Recording storage (WAV + JSON with app and page context) and the Incognito setting.
8. ✅ Test suite (709 unit + 10 integration tests), stress-tested and mutation-tested (97.6%).
9. ✅ Mic freeze fix: AVAudioEngine replaced PortAudio; non-blocking stop.
10. ✅ Rebrand to Mispr Flow (package, data folder, logo, app and menu-bar icons, GitHub repo).
11. ✅ First-run setup window: Welcome → Permissions (live checkmarks; Microphone + Accessibility required, Screen & System Audio optional) → Models (progress, Retry) → Ready. Reopens when something required is missing; "Setup Guide…" in the menu; no launch-time permission prompts.
12. ⬜ Main window: history (from the saved JSON), stats (words, WPM, streak, apps), settings (Incognito, cleanup).
13. ⬜ Meeting notetaker (◉): mic + system audio, diarization, LLM summary to `meeting-recordings/`.
14. ⬜ `.pkg` installer (py2app bundle, postinstall model download, Gemma terms), plus a DMG wrapper.
15. ⬜ Wispr-style extras: custom dictionary, snippets, app-aware style.
16. ⬜ Languages (French and Spanish at minimum; ideally every language Whisper supports): a `language` setting (explicit code or `auto`), multilingual cleanup prompt and examples, the detected language in the JSON record, and eval cases per language. See "Languages" below for test results.
17. ⬜ Customization in the UI: choose icon, sounds, widget position/size, and shortcuts from the settings window.
18. ✅ MIT license, CONTRIBUTING guide, and CHANGELOG.

## Floating Widget

A transparent, non-activating panel centred just above the Dock on the screen with the focused window. It never steals focus.

| State | Appearance | Entered by |
|---|---|---|
| Idle | Tiny outlined pill | App running |
| Hover | Mic button + ◉ note button (36 pt tall, 12 pt above the Dock); tooltips "Dictate **fn**" / "New note **⌥M**" | Pointer over the pill |
| Hold | Compact black pill with live waveform | Hold `fn`, or long-press the mic |
| Hands-free | ✕ · waveform · ✓; tooltips "Cancel", "Finish and paste", "**space** to paste · **fn** to cancel" | Double-tap `fn`, or click the mic |
| Processing | Dim waveform + spinner | Release `fn` (hold), space/return (hands-free), or click ✓ |
| Cancelled | "Transcript cancelled · Undo" toast with a 5 s draining bar. Undo processes the recording; otherwise it is saved as cancelled and wiped when the bar runs out | Click ✕, press delete, or press `fn` during hands-free |
| Meeting | Outlined pill: small waveform + ■ stop (UI only; capture not built yet) | Click ◉ |
| Started by mistake? | Card with Discard / Keep | Stopping a meeting shorter than 10 s |
| Setup | "Downloading models NN%" with progress bar; "Model download failed · Retry" | Launch with a model missing |

Behaviour: soft system sounds (Tink / Pop / Bottle) on start, stop, and cancel; follows the focused window's screen (or the pointer's); the idle pill hides in fullscreen apps but recording states always show. SF Symbols for all icons.

## fn Gestures and Shortcuts

- **Hold** (≥ 0.3 s): push-to-talk. Recording starts on key-down so the first word isn't clipped; release finishes.
- **Tap** (< 0.3 s): discarded silently. A second press within 1 s of the first starts hands-free.
- **Press during hands-free:** cancel (Undo toast).
- **fn + another key** (fn+arrow, fn+F-key): a modifier combo; the recording is discarded.
- fn is ignored while processing, during a meeting, on the "Started by mistake?" card, and during setup.
- The 🌐/fn key also emits its own key event (keycode 179); macOS opens Emoji & Symbols from it, so it is swallowed with the fn flag.
- **Hands-free keys:** space, return, or keypad enter = finish and paste; delete or fn = cancel. **Undo toast:** delete = discard now.
- Keys are swallowed only in those states; presses with ⌘, ⌃, or ⌥ always pass through (⌘Space still opens Spotlight).

## Audio Capture

- `Recorder.start()` waits for any previous stop, wipes the buffer, builds a fresh resampler, and starts the engine (~140 ms). About 0.1 s at the start of each take is lost to device start-up.
- `Recorder.stop()` gates capture off instantly (no samples accepted afterwards), flushes the resampler tail, and stops the engine on a `mic-stop` daemon thread, so it never blocks the UI (~0.5 ms).
- If a stop hasn't finished within 1 s when the next recording starts, that engine is abandoned and a fresh one is built.
- The microphone runs only while recording, so the macOS mic indicator is honest.

## Secure Audio Handling

- Audio lives in one preallocated, mutable NumPy array (10 minutes at 16 kHz), never converted to immutable `bytes`.
- The buffer's pages are `mlock`ed so they can't be swapped to disk; `munlock` on close.
- After each recording the written region is zeroed in place and the wipe is verified.
- whisper.cpp receives the buffer view itself (no Python copy).
- Known limitation: CoreAudio's transient tap buffers and the resampler's small internal state are owned by those libraries; samples are copied out immediately.

## Transcription

- Model loads and warms up (Metal compile) in the background at launch, so the first dictation isn't slow.
- Clips under 0.3 s or with a peak under 0.01 are skipped: Whisper hallucinates text ("Thank you.") on silence.
- Annotations like `[BLANK_AUDIO]` and `(music)` are stripped.
- Runs on a worker thread; whisper.cpp releases the GIL, so the event tap and UI stay responsive.

## LLM Cleanup

- **Does:** removes fillers (um, uh, like, you know), stutters and repeated words; applies explicit self-corrections ("Tuesday, no wait, Wednesday" -> "Wednesday"); fixes punctuation and capitalization.
- **Never:** adds words, rephrases, answers, or obeys the dictation. "I mean" + detail is kept as a clarification; when unsure, it keeps the words.
- **Hard guarantee (code, not model):** the output is rejected and the raw transcript pasted if it contains *any* word the speaker didn't say (case, punctuation, apostrophes, and number words vs digits normalized), or keeps under 60% of the speaker's non-filler words (fillers excluded on both sides).
- **Model choice:** `tools/eval_cleanup.py` (27 cases). Gemma-3-4B: 0 invented, 0 lost, most conservative. Qwen3-4B-Instruct-2507 tied but half-applied a correction; Qwen2.5-3B invented words; Qwen2.5-1.5B missed corrections and obeyed "Translate this...".
- **Performance (M1 Pro):** ~550 ms cleanup; ~1.8 s end-to-end for a 5-6 s clip; Whisper + Gemma use ~3.5 GB RAM.
- **Shutdown:** the llama.cpp model is freed before exit on Quit and SIGTERM (its Metal backend asserts otherwise).
- **Setting:** `cleanup` (default on).

## First-Run Setup (mandatory)

On launch, if either required model (Whisper large-v3-turbo q5, Gemma-3-4B-it Q4_K_M) is missing, the widget enters SETUP: "Downloading models NN%" with a progress bar, and dictation (fn and clicks) is locked until both are downloaded (to a `.part` file) and SHA-256 verified. A failure shows "Model download failed · Retry". Once installed, both engines load and warm up in the background (~2-3 s).

## Recording Storage

- **Default:** every finished or cancelled dictation is saved to `voice-recordings/YYYY-MM-DD/` in the project folder (`~/Library/Application Support/Mispr_Flow/voice-recordings` once packaged), named by start time to the millisecond: `2026-09-30_12-28-33-123.wav` (16 kHz mono PCM) + `.json`.
- **JSON fields:** `id`, `started_at` / `ended_at` (ms precision, with timezone), `duration_s`, `status` (`pasted` / `cancelled`), `transcript`, `raw_transcript`, `words`, `recorded_in` (app, bundle id), `pasted_into` (app, bundle id, and for browsers `url` and `page_title`; `null` if cancelled), `model`, `cleanup` (model, applied, ms, rejection reason), `audio_file`.
- **Not saved:** fn taps, fn+key combos, clips under 0.3 s, silent clips, and anything in Incognito mode.
- **Possible upgrade:** encrypt recordings with a key in the macOS Keychain, so deleting the key crypto-shreds them (the only reliable "delete" on SSD/APFS).

## Meeting Notetaker (◉) — planned

Records a Zoom / Google Meet call, transcribes everyone with speaker labels, and writes a business-style summary.

- **Capture:** microphone ("You") + system audio (others) via ScreenCaptureKit; needs the Screen & System Audio Recording permission.
- **Transcription:** whisper.cpp in chunks for a live transcript; a diarization pass afterwards labels speakers.
- **Summary:** local LLM → overview, decisions, action items with owners, open questions.
- **Output:** `meeting-recordings/` in the project folder; audio follows the dictation rules (saved by default, never in Incognito).
- **Notes window (later):** My thoughts / Transcript / Summary tabs, plus "Ask anything about this meeting".
- **Guard:** very short meetings ask "Started by mistake?" (Discard / Keep). The UI for this already exists.

## Distribution

- **Format:** an unsigned `.pkg` (optionally wrapped in a DMG), built from a py2app bundle. Apple Silicon (M1+) only.
- **Models at install:** the postinstall script downloads Whisper (~0.57 GB) and Gemma (~2.5 GB), verifies SHA-256, and places them in `/Library/Application Support/Mispr_Flow/models` (installer scripts run as root). Installer.app shows only an indeterminate "Running package scripts" bar during this.
- **Build environment (found 2026-09-30):** Homebrew's Python and a locally compiled llama.cpp are stamped "macOS 26 minimum", so a DMG built from the dev venv would only run on macOS 26. The DMG must be built with a portable Python (python-build-standalone via `uv`, minimum macOS 11) and llama.cpp compiled with `MACOSX_DEPLOYMENT_TARGET=14.0`; numpy's wheels set the overall floor at **macOS 14 Sonoma**. The bundle also needs `NSMicrophoneUsageDescription`, `LSUIElement`, a bundle identifier, and the icon.
- **Startup safety net:** the app must check both `/Library/...` and `~/Library/...` for models (today it checks only `~/Library`: to do with the installer). Anything missing triggers the setup screen.
- **Signing:** unsigned for now (users choose "Open Anyway" in System Settings > Privacy & Security). Revisit Developer ID + notarization before a wide release.
- **Permissions caveat:** macOS ties Microphone/Accessibility/Input Monitoring grants to the signature; unsigned updates may need re-granting. Ad-hoc sign with a stable identifier to reduce this.
- **Licensing:** show Gemma's Terms of Use in the installer.

## Testing and Quality

- **Suite:** 769 unit tests (~14 s) + 10 opt-in integration tests (real Whisper, Gemma, microphone, and model checksums). `filterwarnings = error`.
- **Patterns:** dependency injection (clocks, engines, resamplers, lock path, model specs), inline daemon threads for deterministic async tests, spies for sounds and OS/library calls, boundary-value tables, specification tables for product decisions, golden snapshots of layout and rendering (31 files, reviewed visually), and fakes for AppKit objects.
- **Mutation score:** 97.6% overall; audio 95.5%. Remaining survivors are documented as equivalent mutants.
- **Reports:** `logs/2026-09-30_13-25-55_stresstest.md` (suite stress test) and `logs/2026-09-30_14-34-34_mic-deadlock-fix.md` (freeze diagnosis).
- **Tools:** `tools/stress_test.py`, `tools/mutation_test.py`, `tools/eval_cleanup.py`, `tools/render_states.py`.

## Known Issues and Tech Debt

- Mic start takes ~140 ms and the first ~0.1 s of each take is lost.
- ⌘V uses the ANSI V keycode; Dvorak/AZERTY layouts need a layout-aware mapping.
- `soxr` prints harmless nanobind "leaked function" notices at interpreter exit.
- Models under `/Library/Application Support` aren't checked yet (needed for the `.pkg`).
- The app still runs from source; an `.app` bundle and signing are pending.
- The meeting pill's waveform is simulated until meeting capture exists.
- Transcription is English-only today despite the multilingual model.

## Languages (planned)

Whisper large-v3-turbo is multilingual; the app currently forces English (`LANGUAGE = "en"` in `transcribe.py`). A test on 2026-09-30 with macOS TTS voices (Samantha, Thomas, Mónica) and `language="auto"`:

| Clip | Detected | Time (auto) | Time (forced `en`) | Transcript |
|---|---|---|---|---|
| English sentence | en | 1.96 s | 1.00 s | exact |
| English short ("Yes, sounds good.") | en | 1.94 s | 0.98 s | exact |
| French sentence | fr | 2.00 s | n/a | exact, accents correct |
| Spanish sentence | es | 2.03 s | n/a | exact, accents correct |
| French short ("D'accord, merci.") | fr | 2.24 s | n/a | exact |

Findings: detection was correct on every clip, but auto-detect roughly doubles transcription time (~1 s extra), since whisper.cpp runs a detection pass first. Plan:

- `language` setting: a fixed code (fastest) or `auto` (any language, ~1 s slower). The detected language comes from `whisper_full_lang_id`.
- Cleanup: Gemma-3-4B is multilingual. Add a "never translate; keep the speaker's language" rule and French/Spanish few-shot examples. Extend the guard: Unicode word tokens (currently `[a-z]`), accent-insensitive comparison, and French/Spanish fillers (euh, ben, bah, du coup / eh, este, pues, o sea) and number words.
- Tests: eval cases per language in `tools/eval_cleanup.py`, and integration tests with the French and Spanish voices.

## Branches and Releases

- `main`: merged, working code (via GitHub PRs).
- `build`: day-to-day development; merged into `main` through PRs.
- `planning`, `Rebranding`, `widget`, `dictation-complete`, `widgets-fn-record-complete`: milestone and feature branches (all merged).
- Tags: `v0.1-dictation` (end-to-end dictation), `v0.2-llm-cleanup` (LLM cleanup + guard).
