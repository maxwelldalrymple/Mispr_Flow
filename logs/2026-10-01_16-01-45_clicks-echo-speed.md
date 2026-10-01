# Meeting notes: clicks, speaker echo, and speed

**Branch:** `speaker-id`. Speaker and gender detection were researched in the same session but are being done last, at the user's request.

## User reports

1. Clicking buttons during a meeting got transcribed as "okay", "thank you", etc.
2. With the call on speakers, the mic's copy flashed up as "You" saying the same words as the other person, live.
3. Live text still felt slow.

## 1. Clicks → Silero speech detection (`mispr/meeting.py: SpeechDetector`)

- Silero VAD (644 KB, sherpa-onnx release, pinned SHA-256 `9e2449e1…`) measures how much real speech a clip has.
- Final chunks and live previews with under **0.15 s** of speech are skipped; skipped chunks still report done, so finishing never waits. If the model can't load, every clip is kept.
- The model is downloaded on the first meeting, not at first run.
- Settings chosen by test: threshold 0.5, minimum speech run 0.1 s, minimum silence 0.25 s.

| Input | Speech found |
|---|---|
| 3 mouse clicks (2 s, synthetic) | **0 s** |
| typing, 15 keys (3 s, synthetic) | **0 s** |
| silence | 0 s |
| 12 real turns of 1–4 s (AMI EN2002b) | about 90% of their length |
| 12 real short words of 0.3–0.7 s | 9 of 12 kept with a 0.1 s minimum (6 of 12 with 0.25 s) |

## 2. Echo → `EchoGate` (`MisprCore/EchoGate.swift`), before chunking

The earlier fix only removed echo from the text. Now the mic audio itself is filtered:

- Each 20 ms of mic audio is compared with the call audio at the echo's delay. The delay is found by correlating the two streams' loudness, re-checked every ~2 s.
- **Leak** is how much of the call reaches the mic: the median mic/call ratio while the call is loud.
- A slice no louder than **3× the leak** is silenced. A 160 ms hangover after clear speech keeps word endings.
- Mic audio is held 0.3 s so the call audio has arrived. Saved recordings keep everything.
- With headphones no delay is found and the leak learns ≈ 0, so nothing is silenced.
- Because echo never becomes a "You" chunk, Whisper no longer transcribes every sentence twice. That halves the meeting work when the call is on speakers, which is also a speed fix.

**Real-voice bench** (temporary test, not kept): 60 s of the GitLab YouTube meeting as the call, played through a simulated speaker and room (80 ms delay plus 2 reflections) into the mic. One AMI speaker talks over it for 21 s.

| Setup | echo energy left | your speech kept | delay found |
|---|---|---|---|
| laptop speakers, loud (leak 0.3) | 13% | 100% | 6 slots (120 ms) |
| speakers, moderate (leak 0.1) | 14% | 100% | 6 slots |
| headphones (no leak) | 0% | 94% | none, correctly |

What's left of the echo is reverb tails, which the speech detector and text dedup catch.

Margins tried, over 10 runs each of the unit tests:

| Margin | Result |
|---|---|
| 2× | echo leaked in 10/10 runs |
| 2.5× | echo leaked in 4/10 runs |
| **3×** | **0/10 failures** |

## 3. Speed

- Live text now refreshes every **0.5 s** (was 0.8 s), and again after **0.2 s** of new speech (was 0.25 s). It runs on the base.en preview thread, about 0.15 s each.
- Echo is no longer transcribed (above), and clicks and silence are no longer transcribed (VAD).
- The engine log now shows, per meeting chunk, the stream, its length, the lines made, the processing time and the queue wait, so real-app slowness can be measured.

## Tests run

Full suites, since the core, recorder, engine and app all changed:

- Python: **1079 passed, 10 skipped**.
- Swift: **281 tests, 0 failures**.
- The echo tests were also run 10× in a row: 0 failures.

| New tests | What they check |
|---|---|
| `TestClicksAreNotWords` (4) | a no-speech chunk is skipped and still reported done (audio deleted); speech goes through; previews of clicks are empty; timing is logged |
| `TestSpeechDetector` (2) | unavailable model keeps everything; the real Silero model scores clicks, typing and silence as no speech |
| model specs / wiring | Silero is a pinned HTTPS download, not required at first run; the app gives the worker a detector, not loaded until needed |
| `EchoGateTests` (5) | pure echo silenced, delay found at 5 slots, leak learned ≈ 0.25; your voice over the call kept (≥ 60% in a deliberately hard case); headphones pass everything, leak ≈ 0; no call means nothing touched; mic held 0.3 s then released, nothing lost |
| `NoteModelTests.testLiveTextRefreshesTwiceASecond` | the preview cadence |
