# Screenshot backgrounds

**Problem:** the README's meeting-summary image had a see-through background. Pages shot on their own, outside the main window, had no window background. 20 shots in `docs/screenshots/main-window/` were affected: meeting detail (4 tabs), people, a selected person, shared meetings, the third Notetaker tab, Commands history and More insights, each in light and dark.

**Fix:** `ScreenshotTests.shot` draws every view on the theme's window colour (`Theme.content`). The main-window shots were rerendered (`swift test --filter ScreenshotTests/testMainWindow`: 1 passed). All 18 main-window states were rerendered in light and dark; the shots that were already opaque only changed in their sample times.

**Check:** every screenshot was scanned for transparent edges, and none are left outside `floating-widget/`. The pill floats over the desktop, so its transparency is intended. The meeting summary was checked by eye.
