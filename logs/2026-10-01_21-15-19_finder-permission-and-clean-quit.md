# Control Finder couldn't be allowed; crash when quitting

**Branch:** `clean-quit`

## 1. "Control Finder" Allow… opened Automation, but Mispr Flow wasn't in the list

**Cause:** macOS only prompts for, and lists, an app's Automation permission if the app's Info.plist explains why (`NSAppleEventsUsageDescription`). The app declared only the microphone reason, so macOS silently refused.

**Fix:** `tools/build_app.sh` adds `NSAppleEventsUsageDescription`: "Mispr Flow opens the folders you name by voice in Finder, and changes the volume when you ask. Only when you hold your voice command key."

## 2. Crash report on quit

**Seen** in the engine log after a quit, right after a model download: `GGML_ASSERT` in `ggml-metal-device.m:657`. The backtrace runs `-[NSApplication terminate:]` → `exit` → `__cxa_finalize` → `ggml_metal_device_free` → abort. llama.cpp's Metal backend aborts in its exit-time destructor when a model is still loading or not fully released.

**Fix:**
- `_install_shutdown` still wipes audio, frees the models and removes the menu-bar icon.
- It then flushes the logs and leaves with `os._exit(0)`, skipping the C++ exit-time destructors.
- This applies to both menu Quit (`NSApplicationWillTerminate`) and signals. `exit` is injectable, so the tests never really exit.

## Tests

`pytest tests/test_screens_sounds_app.py tests/test_entrypoints.py`: all passed.

- `TestShutdown`: signals and menu Quit both release everything, then exit with code 0, through the injected fake.
