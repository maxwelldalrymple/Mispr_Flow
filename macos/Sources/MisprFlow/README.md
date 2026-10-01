# `MisprFlow`: the app

| File | What |
|---|---|
| `main.swift` | Entry point; dev flags `--detect`, `--segment file.wav`, `--record-test` |
| `AppDelegate.swift` | Menus, the main window, the note side window, launch and quit |
| `AppModel.swift` | The app's state: engine, settings and keys, nicknames, recordings, stats, meetings, contacts, notes and people actions (delete, rename, remove, save contact), profile |
| `Profile.swift` | Profile photo, theme and appearance |
| `MeetingRecorder.swift` | Mic (AVAudioEngine) + system audio (ScreenCaptureKit), `Resampler` to 16 kHz, `EchoGate`, segmenters, `StreamingWAV` files |
| `SystemProbe.swift` | Running apps, window titles, mic in use, and `WindowArranger` (split screen with a call window) |
| `DevTools.swift` | Reports for the dev flags |
| `Views/` | All the screens: see [Views/README.md](Views/README.md) |

Tests: `macos/Tests/MisprFlowTests/`.
