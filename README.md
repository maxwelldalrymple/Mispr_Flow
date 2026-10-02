<p align="center"><img src="mispr/assets/icon.png" width="160" alt="Mispr Flow"></p>

# Mispr Flow

Private, fully local voice control for macOS. Hold **fn**, speak, and clean, punctuated text appears in whatever app you're typing in. Hold your **switch key** and say "Chrome beside VS Code", "new tab", "pause" or "open folder Projects". Take **meeting notes** that know who said what. Speech recognition, cleanup, speaker detection and summaries all run on your Mac: your voice never leaves it.

An open clone of the Wispr Flow desktop experience, without the cloud.

<p align="center"><img src="docs/screenshots/main-window/home_dictation-history_classic-dark.png" width="820" alt="Mispr Flow's Home page: dictation history, stats, shortcuts and voice commands"></p>

**macOS · Apple Silicon · 100% on-device · free · [MIT licensed](LICENSE)**

```bash
python3.13 -m venv .venv && .venv/bin/pip install cmake
CMAKE_ARGS="-DGGML_METAL=on" .venv/bin/pip install -r requirements.txt
.venv/bin/python -m mispr        # then hold fn and speak
```

## Screenshots

| | |
|---|---|
| <img src="docs/screenshots/note-window/note_2-recording-live-transcript_classic-dark.png" width="300" alt="Live meeting transcript with speakers told apart"> | <img src="docs/screenshots/main-window/notetaker_meeting-detail_summary-tab_classic-light.png" width="480" alt="A saved meeting's summary"> |
| **Meeting notes:** a live transcript that tells speakers apart | **A saved note:** summary, decisions and action items |
| <img src="docs/screenshots/tutorial/tutorial_step-3-of-8_auto-enter-and-incognito_classic-light.png" width="480" alt="First-run tutorial, step 3"> | <img src="docs/screenshots/main-window/insights_overview_classic-dark.png" width="480" alt="Insights page"> |
| **First-run tutorial:** 8 steps that point out each area | **Insights:** words, speed and streaks |
| <img src="docs/screenshots/themes/main-window_home_sunset-light.png" width="480" alt="Sunset theme, light"> | <img src="docs/screenshots/themes/main-window_home_ocean-dark.png" width="480" alt="Ocean theme, dark"> |
| **Six themes**, each in light and dark (Sunset light) | (Ocean dark) |
| <img src="docs/screenshots/setup-window/setup-window_welcome_system-light.png" width="420" alt="Setup window"> | <img src="docs/screenshots/settings/settings_general-section_classic-dark.png" width="480" alt="Settings"> |
| **Guided setup:** permissions and model downloads | **Settings:** keys, sounds, nicknames, themes |

All 146 screenshots (every window, state, theme and mode) are in [docs/screenshots/](docs/screenshots/README.md).

## Download

