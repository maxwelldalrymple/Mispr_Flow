# The main window

A SwiftUI app (`macos/`). The Dock icon opens it; it hosts the Python engine in the background.

## First-run tour

The first time the window opens after setup, an 8-step tour outlines each part and explains it, with a card showing "3 of 8" and **Back**, **Next** and **Skip tour**:

1. the dictation key;
2. history;
3. Auto-Enter and Incognito;
4. voice commands;
5. Insights;
6. meeting notes (New note);
7. Prompts;
8. Settings.

Finishing or skipping marks it done. Replay it from **Help → Show Tutorial**, or Settings → System → Tutorial. Code: `Views/Tutorial.swift` (`TourStep`, `TourOverlay`, `.tourSpot(_:)`).

## Top bar

- **Auto-Enter (⏎)** and **Incognito** switches, each with a hover explanation.
- Your **profile photo**, which opens Settings → Profile.

## Voice Commands page

The second page: every voice command, searchable ("tab", "click", "volume"), by category chips, with your keys and what can never happen by voice. A test parses every phrase on it with the real engine, so it always matches what the app does.

## Pages

- **Home:**
  - a greeting and your dictation key;
  - **history** with tabs **Dictation | Commands**, search, playback, copy and delete;
  - side cards: stats (words, wpm, streak), **Shortcuts**, and **Voice commands** (the most useful ones, or a link to set up a switch key).
- **Insights:** pace, streaks, time saved, where your words go, your voice profile, and many fun facts, from your saved dictations.
- **Notetaker:** see [notetaker.md](notetaker.md).
- **Prompts:** edit the cleanup model's instructions, rules and examples, then **Try it** live. They're saved to `prompts.json` and used by the engine at once.
- **Settings** (a modal):
  - **Profile:** name, nickname, photo, and 6 colour themes plus appearance.
  - **General:** dictation key, app switcher key and nicknames, microphone, language, cleanup.
  - **System:** launch at login, sounds, Setup guide.
  - **Privacy.**

## Data

- Settings: `~/Library/Application Support/Mispr_Flow/settings.json`, shared with the engine.
- Dictations: `voice-recordings/`. Meetings: `meeting-recordings/`.

Sample-data tools (`tools/make_sample_dictations.py`, `make_sample_meetings.py`) fill these for screenshots and testing.

## Automatic updates

From v1.1.0, the DMG app keeps itself up to date (**Settings → System**):

- **Automatic updates** (on by default): about 5 times a day, and a minute after launch, it asks GitHub for its releases.
- **Stable and beta:** stable releases install themselves. Betas (GitHub pre-releases, like `1.3.0-beta.1`) are only offered: **Settings → System** shows "Beta … available" with **Install beta**. A beta is only shown while it's newer than your version and every stable release, and the next stable release replaces it automatically.
- A newer version is downloaded and its **signature checked**: every release DMG is signed (Ed25519, over its SHA-256) with a key that stays on the maintainer's Mac. A file that doesn't match is deleted, never installed.
- It installs only after **a minute without dictating or a meeting**: the app quits, the new copy takes its place, and it opens again with an "Updated to 1.x · What's new" note.
- Releases are signed with the same certificate each time, so **permissions carry over**.
- **Check now** shows the status ("Up to date (1.1.0)", "Downloading 1.2.0…"). It works with automatic updates off.
- A copy that can't replace itself says why: a development build, an app run from the DMG or Downloads ("Move Mispr Flow to Applications"), or a folder you can't write to.

