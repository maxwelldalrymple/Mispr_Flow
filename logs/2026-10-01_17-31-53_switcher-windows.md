# App switcher: window commands

**Branch:** `speaker-id`

Hold the switch key and say one of these:

| Say | Does |
|---|---|
| "close Chrome" / "close" | closes the front window (of Chrome, or the app you're in); doesn't quit |
| "minimize Terminal" / "minimize" (also "hide") | minimizes it |
| "expand VS Code" / "maximize" / "expand" | fills the screen (menu bar and Dock stay) |
| "Chrome beside VS Code" (also "window layout …", "put … next to …", "… and …") | side by side: Chrome on the left half, VS Code on the right |
| "Chrome 70% beside VS Code" | Chrome 70% of the width, VS Code the rest |
| "Chrome 80%" / "Chrome eighty percent" / "make Slack 60 percent" | 80% of the screen's width and height, centred |

- Numbers can be spoken ("sixty-five percent"). Sizes from 10% to 100% are accepted, splits from 10% to 90%.
- Apps that aren't open are launched and their window placed when it appears (up to 3 more tries, 0.75 s apart).
- In a layout, the first app named ends up in front.
- Windows are moved through the Accessibility API, which was already granted for pasting. Nothing new to allow.

## Tests

`pytest tests/test_apps.py tests/test_widget.py`: all passed.

- `TestWindowCommands` (14): parsing every form above, including spelled-out numbers and a too-small percent that stays a plain switch; the layout math; reading this Mac's screen and front app.
- `TestAppSwitcher` (+5):
  - close, minimize and expand, by name or the current app;
  - a 70/30 split with the first-named app in front;
  - 80% centred;
  - an app still opening is retried;
  - an unknown app in a layout errors.
