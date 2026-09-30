# Getting Started

This guide takes you from a fresh clone to dictating. It takes about 10 minutes plus a 3 GB model download.

## 1. Check your Mac

- Apple Silicon (M1 or newer). Intel Macs are not supported.
- About 4 GB free disk (3.1 GB of models) and about 3.5 GB of free RAM while running.
- Xcode Command Line Tools (for building `llama-cpp-python`): `xcode-select --install` if you don't have them.
- Homebrew Python 3.13: `brew install python@3.13`.

## 2. Install

```bash
git clone git@github.com:maxwelldalrymple/Mispr_Flow.git
cd Mispr_Flow
python3.13 -m venv .venv
.venv/bin/pip install cmake
CMAKE_ARGS="-DGGML_METAL=on" .venv/bin/pip install -r requirements.txt
```

`llama-cpp-python` compiles from source with Metal (GPU) support. That takes a few minutes, which is normal.

## 3. Set the fn key (optional)

Mispr Flow captures the fn/🌐 key itself once Accessibility is allowed (next step), so macOS won't open the emoji picker. If you ever run it without Accessibility, set **System Settings → Keyboard → "Press 🌐 key to" → Do Nothing** so fn doesn't trigger both.

## 4. First launch

```bash
.venv/bin/python -m mispr
```

The **Mispr Flow Setup** window opens and walks you through four steps:

1. **Welcome.** What Mispr Flow is. Click **Get Started**.
2. **Allow access.** Each permission shows why it's needed and an **Allow…** button. Rows turn to **✓ Allowed** as soon as you grant them (the window checks every half second).
   - **Microphone** (required): hears you while you hold fn.
   - **Accessibility** (required): uses the fn key and pastes into the app you're typing in. The first click shows the macOS prompt; clicking again opens the right page in System Settings.
   - **Screen & System Audio** (optional): for meeting notes. You may need to reopen Mispr Flow after allowing it.

   **Continue** unlocks once both required permissions are allowed. fn starts working within a second of granting Accessibility, with no restart.
3. **Download speech models.** Whisper (0.57 GB) and Gemma (2.5 GB), with a progress bar. Both are verified with SHA-256 and stored in `~/Library/Application Support/Mispr_Flow/models/`. If it fails, click **Retry**.
4. **You're all set.** A quick guide to fn. Click **Start Dictating**.

When running from source, permissions are granted to the app that launched Mispr Flow (Terminal, or Claude if started from a Claude session). The logo appears in the menu bar and a small pill sits above the Dock. Reopen setup anytime from the menu bar: **Setup Guide…**

## 5. Dictate

Click into any text field (Notes, a browser, Slack, Claude), then:

- **Hold fn**, speak, release. The text appears about 1-2 s later.
- **Double-tap fn** for hands-free. Talk as long as you like, then press **space** or **return** to paste, or **fn**/**delete** to cancel. Cancelling shows an **Undo** toast for 5 seconds.

Your previous clipboard is restored automatically after each paste.

## 6. Choose what gets saved

By default each dictation is saved to `voice-recordings/` in the project folder (audio plus a JSON record). To keep nothing, set Incognito in `~/Library/Application Support/Mispr_Flow/settings.json`:

```json
{
  "incognito": true,
  "cleanup": true
}
```

Restart the app after editing. Set `"cleanup": false` to paste Whisper's raw text without LLM cleanup.

## 7. Quit

Menu-bar logo → **Quit Mispr Flow**. Only one copy can run at a time; a second launch prints `mispr: already running` and exits.

Something not working? See [troubleshooting.md](troubleshooting.md).
