# 2. History of the work (from our conversations)

A chronological record of what was asked and what was done: the "chat history". The details of each step are in `logs/` and `CHANGELOG.md`.

## Phase 1: the dictation engine (before Sep 30, 2026)

- **v0.1 dictation:** an fn event tap, AVAudioEngine capture into an `mlock`ed wipeable buffer, whisper.cpp turbo, and paste with clipboard restore.
- **v0.2 LLM cleanup:** Gemma-3-4B chosen over Qwen models in a 27-case eval; a code guard rejects any invented word.
- **The floating widget:** a state machine, waveform, hands-free and Undo toast, screen following, sounds.
- **Test suite:** stress tests, mutation testing (97.6%), golden images.

## Phase 2: polish and the setup window (Sep 30)

- **Sounds:**
  - The user asked for sounds "99.99999% similar" to Wispr's. Copying Wispr's audio was **declined**, so original cues "with the same exact feel" were synthesized (`tools/make_sounds.py`).
  - Every event was hooked to a sound.
  - The paste sound must only play when text actually lands; otherwise the error sound plays.
- **Text boxes:** paste only into a focused text box, otherwise copy with a notice. In Incognito, type instead of paste and never copy.
- **App icon** from the project image; a Dock app; a mic notice on first dictation.
- **Setup window** (Welcome → Permissions → Models → Ready).
- **A mic deadlock fix** (logged).
- README, changelog and plan updated; merged.

## Phase 3: the SwiftUI app (branch `ui`)

- **SwiftUI was chosen over Python** for the main window (the user asked which Wispr uses; native was chosen).
- The user shared videos of Wispr's pages and asked to copy Wispr's code and UI from its app bundle. That was **declined**: originals only, in a similar spirit.
- **Pages:** Home, Insights (many insights, a "Your Voice" profile, fun facts), Notetaker, Prompts (edit the cleanup prompt live), Settings with a Profile (name, nickname, photo, 6 themes).
- **Incognito** became a top-right switch with a hover explanation and a purple look.
- **Dictation key:** any key can be the dictation key.
- **Meeting notes:**
  - ⌥M with mic plus system audio, opening a side panel modelled on Wispr's.
  - Meeting-type detection (Zoom/Meet/Teams…) and a split-screen button.
  - Live previews and Male/Female/Person labels with colour coding.
  - People pages: click one or several people to see shared meetings.
- **Sample data tools** for fake meetings and dictations.
- **Fixes:**
  - The widget and app lost their connection; reconnecting was fixed.
  - Scrolling wasn't smooth.
  - The window was too big.
  - The idle pill was made darker.
  - Permissions kept being re-asked. Fixed with a trusted local signing certificate: the user ran `tools/trust_signing_cert.sh` and `tccutil reset` themselves, because the assistant does not change security settings.
- Merged via PR #15.

## Phase 4: test audit (branch `ui-tests`, Oct 1)

- "Check every UI function has unit tests" led to a new `MisprFlowTests` target and code made testable (injectable recorder and permission checks).
- Swift tests went from 90 to 219, and Python coverage to 99.5%.
- "Track all the tests and what they do in the logs" led to `tools/test_catalog.py`.

## Phase 5: meetings, notes, voice commands (branch `speaker-id`, Oct 1)

1. **Multi-person meetings:** the user reported "can't identify same people", "slow", and asked "cosine similarity to compare voices?".
   - Benchmarked on real AMI meetings.
   - Built WeSpeaker embeddings with cosine clustering, chunks split at speaker changes, and a fast base.en preview thread.
2. **Auto-Enter** button (top bar, tooltip).
3. **Save on purpose:** closing the side panel shouldn't save. Added Save / Discard / Keep editing.
   - Deleting notes four ways.
   - Rename or remove people and contact cards ("you have fun").
4. **Voice app switcher:** hold a key, say an app; nicknames by voice ("set nickname Scooby Snacks to Chrome"). The switch key can be a single key or a combo.
5. **Echo:** with the call on speakers, lines duplicated as "You". Fixed with text-level echo removal.
6. **Second round of meeting feedback:**
   - The user listed: same man switching Male 1/Male 2; women labelled male; still slow; echo flashing; button clicks transcribed. Voice detection was asked to be done last.
   - Clicks: Silero VAD. Echo: an audio echo gate on the mic. Speed: faster preview cadence.
   - **Diarization:**
     - The user suggested testing on their YouTube meeting (GitLab, lBVtvOpU80Q) and reading who's talking from the video.
     - The gallery view has no labels, so macOS Vision lip tracking was used.
     - Five models compared; TitaNet chosen.
     - Rules: a new person only after two matching sentences, and lookalikes merged.
     - Gender: a classifier on 96 voices (AMI and LibriSpeech) plus pitch around 145 Hz.
7. **Auto-Enter cues:** a badge and chime. The YouTube "copied instead of pasted" report led to a browser text-box recheck plus logging.
8. **Voice commands extended**, one request at a time:
   - close / minimize / expand, side by side with splits, "Chrome 80%";
   - tab and browser shortcuts;
   - play/pause, volume, mute mic/tab/app, directional unmute;
   - skip forward/back N seconds;
   - scroll;
   - plain "quit".
9. **Home:** a Voice commands card, shortened when it didn't fit.
10. **Commands history:** commands weren't saved, so a **Commands** tab was added. Saying "Chrome" once opened Logic Pro (Whisper heard "Pro."), so matching was made strict and confidence-scored.
11. **Open folder / open in Finder:**
    - Highest-level match wins.
    - In Finder, "open X" navigates the same window or opens a file; otherwise "can't be found".
    - Spotlight and sound-alike names ("clawed" → claude).
    - Permissions belong in setup. The user asked for Full Disk Access ("the whole file system") rather than per-folder prompts.
12. **Setup:** "doesn't look good" led to two permission pages (required / optional).
13. **Terminal mode:** optimize for shell syntax in terminals. Auto-Enter was first skipped in terminals for safety, then **enabled at the user's request**.
14. **Commands history:** save the outcome with real spellings ("Opened claude"), not what was misheard.
15. **Final checks:** a hands-on checklist for the user, and a test-coverage double-check (the user asked not to run the tests). Merged via **PR #16**.

## Phase 6: documentation (branch `documentation`, Oct 1)

- "Update all the READMEs, create as many as possible to explain every feature and test, and a knowledge base someone can pass into Claude": this folder.
