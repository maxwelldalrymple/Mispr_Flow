# Meeting notes

Press **⌥M** (or ◉ on the widget). A side panel slides in at the right edge of your screen, and the app records **your mic** ("You") and **the Mac's sound** (everyone else on the call) at the same time.

## In the panel

- **Live text** as people talk: grey while a phrase is in progress, final when they pause.
- **Who's talking:** other voices are labelled Male 1, Female 1, Person 1… Click a name to rename them.
- **Tabs:** My thoughts (your own notes), Transcript (with search), Summary.
- **Ask anything** about the meeting, or **What did I miss?**
- **Meeting type is detected:** Zoom, Google Meet, Teams, FaceTime, Webex, Slack huddle, or in person. The split-screen button puts the panel beside the call window.
- **Stop**, then the **Keep this note?** card: **Save note** (⌘S) or **Discard**. Nothing is saved until you press Save. After saving, changes (summary, title, names) keep updating the note.
- **Closing (or starting a new note) with unsaved words asks Save / Discard / Keep editing.** While recording it reads "Stop and save this note?". Incognito notes are never saved.
- **Resume** keeps adding to the same note.

## How it works

1. The app (`MeetingRecorder`) captures the mic with AVAudioEngine and system audio with ScreenCaptureKit, both resampled to 16 kHz mono.
2. **Echo gate** (`EchoGate.swift`), for when the call plays on speakers and the mic hears it again:
   - It finds the echo's delay by correlating the two streams' loudness.
   - It learns how much of the call leaks into the mic, and silences mic slices that are only that leak (3× margin, 160 ms hangover, 0.3 s hold).
   - Your own voice passes. With headphones, nothing is touched.
   - Real-voice bench: 100% of your speech kept, ~86% of echo removed.
3. A **segmenter** cuts each stream at pauses (≥ 0.5 s, chunks up to 10 s) and sends chunks to the engine.
4. **Text-level echo removal** (`Echo` in `LiveMeeting.swift`): a mic line that repeats what the other side said within ±10 s is dropped, or just the echoed words are cut. This works whichever arrives first.
5. **Clicks are ignored:** Silero speech detection skips clips with under 0.15 s of real speech, so mouse clicks don't become "okay." or "Thank you.".
6. **Final text:** Whisper turbo on one worker thread, split at Whisper's segments where the speaker changes.
7. **Live previews:** a small model (`base.en`, ~0.15 s) on its own thread, twice a second, so they never delay final text.
8. **Speakers (diarization):**
   - Each stretch of speech gets a TitaNet voice fingerprint, and joins the most similar person at cosine ≥ 0.40.
   - A new person is created only after **two** matching stretches (≥ 0.30) that don't fit anyone.
   - People whose voices turn out alike (≥ 0.60) are merged, and earlier lines relabelled.
   - On 6 real AMI meetings: 0% label switches within a person, 100% of each person's speech under one label.
   - Known limit: on Zoom-processed audio, similar men can merge into one speaker.
9. **Male/female:** the average of a classifier on the fingerprint (trained on 96 voices) and a pitch score centred on 145 Hz.
10. **Summary and answers:** Gemma, locally (title, overview, decisions, action items, open questions).

Notes are saved as JSON under `meeting-recordings/YYYY-MM-DD/`, with the audio in a folder beside them (unless Incognito). The research behind these numbers is in `logs/*speaker-id*`, `*diarization-gender*`, `*clicks-echo-speed*` and `*echo-removal*`.
