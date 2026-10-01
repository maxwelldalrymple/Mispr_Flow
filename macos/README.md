# `macos/`: the SwiftUI app

A Swift package (`Package.swift`) with:

| Target | What |
|---|---|
| `MisprCore` | Testable logic with no UI: the engine process and protocol, settings file and keys (including combos), recordings and stats, meetings and the store (delete, rename, contacts), the live transcript (with echo text removal), `EchoGate` (mic echo silencing), meeting detection |
| `MisprFlow` | The app: `AppDelegate`, `AppModel`, `MeetingRecorder` (mic + ScreenCaptureKit), `SystemProbe`, `DevTools`, and the views (`Views/`: Home, Insights, Notetaker, People, Prompts, Settings, the note side panel, theme) |
| `MisprCoreTests`, `MisprFlowTests` | XCTest suites (287 tests) |

## Build and run

```bash
tools/make_signing_cert.sh      # once
tools/trust_signing_cert.sh     # once (asks for your password)
tools/build_app.sh --open       # builds build/Mispr Flow.app and opens it
cd macos && swift test          # tests
```

**Dev flags** for `MisprFlow`:
- `--detect` prints what kind of meeting it sees;
- `--segment file.wav` shows how audio is cut into chunks;
- `--record-test` checks real capture.

**Environment:** `MISPR_PAGE=Insights` opens on a page; `MISPR_PEOPLE="A,B"` opens People with them selected.

See [main window](../docs/features/main-window.md), [meeting notes](../docs/features/meeting-notes.md), [engine protocol](../docs/engine-protocol.md).
