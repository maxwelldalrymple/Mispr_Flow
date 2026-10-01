# Testing

**Status at the end of the documentation branch:**
- Python: **1217 passed**, 10 skipped. The skipped ones are opt-in integration tests.
- Swift: **287 / 287**.
- Every function is covered. Python line coverage is 96%.
- **Every test, with what it checks, file by file:** [docs/tests/](tests/README.md). The same list as one file: [logs/2026-10-01_19-14-46_test-catalog.md](../logs/2026-10-01_19-14-46_test-catalog.md). Regenerate both with `python tools/test_catalog.py`.

## Running

```bash
.venv/bin/python -m pytest                           # Python, ~13 s
cd macos && swift test                               # Swift, ~70 s
.venv/bin/python -m pytest tests/test_apps.py        # one file
MISPR_INTEGRATION=1 .venv/bin/python -m pytest tests/test_integration.py   # real models and mic
UPDATE_GOLDEN=1 .venv/bin/python -m pytest           # after an intentional visual change; then review tests/golden/
```

During development, run only the tests that cover a change. Run the full suite when a change cuts across modules.

## Rules

- Tests never touch the real mic, clipboard, keyboard, models, recordings or settings: those are faked or redirected to temp folders (`tests/conftest.py`, `macos/Tests/MisprFlowTests/Helpers.swift`).
- **Any warning fails the run.**
- Things that would change the user's Mac (moving windows, quitting apps, pressing keys) are tested with fakes, or against a process that doesn't exist.
- **Golden files** (`tests/golden/`) pin the widget's layout and look, and the setup window's pages, pixel for pixel.

## Python (`tests/`)

| File | Covers |
|---|---|
| `test_widget.py` | The widget's state machine, gestures, paste/copy/type, sounds, notices, Auto-Enter (badge, chime, terminals), app switcher commands end to end, Commands history, terminal dictation, Incognito |
| `test_apps.py` | Command parsing (apps, windows, tabs, sound, seek, scroll, folders, quit), confident matching, folder search (Spotlight, walk, sound-alikes), Finder/permission helpers |
| `test_terminal.py` | Spoken syntax → shell; never adding commands |
| `test_meeting.py` | Meeting chunks, speech detection, diarization rules, gender, previews, summaries, Q&A |
| `test_hotkey.py` | The event tap: dictation key, switch key/combos, ⌥M, hands-free keys |
| `test_context_paste.py` | Text-box detection, paste/copy/type, Return and media keys |
| `test_onboarding.py` | Setup flow, permissions (required and optional pages), golden images |
| `test_cleanup.py`, `test_prompts.py` | The cleanup model wrapper and its no-invented-words guard; the Prompts file |
| `test_transcribe.py`, `test_audio.py` | Whisper wrapper (timed segments, lazy load); mic capture and wiping |
| `test_storage.py`, `test_settings_models_setup.py` | Saved recordings; settings; model specs and downloads |
| `test_host.py`, `test_entrypoints.py`, `test_threads.py`, `test_draw.py`, `test_screens_sounds_app.py` | The app protocol, entry points, threads, drawing, screens, sounds |
| `test_integration.py` | Opt-in: real models and mic |

## Swift (`macos/Tests/`)

| File | Covers |
|---|---|
| `MisprCoreTests/CoreTests.swift` | Engine protocol, recordings and stats, meetings and the store (delete, rename, remove person, contacts), live transcript, echo text removal, `EchoGate`, speaker merges, switch keys and combos, command history |
| `MisprCoreTests/EngineProcessTests.swift` | The engine as a real child process (stand-in script) |
| `MisprFlowTests/NoteModelTests.swift` | A meeting note from start to saved summary: save/discard/close questions, resume, merges |
| `MisprFlowTests/AppModelTests.swift` | Settings, keys, nicknames, notes and people actions |
| `MisprFlowTests/RenderTests.swift` | Every page, tab, theme and component drawn offscreen and checked non-blank |
| `MisprFlowTests/ViewLogicTests.swift` | Key picking (including combos), wording, layouts |
| `MisprFlowTests/SystemTests.swift`, `RemainingTests.swift` | Recorder parts, window behaviour, app shell |

## Quality tools (`tools/`)

- `stress_test.py`: repeated, random-order and parallel runs.
- `mutation_test.py`: plants bugs to check the tests catch them (last score 97.6%).
- `eval_cleanup.py`: scores the cleanup model.
