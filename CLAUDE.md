# Mispr Flow: notes for Claude

A fully local, MIT-licensed macOS clone of Wispr Flow: dictation, voice commands, meeting notes. The Python engine is in `mispr/` and the SwiftUI app in `macos/`. **Start with [knowledge-base/](knowledge-base/README.md)** (or `knowledge-base/ALL-IN-ONE.md`) for the full history, decisions and research.

## Always

- **Branches:** a new branch per change, unless told to stay on the current one.
- **Tests:** run only the tests covering the change; the full suite only when it's cross-cutting. If told not to run tests, don't.
  - `.venv/bin/python -m pytest tests/<file>.py`
  - `cd macos && swift test --filter <Class>`
- **Logs:** write `logs/<YYYY-MM-DD_HH-MM-SS>_<topic>.md` for every change: what, why, measurements, which tests ran and what they check.
- **Commits** end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. PR bodies end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- **Never copy Wispr Flow's code, sounds or assets.**
- **Never change macOS security or privacy settings yourself.** Give the user the commands.
- **Ask before designing new UI.** Keep replies short and be token-conservative.
- **Paths** the user names are project-relative.
- **Restart the app:** `tools/build_app.sh` (if code changed), then `pkill -f "Mispr Flow.app/Contents/MacOS"; open "build/Mispr Flow.app"`.
- **Debugging:** read `~/Library/Logs/Mispr Flow/engine.log` first.

## Map

- **Engine:** `mispr/`, see [mispr/README.md](mispr/README.md). **App:** `macos/`, see [macos/README.md](macos/README.md).
- **Guides:** `docs/features/`. **Protocol:** `docs/engine-protocol.md`. **Models:** `docs/models.md`. **Tests:** `docs/testing.md`.
