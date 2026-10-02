# `mispr/`: the Python engine

Runs dictation, the widget, voice commands and all the models. Start it alone with `.venv/bin/python -m mispr`, or let the app host it (`MISPR_HOSTED=1`, see [engine protocol](../docs/engine-protocol.md)).

| Module | What it does |
|---|---|
| `app.py` | Entry point: single-instance lock, menu bar, setup window, the hotkey monitor, and the host connection (commands from the Swift app) |
| `widget.py` | The floating pill: state machine (idle, hold, hands-free, processing, meeting…), drawing, mouse and keys, sounds and notices; dictation's paste/copy/Auto-Enter; the **app switcher** (`switch_key`, `_do_switch_command`) |
| `hotkey.py` | Quartz event tap: the dictation key (fn, a modifier side, or a key), the **switch key** (key, modifier side or combo), ⌥M, hands-free keys |
| `apps.py` | Voice commands: parsing, confident app matching, window layout, shortcuts, media/volume/mic, tab muting, seek, scroll, folder/file search (Spotlight, walk, Soundex), Finder control, permission checks |
| `control.py` | More of the Mac by voice: keys and shortcuts, typing, editing "that", window halves and desktops, system switches (dark mode, Wi-Fi, brightness, sound output), web searches, Shortcuts, "again", your own commands, the grid |
| `pointer.py` | Clicking by voice: what's on screen from the Accessibility API, closest-name matching, mouse clicks, drags, menu-bar extras |
| `overlay.py` | The numbers and grid overlay (a click-through window with numbered badges) |
| `sites.py` | The ~1,000 most visited sites (`assets/sites.txt`) for misheard site names and spoken web addresses |
| `terminal.py` | Terminal dictation: spoken syntax → shell, with a no-added-words check |
| `audio.py` | Mic capture into a locked (`mlock`), wipeable buffer |
| `transcribe.py` | whisper.cpp wrapper: text or timed segments; lazy loading |
| `cleanup.py` | Gemma cleanup with the no-invented-words guard; also summaries and answers (`complete`) |
| `meeting.py` | Meeting chunks: final text, live previews (own thread), speech detection (Silero), speaker diarization (TitaNet, `VoiceClusters`), gender (`GenderModel`), summaries, Q&A |
| `paste.py` | Paste with clipboard restore, typing (Incognito), copy, Return |
| `context.py` | Frontmost app, browser URL/title, "is a text box focused?" |
| `storage.py` | Saving dictations and commands (WAV and JSON) |
| `settings.py` | `settings.json` (shared with the app) |
| `models.py` | Model specs (pinned SHA-256), downloads, `python -m mispr.models` |
| `setup.py`, `onboarding.py` | Required model downloads; the setup window (5 steps, two permission pages) |
| `prompts.py` | The cleanup prompt the Prompts page edits |
| `host.py` | JSON lines to and from the app |
| `screens.py`, `draw.py`, `sounds.py`, `levels.py`, `threads.py` | Screen following, drawing helpers, sound cues, audio levels, daemon threads |
| `voice_gender.json` | The trained male/female weights for TitaNet fingerprints |
| `assets/` | Logo, app icon, menu-bar icon, sounds |

Guides: [docs/features/](../docs/features/). Tests: [tests/](../tests/README.md).
