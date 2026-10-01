# 5. How the user likes to work

## Preferences (follow these)

- **Branches:** make a new branch for each change (the user once asked to keep working on the current branch; follow what they say).
- **Tests:** run only the tests covering a change, and the full suite only when a change is cross-cutting. When the user says "don't run the tests", don't.
- **Logs:** every change gets a `logs/<YYYY-MM-DD_HH-MM-SS>_<topic>.md` with the **actual results** (the user asked for real stress-test output, not just a summary), including which tests ran and what they check.
- **Don't rerun all the tests** unless the change affects them ("do not rerun all tests unless they impact the changes you made").
- **"Ask me"** before big product choices (setup screens, UI layouts). Offer options with a recommendation.
- **The end goal** is a downloadable app (DMG) others can install on M1+ Macs. Keep that in mind for packaging choices.
- **Speed matters** to the user ("how long is this gonna take"). Say what you're doing, and finish and restart the app promptly when asked.
- **"Restart"** while working means wrap up what's running and relaunch the app so the user can try it.
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
