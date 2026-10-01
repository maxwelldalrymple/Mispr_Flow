# Commands history: saves what the command did

**Branch:** `speaker-id`

The Commands history showed the raw transcript, misspellings included ("Open clawed folder.").

Now each command's entry is updated with its outcome, using real names: "Opened claude", "→ Google Chrome", "Volume 55%". Failures are saved too ("“receipts” can't be found in Docs"). What Whisper heard stays in `raw_transcript`.

Folder searches finish a moment later, so the entry is saved first and rewritten when the result arrives (`storage.set_transcript`). The app is told to refresh its history.

## Tests

`pytest tests/test_widget.py tests/test_storage.py`: all passed.

- `test_history_keeps_the_outcome_with_real_names`
- `test_set_transcript_keeps_what_was_heard`
