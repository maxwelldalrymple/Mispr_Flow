# Cancel a dictation while it's processing

**Asked for:** delete, or a quick double-tap of fn, in the middle of dictating or while it's processing, cancels that one.

**Already the case:** while recording hands-free, delete or fn cancels (with Undo). While holding fn, another key (fn+delete) discards the recording.

**New:**
- **While processing (`cancel_processing`):** delete, or two fn presses within 0.5 s.
  - Each processing run (dictation, long dictation in pieces, voice command, and the fast→accurate command hand-off) gets a job number. Cancelling moves it on.
  - The audio is wiped at once (the model then reads silence), the cancel sound plays with a "Cancelled" notice, and the widget goes back to idle.
  - When the model finishes, `_if_current` drops the result: no paste, no save, and no wipe, since a new recording may already be using the shared buffer.
- **Double-tap to cancel hands-free:** the second tap within 0.5 s of a cancel is ignored. Before, it started a new recording.

**Tests (`test_widget`):**
- delete cancels and the late result is dropped;
- a quick fn double-tap cancels, a single press doesn't, slow presses don't;
- a new dictation isn't wiped or pasted over by the dropped one;
- double-tap-to-cancel in hands-free doesn't start a new recording.
- The old "delete passes through while processing" case is skipped (now delete cancels). All pass.
