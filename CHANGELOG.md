# Changelog

All notable changes to Mispr Flow. Dates are 2026.

## Oct 2: v1.2.0: control your whole Mac by voice

- **Click anything**, in any app: "click Sign in", double / right click, hover, "click" where the mouse is. Read from the app (Accessibility), no OCR. The closest name wins; several matches get **numbers** ("show numbers", then "7"). Plus a **grid** for unnamed spots, **drag**, and scrolling a named area.
- **Keyboard:** "press enter", "press command shift t", "down 3", "type …" (exact text), and select all / copy / paste / undo / redo / save.
- **Editing:** "scratch that", "select that", "capitalize that", "new line", "delete last word", line and word moves.
- **Windows and desktops:** halves, thirds, corners, center, other screen; Mission Control, show desktop, app windows; next / previous desktop.
- **Switches:** dark mode, brightness, Wi-Fi, sound output ("use AirPods"), Control Center, Notification Center, Launchpad, Spotlight; Mispr Flow's modes ("auto enter on", "incognito mode", "sounds off").
- **The web:** Google, YouTube, Amazon and other searches; "go to apple.com"; find on page.
- **Power tools:** "run shortcut …", "again" / "do that 3 times", your own commands (Settings → General).
- **Voice Commands page:** every command, searchable, checked against the parser by a test.
- **Updates: stable and beta.** Stable releases install themselves; betas are offered in Settings only. `tools/release.sh` publishes either.
- **Long dictations as they're processed** is now a switch, off by default.
- **Fixed:** "YouTube tab", "close tab", "new tab" and other commands in Whisper's hint were dropped as prompt echoes (1.1.0–1.1.1).

## Oct 2: v1.1.1

- The first release delivered by automatic update: proves 1.1.0 finds, verifies and installs a new version by itself. No other changes.

## Oct 2: v1.1.0

- **Automatic updates** (DMG app): checks GitHub ~5×/day, signed downloads only, installs when you're idle, keeps permissions; Settings switch and Check now.
- **Auto-Enter key** ⌃⌥↩ (changeable); ⌘Return on LinkedIn, Gmail and Outlook web, where Return is a new line.
- **No phantom text:** a speech check (Silero, volume-evened) drops clicks and silence; Whisper's noise phrases and sound labels ("*Drums*") removed.
- **Fillers** ("uhh…", "um,") always removed; the cleanup guard counts them as fillers.
- **Long dictations** typed in piece by piece while processing; Auto-Enter waits for the last piece.
- **Voice commands:**
  - "close tab" fixed (heard as "Closed tab.");
  - a tab by its site ("GitHub tab", "YouTube tab 2"), with misheard names assumed and unopened sites opened;
  - screenshots, screen recording, sleep, lock, log out / restart / shut down (macOS confirms);
  - any menu item by name, never ones that delete for good.
- **Site names:** the 1,000 most visited sites (`mispr/assets/sites.txt`) for misheard names in tab commands and spoken web addresses; Whisper primed with ChatGPT, GitHub, YouTube…
- **Release builds** signed with a fixed certificate, plus an update signature (`.sig`).

## Oct 2: v1.0.0

- First DMG release (`tools/build_dmg.sh`): bundled Python 3.13, macOS 14+, no personal data (checked by the build). SHA-256 in the README.
- Gemma Terms of Use on the setup Models page. 146 screenshots in `docs/screenshots/`.

## Oct 1: Documentation (branch `documentation`)

- Feature guides (`docs/features/`), engine protocol, models, testing.
- A README in every folder.
- A knowledge base (`knowledge-base/`) for bringing an AI assistant up to speed.

## Oct 1: Tests, meetings, voice commands (PR #16)

- **Test audit:** every UI and engine function tested, with a test catalogue in `logs/`.
- **Meeting notes:**
  - TitaNet speaker diarization: a new person only after two matching sentences; lookalikes merged.
  - Gender from fingerprint plus pitch.
  - Echo gate on the mic, plus echo removal from text.
  - Silero click filtering; fast `base.en` previews on their own thread.
  - Save / Discard / Keep editing.
- **Notetaker:** delete one or many notes; rename, merge or remove people; contact cards.
- **Voice commands (app switcher):**
  - switch key or combo;
  - apps and windows (close, minimize, expand, quit, side by side, percent);
  - tabs and browser shortcuts;
  - media, skip, volume, mute mic and tab;
  - scrolling;
  - open folders and files (Spotlight, sound-alike names);
  - nicknames;
  - safe matching;
  - Commands history with real names.
