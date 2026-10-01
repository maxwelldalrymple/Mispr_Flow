# Notes: save on purpose, delete, and manage people

**Branch:** `speaker-id`

## What changed

**Side panel: nothing is saved until you press Save**
- After Stop, a "Keep this note?" card appears with an accent **Save note** button (⌘S) and **Discard**. Once saved, the card turns into "Saved to Notetaker · Open", and later changes (summary, title, speaker names) keep updating the saved note.
- The panel asks **Save / Discard / Keep editing** when you have unsaved words and you:
  - close it with ‹ or the red button, or
  - start a new note with ⌥M or ◉.
- While recording, the question reads "Stop and save this note?" and its last button is "Keep recording". Empty or already-saved notes just close.
- **Discard** stops recording, deletes the note's audio folder, and starts a fresh note. Late transcriptions from the discarded note are ignored.
- **Incognito** notes are never saved, so there is no Save button. Closing asks only while recording, offering Discard or Keep recording.

**Notetaker: deleting notes, four ways**, each behind a "Delete …? This can't be undone" confirmation:
- a trash button when you hover a note;
- right-click → Delete…;
- Delete on the note's page;
- **Select** mode: tick notes (Select all / none), then Delete.

Deleting removes the JSON and the audio folder.

**People**
- Right-click or the **⋯** menu → Edit name & details… or Remove from People….
- **Contact card** (sheet):
  - name: renaming updates every note's participants, transcript lines and action items, and renaming onto an existing person merges them;
  - role, company, email (mailto link), phone, notes.
  - Cards are stored in `meeting-recordings/people.json` and shown under the person's name.
- **Remove** keeps the notes. That person's lines become "Unknown speaker" and their card is deleted.

**Found while testing:** note IDs had one-second resolution ("…-000"). A note started in the same second as a discarded one reused its ID, so it could overwrite or delete the wrong files. IDs now carry real milliseconds.

## Tests run

The full Swift suite ran, because the change touches the core, the model, views and the window: **252 tests, 0 failures** (was 219).

| New / changed tests | What they check |
|---|---|
| `NoteEditingTests` (core, 10) | delete removes JSON + audio folder; deleting an unsaved meeting is a no-op; rename updates participants/lines/action items; rename merges into an existing person; never renames "You" or to a blank name; remove keeps the note with "Unknown speaker"; rewrite needs a file; contact book save/load drops empty cards and isn't read as a note; a card moves with a rename; note IDs have milliseconds |
| `NoteModelTests` (+8, 4 updated) | Stop asks for a summary but saves nothing until Save; Save while recording stops then saves; Discard deletes audio and resets; Discard while finishing ignores late words; empty/saved notes close directly; unsaved notes ask, and Keep editing / Save each work; Discard from the question closes without saving; ⌥M over an unsaved note asks first, then Save starts the new one; Incognito asks only while recording and never saves |
| `NotesAndPeopleActionsTests` (5) | deleting notes in the app; renaming a person everywhere moves their card; saving a card with a new name renames; removing a person keeps notes and drops the card; failures show a message |
| `NotesWordingTests` (6) | delete titles, save card detail, question titles, selection after a rename, person subtitle, rename detection |
| `RenderTests` (+2, 2 extended) | note rows (hover-delete, select mode, picked), note page with Delete, people with contact details, the contact editor, the Save card, question card and Saved chip in the panel |
| `AppShellTests.testClosingWithAnUnsavedNoteKeepsThePanelAndAsks` | the red close button never closes directly; it asks, and Discard closes |
