# Architecture

How Mhispr_Flow turns a press of fn into pasted text. For decisions and roadmap, see [plan.md](../plan.md).

## The pipeline

```
 hold fn                 speak                   release fn
    │                      │                         │
    ▼                      ▼                         ▼
 hotkey.FnMonitor ──► widget: HOLD ──────────► widget: PROCESSING
 (HID event tap)      audio.Recorder.start()   audio.Recorder.stop()  (instant; engine stops in background)
                      AVAudioEngine tap                 │
                      → soxr 44.1k→16k                  ▼
                      → mlock'ed buffer        transcribe.Transcriber   (worker thread, ~1.1 s)
                      → live waveform level             │ raw text
                                                        ▼
                                               cleanup.Cleaner          (same worker, ~0.55 s)
                                               Gemma + check(): no invented words
                                                        │ text
                                                        ▼ (back on the main thread)
                                   context.frontmost() → paste.paste_text() → storage.save_recording()
                                                        │
                                                        ▼
                                               recorder.wipe() → widget: IDLE
```

## Threads

| Thread | Runs | Why |
|---|---|---|
| Main (AppKit run loop) | Event tap callbacks, widget state machine, 60 fps rendering, paste, saving | AppKit and the event tap require it |
| CoreAudio I/O | `Recorder._on_samples`: resample and append to the buffer, update the level | Real-time audio; guarded by `Recorder._lock` |
| `whisper-load`, `cleanup-load` | Load and warm up models at launch | 2-3 s of work that mustn't block the UI |
| `whisper-run` | Transcription + cleanup for one dictation | whisper.cpp and llama.cpp release the GIL, so the UI stays live |
| `mic-stop` | `AVAudioEngine.stop()` | Can never freeze the UI, even if CoreAudio hangs |
| `model-setup` | First-run downloads | Progress is stored as a float the widget draws |

All workers use `threads.start_daemon()`, so none can keep the app from quitting. Results come back to the main thread through `AppHelper.callAfter`.

## The event tap (`hotkey.py`)

- An **active** tap at `kCGHIDEventTap` (needs Accessibility) sees keys before the window server. It swallows:
  - fn flag changes: drives `fn_down` / `fn_up`;
  - the 🌐 key's own key events (keycode 179): stops the Emoji & Symbols picker;
  - hands-free shortcuts, and the matching key-ups, when `WidgetController.handle_key` claims them (space/return/enter/delete).
- The callback only inspects state and defers work with `callAfter`. An active tap delays every keystroke system-wide until it returns, so it must stay fast.
- Without Accessibility it falls back to a listen-only session tap, and upgrades itself every 2 s once Accessibility is granted.
- If macOS disables the tap for being slow, the callback re-enables it.

## The widget (`widget.py`)

`WidgetController` is a state machine drawn into a transparent, non-activating `NSPanel` at status-bar level. It never takes focus from the app you're typing in.

```
            hover                       long-press mic / hold fn
   IDLE ─────────► HOVER ───────────────────────────────► HOLD ──release──► PROCESSING ──► IDLE
    ▲  ◄───────────  │  click mic / double-tap fn                              ▲
    │   pointer out  └──────────────────────────► HANDSFREE ─ ✓/space/return ──┘
    │                                                │  ✕/delete/fn
    │                                                ▼
    └──── 5 s / delete ◄──────────────────────── CANCELLED ── Undo ──► PROCESSING
   HOVER ─ ◉ ─► MEETING ─ stop ─► (short) MISTAKE ─► IDLE        launch w/o models ─► SETUP ─► IDLE
```

- **Layout** (`layout(state)`) is a pure function returning the background shape and clickable elements. Its output is pinned by a golden snapshot test.
- **Frame loop** (`tick`, 60 fps): runs due scheduled callbacks (`_run_due`), polls the active screen every 0.5 s, updates hover and click-through, animates the waveform, eases the shape 30% per frame toward its target, fades content and tooltips, then redraws.
- **Scheduled callbacks** (`after`) carry the state's sequence number, so a timer from an old state (for example the Undo countdown after you pressed Undo) never fires.
- **Click-through:** the panel ignores the mouse except while the pointer is over a button, so it never blocks clicks on the app beneath it.

## Audio (`audio.py`)

- `MicEngine` is the only AVFoundation code. It taps input bus 0 at the device's native format and hands channel 0 to the recorder.
- `Recorder` owns the `SecureAudioBuffer` (10 min, `mlock`ed, zeroed after use), the `soxr` resampler, and the waveform level (RMS → dB → 0..1, fast attack and slow release).
- `stop()` gates capture off under the lock, so no sample arrives after it returns. It flushes the resampler tail and stops the engine on `mic-stop`. A stop that hasn't finished within 1 s is abandoned and the next start builds a fresh engine.
- Why not PortAudio: its macOS backend deadlocked in `Pa_StopStream` (lock-order inversion with CoreAudio's I/O thread). Full analysis in `logs/2026-09-30_14-34-34_mic-deadlock-fix.md`.

## Transcription and cleanup

- `Transcriber._transcribe` skips clips under 0.3 s or with a peak under 0.01, waits for the model to finish loading if needed, and strips `[BLANK_AUDIO]`-style annotations.
- `Cleaner.clean` sends a system prompt, six few-shot examples, and the dictation in `<dictation>` tags, using greedy decoding. `check(raw, cleaned)` then enforces:
  - no word in the output that isn't in the input (after normalizing case, punctuation, apostrophes, and number words);
  - at least 60% of the speaker's non-filler words kept.
  If either fails, the raw transcript is used and the reason is recorded.

## Paste and context

- `paste_text` snapshots the clipboard, puts the text plus transient/concealed markers on it, posts ⌘V (flags = ⌘ only, so a held fn doesn't leak in), and restores the snapshot 0.5 s later unless the user copied something in between.
- `context.frontmost()` names the app. For browsers it walks up the Accessibility tree from the focused element to the outermost `AXWebArea` to get the page URL and title (0.3 s timeout, max 60 hops).

## Storage and settings

- `storage.save_recording` writes the 16 kHz 16-bit WAV and the JSON record (see [plan.md](../plan.md#recording-storage) for fields). The folder is the project's `voice-recordings/` from source, or Application Support when packaged.
- `settings.py` loads `settings.json` (unknown keys ignored, corrupt files fall back to defaults with a warning).
- `models.py` downloads to a `.part` file, verifies size and SHA-256, then renames into place. A bad download is never used.

## Lifecycle (`app.py`)

1. Single-instance lock (`$TMPDIR/Mhispr_Flow.lock`); a second copy exits.
2. Accessory activation policy (menu bar only, no Dock icon); app icon from `assets/AppIcon.icns`; menu-bar template icon.
3. `WidgetController.start()`: builds the panel, prepares the mic engine, then either loads the models or enters SETUP.
4. Requests permissions and installs the event tap.
5. On Quit or SIGTERM/INT/HUP: stop the mic, zero and unlock the audio buffer, free the llama.cpp model (its Metal backend asserts otherwise), and remove the menu-bar icon.
