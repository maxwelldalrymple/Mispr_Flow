# Setup window falls behind the app after allowing a permission

**Branch:** `setup-window-front`

**Report:** with the app and the setup window both open, allowing a permission in System Settings and coming back left the setup window **behind** the app's main window.

**Cause:** the setup window belongs to the Python engine, a separate process from `Mispr Flow.app`. Returning from System Settings activates the app, and its main window covers the engine's window.

**Fix (`onboarding.SetupWindow`):**
- **When the app comes forward:** while setup is open, it watches `NSWorkspaceDidActivateApplicationNotification`. When `Mispr Flow.app` (`io.github.maxwelldalrymple.MisprFlow`) becomes active, the setup window orders itself in front (`orderFrontRegardless`).
- **When a permission turns on:** it also comes forward.
- **Not always-on-top:** it doesn't float above everything, because that would cover System Settings while you flip the switches.
- **When setup closes:** the observer is removed.

## Tests

`pytest tests/test_onboarding.py`: all passed.

- `TestSetupStaysInFront` (3):
  - the app coming back brings setup forward, but System Settings or nothing doesn't;
  - a newly granted permission brings it forward;
  - watching starts with show and stops with close; a hidden window stays hidden.
