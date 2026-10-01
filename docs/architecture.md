# Architecture

How Mispr Flow turns a press of fn into pasted text. For decisions and roadmap, see [plan.md](../plan.md).

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
| `meeting-worker` | Final meeting text: speech detection, Whisper turbo segments, speaker fingerprints, summaries, Q&A | One queue so chunks come back in order |
| `meeting-preview` | Live meeting previews with Whisper `base.en` | Its own thread so previews never delay final text |
| `find-folder` | "open folder" / "open …" searches (Spotlight, then a walk) | Up to 1.5 s of disk work off the main thread |

All workers use `threads.start_daemon()`, so none can keep the app from quitting. Results come back to the main thread through `AppHelper.callAfter`.

## The event tap (`hotkey.py`)

- An **active** tap at `kCGHIDEventTap` (needs Accessibility) sees keys before the window server. It swallows:
  - fn flag changes: drives `fn_down` / `fn_up`;
  - the 🌐 key's own key events (keycode 179): stops the Emoji & Symbols picker;
  - hands-free shortcuts, and the matching key-ups, when `WidgetController.handle_key` claims them (space/return/enter/delete).
- The callback only inspects state and defers work with `callAfter`. An active tap delays every keystroke system-wide until it returns, so it must stay fast.
- The same tap watches the **app switcher key** (`switch_trigger`): a key (swallowed), one side of a modifier (passes through), or a combo of modifiers with or without a key. It reports `down` / `up` / `combo` (another key pressed while held, which cancels) to `widget.switch_key`.
- ⌥M (new meeting note) is swallowed so it doesn't type "µ".
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

## First-run setup (`onboarding.py`)

- `SetupFlow` is pure logic: the current step (Welcome, Permissions, Optional features, Models, Ready), which permissions are missing, whether Continue is allowed, and when the window should show (`needed()`). Microphone and Accessibility are required (page 2); Screen & System Audio, Full Disk Access and Control Finder are optional (page 3, never blocking).
- `allow(key)`: the first click shows the one-time system prompt; later clicks (or a microphone that was already denied) open the matching System Settings pane.
- Permission checks never prompt (the window refreshes on a timer): Finder control uses `AEDeterminePermissionToAutomateTarget` without asking, Full Disk Access reads the protected TCC database; only **Allow…** asks.
- `SetupWindow` draws the five pages with standard AppKit controls (so it follows light/dark mode) and refreshes every 0.5 s: checkmarks, the model progress bar (from the widget's download state), and the Continue button.
- Finishing sets `onboarded` in `settings.json`.

## Storage and settings

- `storage.save_recording` writes the 16 kHz 16-bit WAV and the JSON record (see [plan.md](../plan.md#recording-storage) for fields). The folder is the project's `voice-recordings/` from source, or Application Support when packaged.
- `settings.py` loads `settings.json` (unknown keys ignored, corrupt files fall back to defaults with a warning).
- `models.py` downloads to a `.part` file, verifies size and SHA-256, then renames into place. A bad download is never used.

## Lifecycle (`app.py`)

0. **Hosted mode:** when started by `Mispr Flow.app` (`MISPR_HOSTED=1`), the engine skips its own windows and menu, connects to the app (`_connect_host`), and quits when the app does.
1. Single-instance lock (`$TMPDIR/Mispr_Flow.lock`); a second copy exits.
2. Regular activation policy (Dock icon, like Wispr Flow); the process is renamed "Mispr Flow" (`_brand_process`) and the Dock tile uses `assets/AppIcon.icns`; an app menu (About, Setup Guide…, Hide, Quit); clicking the Dock icon opens the setup window until the main window exists; menu-bar template icon.
3. `WidgetController.start()`: builds the panel, prepares the mic engine, then either loads the models or enters SETUP.
4. Opens the setup window (`onboarding.py`) if setup is needed: first run, a required permission missing, or a model missing. Adds **Setup Guide…** to the menu.
5. Every second, `maintain_hotkey` installs the fn tap as soon as a permission allows it, and upgrades a listen-only tap to the active one once Accessibility is granted. No restart needed.
6. On Quit or SIGTERM/INT/HUP: stop the mic, zero and unlock the audio buffer, free the llama.cpp model (its Metal backend asserts otherwise), and remove the menu-bar icon.

## The app and the engine

Two processes:

- **Mispr Flow.app** (SwiftUI, `macos/`): the main window, the meeting side panel, the meeting audio recorder and the echo gate.
- **The Python engine** (`mispr/`): the widget, the hotkeys, dictation, voice commands and all the models.

The app starts the engine and restarts it if it crashes. They talk in JSON lines ([engine protocol](engine-protocol.md)) and share `settings.json`: the app writes it, then sends `reload_settings`.

## Voice commands

```
hold switch key ─► hotkey.FnMonitor (switch edge: down / up / combo)
                   └► widget.switch_key: record (opens a muted mic just for the command)
let go ──────────► Whisper (raw, no cleanup)
                   └► widget._on_switch_heard: save to history (status "command")
                      └► apps.parse(text) → ("switch" | "open" | "open_folder" | "close" | "minimize" | "expand"
                          | "beside" | "size" | "shortcut" | "media" | "seek" | "volume" | "mic" | "mute_tab"
                          | "mute_app" | "scroll" | "scroll_end" | "quit" | "nickname", …)
                          └► widget._do_switch_command → apps.* (match_scored, window_action, press_shortcut,
                             press_media, seek, scroll, set_volume, spotlight / find_in, finder_go …)
                             └► notice + sound; the outcome rewrites the history entry ("Opened claude")
```

Folder searches run on a background thread (`_in_background`). App matching is confidence-scored, so weak guesses never launch an app that isn't running.

## Meeting notes

```
App: MeetingRecorder ─ mic (AVAudioEngine) ──► Resampler 16k ─► EchoGate.mic ─► Segmenter("you") ─┐
                     └ system (ScreenCaptureKit) ► Resampler ─► EchoGate.system, Segmenter("them") ┤
     NoteModel: chunks at pauses ─► transcribe_chunk;  every 0.5 s ─► transcribe_chunk(partial) ───┘
Engine: MeetingWorker
   final queue (one thread): SpeechDetector (Silero) → Whisper turbo segments → VoiceClusters.split
                             (TitaNet fingerprints, join/confirm/merge, GenderModel + pitch) → chunk_text, speakers_merged
   preview queue (own thread): SpeechDetector → Whisper base.en → chunk_text(partial)
App: LiveTranscript.add (Echo text removal, merges) → the panel; Stop → summarize → Save note
```
