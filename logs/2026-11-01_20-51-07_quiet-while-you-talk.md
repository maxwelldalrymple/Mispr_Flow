# Quiet while you talk

**Asked for** (the queued idea, now built): when dictating, pause or quiet whatever is playing, and put it back when you let go.

**Choice:** mute the Mac's output instead of pressing play/pause. Play/pause starts Apple Music when nothing is playing; muting covers every source and does nothing when it's silent.

**How:** `mispr/duck.py`, `Ducker`.
- On `begin_hold` / `begin_handsfree`: after the start chime (0.094 s long; the mute waits 0.3 s), it checks `output muted`. If you hadn't muted it yourself, it mutes and writes a marker file. All of this runs off the main thread.
- On `_stop_recording` and `discard_quietly`: if we muted it, unmute (before the stop chime) and remove the marker.
- A quick tap never mutes: `wanted` is checked under a lock after the delay.
- At startup, `recover()` unmutes if the marker is left over from a crash.
- Meetings don't go through these paths, so they're never muted.
- Setting `duck_audio` (default on); switch in Settings → System.

**Tests:**
- New `test_duck.py`: mute then restore, already-muted stays muted, a quick tap never mutes, crash recovery.
- `test_widget`: muted while recording and restored on finish, a tap restores, switch off.
- `test_settings_models_setup`, `test_entrypoints`.
- The shared fixture replaces `Ducker`, so tests never mute the real Mac.
- All pass.

## Changed: pause instead of mute (owner: "it needs to pause while I'm talking… and work in the double-click logic")

**Now (`duck.py`):**
- On pressing the **dictation key**, a worker thread checks which apps are running. It asks Music, Spotify and TV for `player state` (only those already running, since asking AppleScript would open an app), and pauses any that are playing.
- In Chrome-family browsers, a page script runs in every tab: it pauses playing `<video>`/`<audio>` and marks them `data-mispr-paused`.
- On release, it plays exactly those apps and resumes the marked elements.
- A tap (`discard_quietly`) resumes after `DOUBLE_TAP_WINDOW` (1 s). A second tap (hands-free) cancels that and stays paused until it finishes.
- The switch key (voice commands) never pauses, so "pause"/"play" don't clash. Meetings are unchanged.
- One worker queue, so a resume never overtakes its pause. The mute code is removed.
- **Live, read only:** Music was "stopped" and Chrome tabs had 0 playing media, and the queries ran cleanly. The AppleScripts compile.

**Tests:**
- `test_duck`: pauses only what plays and resumes only that; nothing playing starts nothing; apps that aren't running are never asked; a tap waits and a second tap keeps it paused without pausing twice.
- `test_widget`: paused while recording and resumed on finish; a tap resumes later; voice commands never pause; switch off.
- All pass.

## "not working": found and fixed

- **Diagnosis:**
  - CoreAudio's per-process output (`prs#`/`piro`, read with ctypes) showed `com.google.Chrome.helper` making sound: a YouTube tab.
  - The page script reached only 1 profile's tabs. The other profile's 18 tabs answered "Executing JavaScript through AppleScript is turned off". **The Chrome setting is per profile.**
- **Fix:** `playing_apps()` reports which apps are making sound. If page scripts missed any tabs and a browser is making sound, the play/pause media key is pressed, and pressed again on release.
  - It's not used when the scripts reached every tab: Chrome can still report sound just after a pause, and the key would restart it.
  - It's never used when no browser is making sound.
- **Cleanup:** a leftover test tab (from the earlier background-typing test) was found in the other profile and closed. The earlier close command hadn't reached every window, so it now loops through each window's tabs.
- **Tests:** `test_duck` adds unreachable tab + sound → key pressed then pressed again; all tabs reached → no key; nothing playing → no key. All pass.
