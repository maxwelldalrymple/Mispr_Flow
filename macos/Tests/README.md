# Swift tests (`swift test`)

287 tests. `MisprCoreTests` covers the logic; `MisprFlowTests` covers the app.

- **No real hardware or files:** `Helpers.swift` provides `TestApp` (no engine process, temp folders, scratch preferences), `FakeRecorder`, offscreen `render`, and sample recordings and meetings.
- **Running:** `swift test --filter <Class>` runs one class.
- **What each test checks:** [docs/tests/](../../docs/tests/README.md).
