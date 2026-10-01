# 5. How the user likes to work

## Preferences (follow these)

- **Branches:** make a new branch for each change (the user once asked to keep working on the current branch; follow what they say).
- **Tests:** run only the tests covering a change, and the full suite only when a change is cross-cutting. When the user says "don't run the tests", don't.
- **Logs:** every change gets a `logs/<YYYY-MM-DD_HH-MM-SS>_<topic>.md` with real results, including which tests ran and what they check.
- **Paths:** folder names the user mentions are project-relative (`/voice-recordings` means `<project>/voice-recordings`).
- **UI:** ask before designing UI. When asked, offer choices with a recommended option.
- **Copying:** never copy Wispr Flow's code, audio or assets. Originals only.
- **Security settings:** never change macOS security or privacy settings (tccutil, keychain trust, System Settings) yourself. Give the user the commands.
- **Commits:** end messages with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. PR bodies end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- **Tokens:** the user asked to be token-conservative. Keep replies short and avoid exploratory detours.
- **Restarting:** "restart" means rebuild if needed (`tools/build_app.sh`), then `pkill -f "Mispr Flow.app/Contents/MacOS"; open "build/Mispr Flow.app"`.
- **Language:** the user writes fast and informally (typos like "clawed", "inognito"). Read the intent and mention any reading you weren't sure of.

## Patterns that worked

- **Measure on real data with ground truth** (AMI, LibriSpeech, lip tracking) before choosing a model or threshold. Report the numbers honestly, including limits.
- **Check the engine log** (`~/Library/Logs/Mispr Flow/engine.log`) first when the user reports a bug: it showed "Pro.", "Open Claude Folder" and "text box: no (Google Chrome)".
- **Safety first for anything that acts on the Mac:** no app launches on a guess, no added shell words, permission checks that never prompt.
