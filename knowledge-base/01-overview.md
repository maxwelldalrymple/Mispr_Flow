# 1. Project overview

**Mispr Flow** is a free, open-source (MIT), fully local macOS clone of Wispr Flow, by Maxwell Dalrymple (GitHub `maxwelldalrymple/Mispr_Flow`). Everything (speech recognition, text cleanup, speaker detection, summaries) runs on the Mac. The only network use is one-time, hash-checked model downloads.

## What it does

1. **Dictation:**
   - Hold `fn` (or any chosen key), speak, release; double-tap for hands-free.
   - Whisper transcribes, Gemma cleans up (never inventing words), and the text is pasted into the focused text box, or copied if there's none.
   - Incognito saves nothing and types instead of pasting.
   - Auto-Enter presses Return after.
   - Terminal mode turns spoken syntax into shell commands.
2. **Voice commands ("app switcher"):**
   - Hold a switch key (key, modifier side, or combo) and say a command:
     - switch, close, minimize, expand or quit apps;
     - side-by-side and percent layouts;
     - tab and browser shortcuts;
     - play/pause, skip seconds, volume, mute mic/tab;
     - scroll;
     - open folders and files;
     - nicknames.
   - Commands are saved to a Commands history with the real names.
3. **Meeting notes:**
   - ⌥M opens a side panel that records the mic ("You") and system audio (the call) together.
   - Live text, with speakers told apart (TitaNet fingerprints) and labelled Male/Female/Person N.
   - Echo and clicks are filtered.
   - Summary and Q&A run locally. Notes are saved only when you press Save.
4. **Main window (SwiftUI):** Home (history: Dictation | Commands, stats, shortcuts, voice commands), Insights, Notetaker (notes, People with contact cards, insights), Prompts (edit the cleanup prompt live), Settings (profile, 6 themes, keys, nicknames, sounds).
5. **Setup window:** Welcome → Allow access (Microphone, Accessibility) → Optional features (System Audio, Full Disk Access, Control Finder) → Models → Ready.

## Architecture in one paragraph

Two processes:
- **`Mispr Flow.app`** (Swift package `macos/`, targets `MisprCore` and `MisprFlow`): the windows, the meeting recorder (AVAudioEngine and ScreenCaptureKit) and the echo gate.
- **The Python engine** (`mispr/`, PyObjC): the floating widget, the global hotkeys (Quartz event tap), dictation, voice commands and all models (pywhispercpp, llama-cpp-python, sherpa-onnx).

The app hosts the engine (`MISPR_HOSTED=1`). They talk in JSON lines over stdin/stdout (engine events are prefixed `@mispr `) and share `~/Library/Application Support/Mispr_Flow/settings.json`.

## Models

| Model | Size | Used for |
|---|---|---|
| Whisper large-v3-turbo q5_0 | 574 MB | dictation and final meeting text |
| Gemma-3-4B Q4_K_M | 2.49 GB | cleanup, terminal mode, summaries, Q&A |
| Whisper base.en | 148 MB | live meeting previews |
| NVIDIA TitaNet-large | 101 MB | speaker fingerprints |
| Silero VAD | 0.6 MB | speech vs clicks |
| `voice_gender.json` | 192 weights, trained here | male/female |

## Key paths

| Path | What |
|---|---|
| `mispr/` | engine |
| `macos/` | app |
| `tests/` | Python tests: 1217 |
| `macos/Tests/` | Swift tests: 287 |
| `tools/` | build, signing, sample data, test catalogue |
| `docs/` | guides |
| `logs/` | one timestamped report per change, with real results |
| `voice-recordings/`, `meeting-recordings/` | user data, gitignored |
| `~/Library/Logs/Mispr Flow/engine.log` | engine log |
| `build/Mispr Flow.app` | the built app (`tools/build_app.sh`) |

## State at the end of this history (2026-10-01)

- `main` has everything (PR #16 merged).
- The `documentation` branch holds the docs and this knowledge base.
- All tests pass.
- **Next:** the first-run tutorial and a security/network audit; then languages, a dictionary/snippets, and an installable build for other Macs.
