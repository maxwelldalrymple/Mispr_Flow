# Getting Started

This guide takes you from a fresh clone to dictating. It takes about 10 minutes plus a 3 GB model download.

## 1. Check your Mac

- Apple Silicon (M1 or newer). Intel Macs are not supported.
- About 4 GB free disk (3.1 GB of models) and about 3.5 GB of free RAM while running.
- Xcode Command Line Tools (for building `llama-cpp-python`): `xcode-select --install` if you don't have them.
- Homebrew Python 3.13: `brew install python@3.13`.

## 2. Install

```bash
git clone git@github.com:maxwelldalrymple/Mhispr_Flow.git
cd Mhispr_Flow
python3.13 -m venv .venv
.venv/bin/pip install cmake
CMAKE_ARGS="-DGGML_METAL=on" .venv/bin/pip install -r requirements.txt
```

`llama-cpp-python` compiles from source with Metal (GPU) support. That takes a few minutes, which is normal.

## 3. Set the fn key (optional)

Mhispr_Flow captures the fn/🌐 key itself once Accessibility is allowed (next step), so macOS won't open the emoji picker. If you ever run it without Accessibility, set **System Settings → Keyboard → "Press 🌐 key to" → Do Nothing** so fn doesn't trigger both.

## 4. First launch

```bash
.venv/bin/python -m mhispr
```

1. **Models download.** The widget above the Dock shows **"Downloading models NN%"** for the Whisper model (0.57 GB) and Gemma (2.5 GB). Both are verified with SHA-256 and stored in `~/Library/Application Support/Mhispr_Flow/models/`. Dictation stays locked until they're ready. If it fails, click **Retry**.
2. **Permissions.** macOS asks for each one; allow them. They're granted to the app that launched Mhispr_Flow (Terminal, or Claude if started from a Claude session).
   - **Accessibility** (System Settings → Privacy & Security → Accessibility): captures fn, pastes text, reads the browser URL. If the app is already running with Input Monitoring, this takes effect within about 2 s; otherwise restart the app.
   - **Input Monitoring:** fallback fn detection without Accessibility. Needs a restart after granting.
   - **Microphone:** asked the first time you dictate.
3. The Mhispr_Flow logo appears in the menu bar, and a small pill sits above the Dock.

## 5. Dictate

Click into any text field (Notes, a browser, Slack, Claude), then:

- **Hold fn**, speak, release. The text appears about 1-2 s later.
- **Double-tap fn** for hands-free. Talk as long as you like, then press **space** or **return** to paste, or **fn**/**delete** to cancel. Cancelling shows an **Undo** toast for 5 seconds.

Your previous clipboard is restored automatically after each paste.

## 6. Choose what gets saved

By default each dictation is saved to `voice-recordings/` in the project folder (audio plus a JSON record). To keep nothing, set Incognito in `~/Library/Application Support/Mhispr_Flow/settings.json`:

```json
{
  "incognito": true,
  "cleanup": true
}
```

Restart the app after editing. Set `"cleanup": false` to paste Whisper's raw text without LLM cleanup.

## 7. Quit

Menu-bar logo → **Quit Mhispr_Flow**. Only one copy can run at a time; a second launch prints `mhispr: already running` and exits.

Something not working? See [troubleshooting.md](troubleshooting.md).
