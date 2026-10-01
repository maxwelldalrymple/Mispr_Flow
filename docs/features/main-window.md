# The main window

A SwiftUI app (`macos/`). The Dock icon opens it; it hosts the Python engine in the background.

## Top bar

- **Auto-Enter (⏎)** and **Incognito** switches, each with a hover explanation.
- Your **profile photo**, which opens Settings → Profile.

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
