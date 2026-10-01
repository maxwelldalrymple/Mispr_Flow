# 4. Research findings and numbers

## Speed (meeting notes, 2-minute real-time replay of an AMI meeting)

| | Final text after a phrase ends | Live preview lag | Previews delivered |
|---|---|---|---|
| Before (shared queue, turbo) | median 2.07 s | median 0.49 s | 96 / 139 |
| After (own thread, base.en) | median 1.27 s | median 0.14 s | 139 / 139 |

Whisper per clip: turbo ~1 s, small.en 0.2–0.3 s, base.en 0.12–0.17 s.

## Speaker models (d′ = separation of same vs different person)

| Model | AMI d′ | Zoom (YouTube) d′ | ms per s of audio |
|---|---|---|---|
| WeSpeaker ResNet34 | 3.10 | 0.57 | 21 |
| CAM++ | 0.74 | 0.32 | 8 |
| **TitaNet-large** | **4.09** | **0.66** | 21 |
| ResNet293 | 2.95 | 0.25 | 153 |

**Zoom effect:** different people scored 0.55 similar on the Zoom recording versus 0.22 on AMI. Call audio processing makes voices more alike. Centering on the meeting mean didn't help.

## Assignment rules (6 AMI meetings, 23 people)

| Rules | People found | Same-person label switches | Speech under one label |
|---|---|---|---|
| New person below 0.60 (old) | 45 | 9% | — |
| **Join ≥ 0.40, confirm ≥ 0.30, merge ≥ 0.60 (TitaNet)** | 18 | **0%** | **100%** |

On the user's video (lip-tracked labels):
- 7 of 7 people found.
- The main woman was labelled female, and the men male.
- Similar men merged.

## Gender

- **Pitch:** AMI women 163–227 Hz, men 113–142 Hz; Zoom women ~150–155 Hz, men 115–132 Hz.
- **Fingerprint classifier** (logistic regression, 192 TitaNet dimensions), held out by person: 76/80 LibriSpeech and 13/16 AMI correct.

## Clicks (Silero VAD)

- Mouse clicks and typing: 0 s of speech.
- Real 1–4 s turns: ~90% detected as speech.
- With a 0.1 s minimum speech run, 9/12 short "yeah"s were kept.

## Echo gate (60 s real call audio, simulated speaker and room, a real second speaker)

| Setup | Echo left | Your speech kept |
|---|---|---|
| Loud laptop speakers | 13% | 100% |
| Moderate speakers | 14% | 100% |
| Headphones | 0% | 94% |

**Margins tested** (10 runs each): 2× leaked 10/10, 2.5× leaked 4/10, **3×: 0/10 failures**.

## Ground-truth methods used

- **AMI Meeting Corpus** (`diarizers-community/ami` on Hugging Face): close-talk (`ihm`) and far-field (`sdm`) test splits, with speaker labels; gender is encoded in speaker IDs (F…/M…).
- **LibriSpeech** dev/test-clean: 80 speakers with gender.
- **The user's YouTube meeting** (GitLab product marketing, 7 people, gallery view): who's talking from macOS Vision lip landmarks, since there were no on-screen labels or highlight. The labels proved only roughly right.

## Real-Mac checks

| Check | Result |
|---|---|
| Folder search: "Mispr_Flow" | 0.17 s |
| Folder search: "claude" (Spotlight) | 0.18 s |
| Apps found on the Mac | 109 |
| Chrome text-box detection on a test page | correct |
