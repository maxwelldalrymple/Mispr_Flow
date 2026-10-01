# `MisprCore`: the app's testable logic (no UI)

| File | What |
|---|---|
| `Engine.swift` | Starts, watches and restarts the Python engine process; sends commands; publishes events (`hello`, `saved`, meeting events, `settings_changed`) |
| `EngineProtocol.swift` | `EngineEvent` (parsing `@mispr` JSON lines) and `EngineCommand` (see [the protocol](../../../docs/engine-protocol.md)) |
| `SettingsFile.swift` | Reads and writes `settings.json`, keeping unknown keys: booleans, the dictation key, the switch key (`null` = off), nicknames |
| `DictationKey.swift` | A shortcut: `fn`, a modifier side, a key, or a `combo` of modifiers (± key); labels like "⌃⌥S"; JSON in and out |
| `Recording.swift` | A saved dictation or command (`Status`: pasted/copied/cancelled/command, `isDictation`); `RecordingStore` loads and deletes them |
| `Stats.swift` | Insights: words, pace, streaks, time saved, where words go, voice profile, fun facts (dictation only) |
| `Meeting.swift` | A meeting note and its summary; `MeetingStore` (load, delete, rename person everywhere, remove person); `Contact` and `ContactBook`; `MeetingInsights`, `MeetingsOverview`, `PeopleIndex` |
| `LiveMeeting.swift` | `Segmenter` (cuts audio at pauses), `WAV`, `Echo` (text-level echo removal), `LiveTranscript` (lines, live partials, labels "Male 1"…, merges, the saved meeting) |
| `EchoGate.swift` | Silences the call coming back in through the mic: finds the echo delay, learns the leak, 3× margin, 160 ms hangover, 0.3 s hold |
| `MeetingSource.swift` | Detects the kind of meeting (Zoom, Meet, Teams, FaceTime, Webex, Slack huddle, in person) from running apps and window titles |
| `PromptsFile.swift` | The Prompts page's draft (`prompts.json`) |
| `ProfileInfo.swift` | Name and nickname rules (the greeting) |

Tests: `macos/Tests/MisprCoreTests/`.
