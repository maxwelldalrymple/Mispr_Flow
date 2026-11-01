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
