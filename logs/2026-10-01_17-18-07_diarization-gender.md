# Speaker diarization and voice gender

**Branch:** `speaker-id`

## Problems the user reported

- The same man switched between "Male 1" and "Male 2".
- Women were labelled male.

## Research (scratch data; not in the repo)

**Data:**
- AMI Meeting Corpus close-talk test set: 6 meetings, 16 people with known gender (CC BY 4.0).
- LibriSpeech dev/test-clean: 80 people (CC BY 4.0).
- The user's YouTube meeting (GitLab, 7 people). "Who's talking" labels came from macOS Vision lip tracking, since there's no outline or name label in the recording. Those labels are approximate.

**Voice models.** d′ is the separation between same-person and different-person similarity; higher is better.

| Model | AMI d′ | YouTube d′ | ms per s of audio |
|---|---|---|---|
| WeSpeaker ResNet34 (old) | 3.10 | 0.57 | 21 |
| CAM++ | 0.74 | 0.32 | 8 |
| **TitaNet-large (new)** | **4.09** | **0.66** | 21 |
| ResNet293 | 2.95 | 0.25 | 153 |

**Why people switched labels.** On clean meetings, 5% of one person's sentences score below 0.33 against their other sentences, so one odd sentence made a new person. In the Zoom recording, different people scored 0.55 alike (0.22 in AMI). Zoom's audio processing makes voices more alike, so no single threshold fits both.

**Rules (TitaNet), simulated on the 6 AMI meetings:**

| Rule | people found (true 23) | same-person label switches | each person under one label |
|---|---|---|---|
| old: new person below 0.60 | 45 | 9% | — |
| **new: join ≥ 0.40, confirm ≥ 0.30, merge ≥ 0.60** | 18 | **0%** | **100%** |

**Gender:**
- Pitch: Zoom women measured ~150–155 Hz and men 115–132 Hz. The old male/female cutoffs were 155/168 Hz, which is why women came out male.
- A fingerprint classifier trained on 96 voices and tested on people left out of training: 76/80 LibriSpeech and 13/16 AMI correct. On Zoom it rates everyone lower, but women still score higher than men.
- Shipped: the average of the classifier and a pitch score centred on 145 Hz.

## What changed

- **Model:** `SPEAKER_MODEL` = TitaNet-large (101 MB, SHA-256 pinned, from sherpa-onnx's release). It downloads on the first meeting.
- **`VoiceClusters` uses stable speaker ids:**
  - a sentence joins the closest person at ≥ 0.40;
  - otherwise it waits as "maybe someone new" (shown as the closest person); a second matching sentence (≥ 0.30) creates the new person;
  - people ≥ 0.60 alike are merged, and the engine sends `speakers_merged` so the app relabels earlier lines (names given to either are kept).
  - The spectral-signature fallback uses its own thresholds.
- **Gender:** `GenderModel` loads `mispr/voice_gender.json` (192 weights).
  - The voice label is the average of the classifier and the pitch score; "person" only when nothing has been heard.
- **Bug found while testing:** a "maybe someone new" sentence added its pitch to the person it was temporarily shown as. Now only confident matches teach a voice.

## On the user's video (shipped code, 116 lip-labelled stretches)

- 7 people found (of 7), 0 merges needed.
- The main female speaker is labelled female; the men are male. One woman's tile came out male; her lip labels may be wrong.
- Most men collapse into one speaker: in this Zoom audio their voices are too alike for the model. The rules prefer merging over switching, as asked.
- 7 of 50 same-person transitions switched label, against noisy labels.

## Tests

The full suites ran:

- Python: **1080 passed, 10 skipped**.
- Swift: **284 tests, 0 failures**.

New and rewritten:

- `TestEmbeddingClusters` (9): join; one odd sentence never makes a new person; alike people merged and reported; short or unclear speech; only clear speech refines a voice; too short means the last speaker; at most 8 people; signature fallback; merges sent to the app.
- `TestGender` (4): shipped weights load; missing or mismatched weights give None; fingerprint and pitch averaged; probability output.
- Updated `TestVoiceKind`, `TestTranscribeChunk` and `TestSplitAtSpeakerChanges` for the confirm rule.
- Swift `SpeakerMergeTests` (2) and `NoteModelTests.testMergedSpeakersShowAsOnePerson`.