**[Mispr-Flow-1.1.1.dmg](https://github.com/maxwelldalrymple/Mispr_Flow/releases/tag/v1.1.1)** (87 MB) for Apple Silicon Macs on macOS 14 or newer. Models (about 3.1 GB) are downloaded during setup. From 1.1.0 on, the app updates itself (Settings → System → Automatic updates).

**Verify it** before opening. The SHA-256 must match exactly:

```
0c83e67e68636e268d764581c17e67e25902975177d7efd64124822f833fdee2  Mispr-Flow-1.1.1.dmg
```

```bash
shasum -a 256 ~/Downloads/Mispr-Flow-1.1.1.dmg
```

**First open:** the app isn't signed with an Apple Developer ID, so macOS blocks a double-click. Drag it to Applications, then right-click it and choose **Open** (or System Settings → Privacy & Security → **Open Anyway**). The DMG holds only the app: it creates its own folders in `~/Library` on first run. Build it yourself with `tools/build_dmg.sh`.

**Updates are signed:** each release also has a `.sig` file, an Ed25519 signature over the DMG's SHA-256. The app installs an update only if it matches the public key in `macos/Sources/MisprCore/Update.swift`.

## Why

1. **Open source.** MIT licensed. Every line is readable, auditable and changeable: the hotkey, the audio pipeline, the prompts, the safety checks.
2. **Free.** No subscription, no account. The models are free downloads.
3. **Your voice stays on your Mac.** Cloud dictation sends your audio to someone's servers. Mispr Flow transcribes, cleans up and summarizes on-device.
4. **Yours to change.** Icons, sounds, widget, shortcuts, models and the cleanup prompt (edit it live on the Prompts page).

## Features

| | | Guide |
|---|---|---|
| **Dictation** | Hold or double-tap fn (or any key you pick). Local Whisper plus a cleanup model that never invents words. Pastes into the focused text box, or copies if there isn't one. Incognito saves nothing. **Auto-Enter** sends what you said (⌃⌥↩ toggles it). Clicks and silence never become text; long dictations appear as they're processed. **Terminal mode** turns "ls flag a" into `ls -a` | [dictation](docs/features/dictation.md) |
| **Voice commands** | Hold a switch key (a key or a combo like ⌃⌥) and say:<br>• switch, close, minimize, expand, quit<br>• "Chrome beside VS Code", "Chrome 80%"<br>• "click Sign in", "show numbers", "show grid", drag, double/right click: anything on screen, any app<br>• "press command shift t", "type …", "scratch that", "left half", "next desktop"<br>• "dark mode on", "use AirPods", "google …", "run shortcut …", "again", your own commands<br>• new tab, reload, zoom, "GitHub tab", "YouTube tab 2"<br>• screenshot, screen recording, sleep, lock, shut down (confirmed)<br>• any menu item: "save", "show sidebar"<br>• pause, skip 30 seconds, volume, mute mic/tab<br>• scroll<br>• "open folder Projects"<br>• nicknames<br>It never opens an app on a guess, and keeps a Commands history | [voice commands](docs/features/voice-commands.md) |
| **Meeting notes** | ⌥M records you and the call at once:<br>• live text, speakers told apart (TitaNet), male/female labels<br>• speaker echo and clicks filtered out<br>• local summary and Q&A<br>• save only when you choose | [meeting notes](docs/features/meeting-notes.md) |
| **Notetaker and People** | Past notes with search, insights and deleting (one or many); people with rename, merge and contact cards | [notetaker](docs/features/notetaker.md) |
| **Main window** | Home (history: Dictation and Commands), Insights, Notetaker, Prompts, Settings (profile, 6 themes, keys, sounds) | [main window](docs/features/main-window.md) |
| **Setup** | A guided window: required permissions, optional features, model downloads | [setup and permissions](docs/features/setup-and-permissions.md) |
| **Updates** | The DMG app updates itself from GitHub Releases (signed, installs when idle; can be turned off) | [main window](docs/features/main-window.md#automatic-updates) |
| **Privacy** | No network use except one-time, hash-checked model downloads and the update check | [privacy](docs/features/privacy.md) |

End to end, dictated text appears about 1.8 s after you stop talking.

## Requirements

- Apple Silicon (M1 or newer). Developed on an M1 Pro, 16 GB, macOS 26.
- About 3.1 GB of disk for the dictation models. Meeting notes add about 250 MB (downloaded on first use). All are SHA-256 verified.
- About 3.5 GB of RAM while running.
- Python 3.13 and Xcode's Swift toolchain (to run from source).
- Permissions, asked for in setup with an explanation:
  - **Required:** Microphone, Accessibility.
  - **Optional:** Screen & System Audio (meeting notes), Full Disk Access (open folder), Control Finder.

## Install and run

```bash
python3.13 -m venv .venv
.venv/bin/pip install cmake
CMAKE_ARGS="-DGGML_METAL=on" .venv/bin/pip install -r requirements.txt
tools/make_signing_cert.sh      # once: local signing, so permissions survive rebuilds
tools/trust_signing_cert.sh     # once: asks for your password
tools/build_app.sh --open       # builds and opens Mispr Flow.app
```

The app runs this checkout's Python engine in the background. Setup walks you through permissions and downloads the models. More: [getting started](docs/getting-started.md), [troubleshooting](docs/troubleshooting.md).

## Settings

In the app (Settings), or `~/Library/Application Support/Mispr_Flow/settings.json`:

| Key | Default | Meaning |
|---|---|---|
| `incognito` | `false` | Save nothing; type instead of paste |
| `auto_enter` | `false` | Press Return after dictated text is pasted (also in terminals; ⌘Return on LinkedIn, Gmail, Outlook) |
| `auto_enter_hotkey` | ⌃⌥↩ | The key that turns Auto-Enter on/off; `null` = off |
| `auto_update` | `true` | Check GitHub for a new version ~5×/day and install stable ones when idle (betas are only offered) |
| `live_long_dictations` | `false` | Type long dictations in piece by piece while processing |
| `custom_commands` | `[]` | Your own voice commands: `[{"say": "sign off", "type": "Best, Alex", "keys": "enter"}]` |
| `cleanup` | `true` | `false` pastes raw Whisper text |
| `sounds` | `true` | Sound cues |
| `hotkey` | fn | The dictation key: `{"kind": "fn" \| "modifier" \| "key", "keycode", "label"}` |
| `switch_hotkey` | off | The voice command key; also `{"kind": "combo", "mods": [...], "keycode": null}` |
| `app_nicknames` | `{}` | Spoken nicknames: `{"c": "Google Chrome"}` |
| `onboarded` | `false` | Setup finished |

## Where things live

| What | Where |
|---|---|
| Models | `~/Library/Application Support/Mispr_Flow/models/` |
| Settings, prompts | `~/Library/Application Support/Mispr_Flow/` |
| Dictations and commands | `voice-recordings/YYYY-MM-DD/` (WAV + JSON, gitignored) |
| Meeting notes, contacts | `meeting-recordings/` (gitignored) |
| Engine log | `~/Library/Logs/Mispr Flow/engine.log` |
| Change and test reports | [logs/](logs/README.md) |

## Testing

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest          # 1217 Python tests, ~13 s
cd macos && swift test              # 287 Swift tests
```

Every function has tests, and Python line coverage is 96%. Tests never touch the real mic, clipboard, keyboard, models or your files. See [testing](docs/testing.md) and the latest [test catalog](logs/README.md).

## Documentation

- **Features:** [dictation](docs/features/dictation.md) · [voice commands](docs/features/voice-commands.md) · [meeting notes](docs/features/meeting-notes.md) · [notetaker](docs/features/notetaker.md) · [main window](docs/features/main-window.md) · [setup](docs/features/setup-and-permissions.md) · [privacy](docs/features/privacy.md)
- **How it works:** [architecture](docs/architecture.md) · [engine ↔ app protocol](docs/engine-protocol.md) · [models](docs/models.md) · [data formats](docs/data-formats.md) · [testing](docs/testing.md) · [every test](docs/tests/README.md) · [development](docs/development.md)
- **Code:** [mispr/](mispr/README.md) ([assets](mispr/assets/README.md)) · [macos/](macos/README.md) ([MisprCore](macos/Sources/MisprCore/README.md), [MisprFlow](macos/Sources/MisprFlow/README.md), [Views](macos/Sources/MisprFlow/Views/README.md), [Swift tests](macos/Tests/README.md)) · [tests/](tests/README.md) ([golden](tests/golden/README.md)) · [tools/](tools/README.md) · [logs/](logs/README.md) · [docs/](docs/README.md)
- **Help:** [getting started](docs/getting-started.md) · [troubleshooting](docs/troubleshooting.md) · [contributing](CONTRIBUTING.md) · [changelog](CHANGELOG.md) · [plan and roadmap](plan.md)
- **Knowledge base**, to bring an AI assistant up to speed on everything, including the full chat history: [knowledge-base/](knowledge-base/README.md) (paste [ALL-IN-ONE.md](knowledge-base/ALL-IN-ONE.md))

## Status

Dictation, voice commands, the main window and meeting notes all work, as a downloadable app (see [Download](#download)).

**Next:**
- languages;
- a dictionary and snippets;
- a signed and notarized build.

See [plan.md](plan.md).

## License

Mispr Flow's code is [MIT licensed](LICENSE). Models are downloaded, not included:
- Whisper: MIT.
- Gemma: Google's Gemma Terms of Use.
- TitaNet: NVIDIA, CC BY 4.0.
- Silero VAD: MIT.

The gender weights were trained on the AMI Meeting Corpus and LibriSpeech (both CC BY 4.0). Mispr Flow is an independent project, not affiliated with Wispr Flow.
