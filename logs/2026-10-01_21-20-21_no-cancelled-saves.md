# Cancelled recordings are never saved

**Branch:** `no-cancelled-saves`

**Request:** "Cancelled recording should never be saved in the audio file or in the text history."

**Before:**
- When the Undo countdown ran out, or delete was pressed on the toast, `_expire_cancel` saved the audio and a "Cancelled recording" history entry.
- `_drop_cancelled` did the same when a new recording replaced the toast.

**Now:**
- Both just wipe the audio (`_wipe`); nothing is written.
- While the Undo toast is up, the audio stays in locked memory only. Undo still works.
- Older cancelled entries (3 on this Mac) are left alone; deleting them is the user's call.

## Tests

`pytest tests/test_widget.py`: all passed.

- `test_cancelled_recording_is_never_saved`: no JSON and no WAV after the countdown; audio wiped.
- `test_delete_on_the_undo_toast_wipes_without_saving`
- `test_superseded_cancel_is_wiped_not_saved`