- **Dictation:** Auto-Enter with badge and chime (works in terminals); terminal mode (spoken syntax → shell, never adds commands); browser text-box recheck.
- **Setup:** two permission pages (required; optional: System Audio, Full Disk Access, Control Finder).
- **Home:** Voice commands card.

## Unreleased

### Main window (SwiftUI) and meeting notes — branch `ui`

- **Mispr Flow.app:** a SwiftUI app (`macos/`) that runs the Python engine in the background (JSON lines over stdin/stdout), restarts it if it crashes, and quits with it. `tools/build_app.sh` builds and signs it; with the local certificate (`tools/make_signing_cert.sh`, trusted via `tools/trust_signing_cert.sh`) macOS keeps its permissions across rebuilds.
- **Pages:** Home (history by day, search, play, copy, delete; stats), Insights (WPM vs typing, cleanup fixes, usage by kind of app, streak calendar, time saved, week over week, hours and weekdays, top apps, pace, fun facts; Your voice: style, tone, habits, word cloud), Notetaker, Prompts, and Settings (Profile with six color themes, General with a click-to-set dictation key, System, Data and Privacy).
- **Prompts page:** the cleanup system prompt, your own rules, and the examples are editable, with a Try it box and a switch for the no-invented-words guard.
- **Incognito:** a switch in the window's corner; purple outline on the widget and the window while on; text is typed instead of pasted and is never copied.
- **Any dictation key:** fn, one side of a modifier, or any other key.
- **Meeting notes:** ⌥M or the widget's ◉ opens a side panel and records mic + system audio; live text while people talk, final lines at pauses; speakers grouped by voice and labelled Male/Female/Person N (renamable); Stop saves the note, writes a summary and title, and Resume continues it; Ask anything / What did I miss?; search; Share; split screen with the call window. Meeting type (Zoom, Meet, Teams, FaceTime, Webex, Slack, in person) is detected automatically.
- **Notetaker:** past notes (summary, transcript, per-meeting insights, your notes), overall insights, and People: click one person or several to see the meetings you shared, talk share, topics, and their action items.
- **Fixes:** the app connects to the engine even while Gemma loads (a private stdout copy); smooth history scrolling; paste is skipped (copied instead) when a native app has no text box focused; windows never outgrow the screen; quiet continuous meeting audio keeps transcribing.
- **Sample data:** `tools/make_sample_meetings.py` and `tools/make_sample_dictations.py` (with `--remove`).
- **Tests:** 958 Python unit tests, 90 Swift tests.

### Earlier on `build`

- **Dock icon:** Mispr Flow is now a regular Dock app with the logo as its tile (it was menu-bar only), named "Mispr Flow" in the menu bar and ⌘-Tab, with an app menu (About, Setup Guide…, Hide, Quit). Clicking the Dock icon opens the setup window until the main window exists.
- **Original sound cues** replace the macOS system sounds (Tink, Pop, Bottle). Ten cues, all synthesized from scratch by `tools/make_sounds.py` into `mispr/assets/sounds/`; a test checks the shipped WAVs match the generator byte for byte. Levels are baked into the files, so they play at full volume.
- **Every sound is hooked up** to the events that exist today: start, stop, lock (double-tap into hands-free), paste (text landed), cancel, alert (recorded but no words came out), error (mic won't open, no text box, or model download failed), success (models installed, or a permission granted in setup), and achievement (setup finished). `notification` is reserved for the main window.
- **No text box, no paste:** before pasting, Accessibility is asked what has keyboard focus. If it's clearly not a text input (Finder, the desktop, a web page with nothing focused), Mispr skips ⌘V, leaves the text on the clipboard, plays the error sound, and shows "No text box · Copied to clipboard" for 4 s. The recording is saved with status `copied`. When an app won't say (e.g. Electron apps like VS Code or Slack), it pastes as before.
- **Mic name on first dictation:** "Using Built-in mic (recommended)" or "Using <device>" above the widget for 3 s, like Wispr Flow. The pill is now a general notice used by the copied-to-clipboard message too.
- **App icon** redrawn on the macOS icon grid (824 px rounded tile with a soft shadow); `tools/make_icon.py` rebuilds it from `icon.png`.
- Tests: 841 unit tests (+72), 44 golden files.

## Sep 30: Setup window and rename

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
