# Mispr Flow: complete knowledge base

You are being given the full context of the Mispr Flow project: what it is, how it's built, every
decision and why, the history of the work, research results, and how the project owner likes to
work. Read section 1 (overview) and section 2 (working preferences) first, and follow those
preferences when helping. Paths are relative to the repository root
(github.com/maxwelldalrymple/Mispr_Flow). Links inside each section are relative to that section's own
file, named in the comment above it.

_Built 2026-10-01 19:18 from 25 files by tools/build_knowledge_base.py._


---

<!-- knowledge-base/01-overview.md -->

# 1. Project overview

**Mispr Flow** is a free, open-source (MIT), fully local macOS clone of Wispr Flow, by Maxwell Dalrymple (GitHub `maxwelldalrymple/Mispr_Flow`). Everything (speech recognition, text cleanup, speaker detection, summaries) runs on the Mac. The only network use is one-time, hash-checked model downloads.

## What it does

1. **Dictation:**
   - Hold `fn` (or any chosen key), speak, release; double-tap for hands-free.
   - Whisper transcribes, Gemma cleans up (never inventing words), and the text is pasted into the focused text box, or copied if there's none.
   - Incognito saves nothing and types instead of pasting.
   - Auto-Enter presses Return after.
   - Terminal mode turns spoken syntax into shell commands.
2. **Voice commands ("app switcher"):**
   - Hold a switch key (key, modifier side, or combo) and say a command:
     - switch, close, minimize, expand or quit apps;
     - side-by-side and percent layouts;
     - tab and browser shortcuts;
     - play/pause, skip seconds, volume, mute mic/tab;
     - scroll;
     - open folders and files;
     - nicknames.
   - Commands are saved to a Commands history with the real names.
3. **Meeting notes:**
   - ⌥M opens a side panel that records the mic ("You") and system audio (the call) together.
   - Live text, with speakers told apart (TitaNet fingerprints) and labelled Male/Female/Person N.
   - Echo and clicks are filtered.
   - Summary and Q&A run locally. Notes are saved only when you press Save.
4. **Main window (SwiftUI):** Home (history: Dictation | Commands, stats, shortcuts, voice commands), Insights, Notetaker (notes, People with contact cards, insights), Prompts (edit the cleanup prompt live), Settings (profile, 6 themes, keys, nicknames, sounds).
5. **Setup window:** Welcome → Allow access (Microphone, Accessibility) → Optional features (System Audio, Full Disk Access, Control Finder) → Models → Ready.

## Architecture in one paragraph

Two processes:
- **`Mispr Flow.app`** (Swift package `macos/`, targets `MisprCore` and `MisprFlow`): the windows, the meeting recorder (AVAudioEngine and ScreenCaptureKit) and the echo gate.
- **The Python engine** (`mispr/`, PyObjC): the floating widget, the global hotkeys (Quartz event tap), dictation, voice commands and all models (pywhispercpp, llama-cpp-python, sherpa-onnx).

The app hosts the engine (`MISPR_HOSTED=1`). They talk in JSON lines over stdin/stdout (engine events are prefixed `@mispr `) and share `~/Library/Application Support/Mispr_Flow/settings.json`.

## Models

| Model | Size | Used for |
|---|---|---|
| Whisper large-v3-turbo q5_0 | 574 MB | dictation and final meeting text |
| Gemma-3-4B Q4_K_M | 2.49 GB | cleanup, terminal mode, summaries, Q&A |
| Whisper base.en | 148 MB | live meeting previews |
| NVIDIA TitaNet-large | 101 MB | speaker fingerprints |
| Silero VAD | 0.6 MB | speech vs clicks |
| `voice_gender.json` | 192 weights, trained here | male/female |

## Key paths

| Path | What |
|---|---|
| `mispr/` | engine |
| `macos/` | app |
| `tests/` | Python tests: 1217 |
| `macos/Tests/` | Swift tests: 287 |
| `tools/` | build, signing, sample data, test catalogue |
| `docs/` | guides |
| `logs/` | one timestamped report per change, with real results |
| `voice-recordings/`, `meeting-recordings/` | user data, gitignored |
| `~/Library/Logs/Mispr Flow/engine.log` | engine log |
| `build/Mispr Flow.app` | the built app (`tools/build_app.sh`) |

## State at the end of this history (2026-10-01)

- `main` has everything (PR #16 merged).
- The `documentation` branch holds the docs and this knowledge base.
- All tests pass.
- **Next:** the first-run tutorial and a security/network audit; then languages, a dictionary/snippets, and an installable build for other Macs.


---

<!-- knowledge-base/05-working-with-the-user.md -->

# 5. How the user likes to work

## Preferences (follow these)

- **Branches:** make a new branch for each change (the user once asked to keep working on the current branch; follow what they say).
- **Tests:** run only the tests covering a change, and the full suite only when a change is cross-cutting. When the user says "don't run the tests", don't.
- **Logs:** every change gets a `logs/<YYYY-MM-DD_HH-MM-SS>_<topic>.md` with the **actual results** (the user asked for real stress-test output, not just a summary), including which tests ran and what they check.
- **Don't rerun all the tests** unless the change affects them ("do not rerun all tests unless they impact the changes you made").
- **"Ask me"** before big product choices (setup screens, UI layouts). Offer options with a recommendation.
- **The end goal** is a downloadable app (DMG) others can install on M1+ Macs. Keep that in mind for packaging choices.
- **Speed matters** to the user ("how long is this gonna take"). Say what you're doing, and finish and restart the app promptly when asked.
- **"Restart"** while working means wrap up what's running and relaunch the app so the user can try it.
- **Paths:** folder names the user mentions are project-relative (`/voice-recordings` means `<project>/voice-recordings`).
- **UI:** ask before designing UI. When asked, offer choices with a recommended option.
- **Copying:** never copy Wispr Flow's code, audio or assets. Originals only.
- **Security settings:** never change macOS security or privacy settings (tccutil, keychain trust, System Settings) yourself. Give the user the commands.
- **Commits:** end messages with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. PR bodies end with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- **Tokens:** the user asked to be token-conservative. Keep replies short and avoid exploratory detours.
- **Restarting:** "restart" means rebuild if needed (`tools/build_app.sh`), then `pkill -f "Mispr Flow.app/Contents/MacOS"; open "build/Mispr Flow.app"`.
- **Language:** the user writes fast and informally (typos like "clawed", "inognito"). Read the intent and mention any reading you weren't sure of.

## Patterns that worked

- **Measure on real data with ground truth** (AMI, LibriSpeech, lip tracking) before choosing a model or threshold. Report the numbers honestly, including limits.
- **Check the engine log** (`~/Library/Logs/Mispr Flow/engine.log`) first when the user reports a bug: it showed "Pro.", "Open Claude Folder" and "text box: no (Google Chrome)".
- **Safety first for anything that acts on the Mac:** no app launches on a guess, no added shell words, permission checks that never prompt.


---

<!-- knowledge-base/02-history.md -->

# 2. History of the work

What was asked and what was done, in order, built from every message in the conversation. Times are UTC. Your exact words are in [08-your-messages.md](08-your-messages.md), and the full conversation is in [07-chat-log.md](07-chat-log.md). Each change's details and test results are in `../logs/`.

The idea started in an earlier claude.ai chat, "Whispr Clone", which isn't included. All the building happened in one Claude Code conversation, from **2026-09-30 14:56** to **2026-10-01 23:15**.

## Sep 30: the dictation engine

- **14:56, start.**
  - "We are building our own whispr desktop app that uses fn presses to activate an STT pipeline." A folder under `claude/`, a git repo, an empty README.
  - **How Wispr behaves:** double-press (within 1 s) or hold fn; speech-to-text; a light model cleans up; paste into the current window.
- **15:14, the floating widget,** built from screen recordings of Wispr:
  - a pill near the bottom; hover for a record button; cancel or accept while recording;
  - "Transcript cancelled" with **Undo**.
  - **Fixes the user asked for:**
    - two duplicate menu-bar icons, removed;
    - hover buttons with more padding, 25–50% taller;
    - a nicer record icon.
  - The user noted the goal of a **DMG** others can download ("unsigned for now, DMG after dictation works") and asked to **work on a `build` branch**.
- **fn and the mic:**
  - double-fn opened macOS's **emoji window**, fixed by swallowing fn and the globe key;
  - **space/enter accept, delete/fn cancel** while hands-free;
  - pressing delete on the cancelled toast discards immediately.
  - Pushed as `widgets-fn-record-complete`.
- **16:17, transcription** with whisper.cpp. The user asked whether a Python app can still ship as a DMG for M1+ Macs (yes, with a bundled Python).
- **Recording storage:**
  - Saved by default (a future **Incognito** switch will delete instantly).
  - The user corrected the naming to **millisecond precision**, with JSON recording the app it pasted into and the website URL.
  - The user corrected the path too: "when I give a file location I obviously mean starting with the project path", so it's `<project>/voice-recordings`.
- **16:38:** tagged **`v0.1-dictation`**.
- **LLM cleanup:**
  - The user had Qwen2.5 installed and asked to look for it.
  - Then: "use a better model, I can't have it making up stuff I didn't say." Gemma-3-4B won an eval, with a code guard against invented words.
  - **Models are a mandatory install step at startup.**
  - Tagged **`v0.2-llm-cleanup`**. (The user had been merging to `main` on GitHub; build "4 behind main" was explained.)
- **17:07, "unit tests":** "every single function that gives an output: as many unit tests as possible."
- **17:20, stress tests:** "stress test the shit out of the tests, and rewrite failing ones with proper design patterns."
  - **"Log all this stress testing in /logs as today's date and time, and store the actual results."**
  - The user pushed for speed ("how long is this gonna take", "I gave you a whole hour").
- **18:30, mic freeze:** the widget froze after long audio. The user said: fix it on `build`, "track all this in /logs", and "**do not rerun all tests unless they impact the changes you made**". The fix replaced PortAudio with AVAudioEngine (logged).
- **18:48, rebrand** (branch `Rebranding`): first to "Mhispr". The user then corrected it: the real app is **"Wispr Flow"**, so this one is **"Mispr Flow"**. The new logo became the app and GitHub icon.
- **18:55, docs:** `plan.md` in lower case, updated README and plan. "Mispr Flow is a clone of Wispr Flow," with the reasons: open source, free, private, customizable, multilingual.
  - An **MIT license** was added. French and Spanish were tested, and languages went on the roadmap.
  - "Make sure the documentation is excellent." Merged.
- **19:15, benchmarks and scope** (pasted notes from the claude.ai chat), then a confirmation that a Python app still bundles into a DMG.
- **19:22, first-run setup screens** (permissions checklist). The user said "ask me" and "**make a new branch if you're making changes**". Merged.
- **19:43, a real app window:** "I want an actual app window. The widget is only visible when the app window isn't." The user asked what Wispr is made with, and promised videos of every screen.
- **19:53, sounds:**
  - The user asked to take Wispr's sounds from its app folder, then to edit them with randomness so they aren't copies, then "**99.99999% similar**". All **declined** as copying.
  - Agreed instead: "**make original sounds with the same exact feel**".
  - Every event was hooked to a sound.
  - The paste sound plays only on a real paste; otherwise the error sound.
- **20:16, `ui` branch:**
  - The Dock icon should be a proper macOS app icon.
  - "**We will use SwiftUI then.**"
  - The user sent videos of Wispr's pages and asked to "go into the Wispr app directory and copy all the pages and the business logic". **Declined**; originals only. Choices made by the user: real data first, drop the extras, modal like Wispr, skip some sections for now.

## Oct 1, night: the SwiftUI app and meeting notes

- **00:55:** the user ran out of credits; the engine was restarted.
- **01:28 onward, fixes:** "not in a text box should copy" broke and was fixed; "the widget and desktop app aren't connected" was reconnected; scrolling wasn't smooth.
- **02:14, permissions asked every time:**
  - A local signing certificate was made ("just do it").
  - The user asked for a reset ("just reset it for me"), which was declined, since the assistant doesn't change security settings. **The user ran `tccutil reset` themselves.**
- **02:36, meeting notes:**
  - "Make the meeting record look and act like this: opening a side window."
  - Incognito became a **top-right slider with a hover tip**.
  - The blurry home image was fixed.
  - A **Profile** in Settings (name, nickname, themes).
  - **Incognito never copies to the clipboard.**
- **02:47 onward, the main window:**
  - a **Prompts** page to edit the cleanup prompt;
  - more insights ("be creative");
  - a different look in Incognito;
  - the **fn key button** changes the dictation key to any key;
  - a **Notes** tab with past notes, people, durations and insights;
  - the 9-to-5 insight was fixed;
  - fake meetings and dictations for testing.
- **03:14, what kind of meeting** (Meet/Zoom/live): detected from the running apps.
- **03:18:**
  - **⌥M** records the screen's audio and the mic at once.
  - Colour coding for multiple people.
  - Click a person (or several) to see shared meetings.
  - An auto split-screen button.
  - A darker idle pill.
- **04:16–04:34, problems:**
  - The side panel didn't transcribe browser audio.
  - The panel was too large.
  - Permissions kept being re-asked. The user ran `trust_signing_cert.sh` and `tccutil reset ScreenCapture` themselves.
  - "**Male 1 / Female 1 / Person 1**" labels for unknown speakers.
  - It then worked, but "needs to update a lot faster" and "just stopped working".

## Oct 1, day: tests, meetings, voice commands

- **14:48–15:03:** finished, merged (**PR #15**), restarted.
- **15:05, test audit:** "check that every UI function has unit tests", and "**make sure you're tracking all the tests and what they do in the logs**" (`tools/test_catalog.py`). Branch `ui-tests`.
- **15:31, multi-person meetings** (branch `speaker-id`):
  - The user reported: "hard time with multiperson conversation", "updates slow", "can't identify same people", and asked "can't we do something like **cosine similarity** to compare voices?". The test video was the GitLab meeting (YouTube lBVtvOpU80Q).
  - Research on AMI meetings; voice embeddings with cosine similarity; a fast preview thread.
- **Requests that arrived while working on that**, all on the same branch ("**no do it in this branch**"):
  - **Auto-Enter** button beside Incognito, with a tooltip; a manual toggle.
  - **Delete old notes**; the side panel should ask before saving ("exit out is just exiting out"). The user chose: ask first, Save at the bottom "very appealing", delete in all four ways, plus delete/edit people and contact info ("you have fun").
  - **A voice app switcher key:** say an app to bring it forward; nicknames ("Scooby Snacks is Chrome", "set nickname"). "**The switch key can be a combo of keys too, or single.**"
  - **Later:** a **first-run tutorial**, and a **strict security audit** that nothing leaves the Mac.
- **16:28, echo:** with the call on speakers, lines duplicated as "You", so text-level echo removal was added. "Restart the app and screw replays" (a benchmark was stopped).
- **18:33, second meeting report:**
  - the same man switches Male 1/Male 2 ("needs to not ever happen");
  - women labelled male;
  - still slow;
  - echo still flashes "You".
  - The user suggested testing on their YouTube link, reading who's talking from the video. Lip tracking with macOS Vision was used, since there were no on-screen labels.
  - Also: **button clicks get transcribed** as "okay"/"thank you".
  - "If you can just stop now and restart."
- **19:14–19:16:**
  - "**Don't try and fix anything yet**", adding: Auto-Enter into a YouTube box copied instead of pasting.
  - Auto-Enter needs a **visual or audio cue**.
  - Settings needs a **sound off** switch (it already existed).
- **19:50:** "**let's do the voice detect stuff last**", so clicks (Silero), the echo gate, and speed came first.
- **21:12:**
  - "go back to the voice stuff, what's it called?" (speaker diarization).
  - "**be conservative with token usage**".
  - TitaNet diarization and gender were built. Merged into later work.
- **21:30–21:47, voice commands grew request by request:**
  - close, minimize, "expand";
  - "window layout Chrome beside VS Code" side by side, and "**Chrome 80%**";
  - close tab, new tab "and all the other settings";
  - pause and play, volume, "**mute mic / mute tab / mute app**", then "**unmute** for all the same";
  - "**skip forward/backward x seconds**";
  - "**scroll up and down**".
- **21:45–21:47, Home:** a section listing the computer-control commands, then "just put the important commands so it fits".
- **21:49–21:50, history:**
  - Commands weren't saved, so a **Commands tab** was added.
  - "I said Chrome but it opened Logic Pro", so matching became confident only.
- **21:55–22:05, folders:**
  - "**open folder**": the highest-level duplicate wins, it opens in Finder; in Finder "open _" goes into a subfolder or opens a file, or says "_ can't be found".
  - "Open clawed folder", "claud", "claude": sound-alike names.
  - "It can't find any of the folders" (macOS protects Documents). "**For the permission, just have the whole file system**" (Full Disk Access). "Make sure you added the permissions in the setup."
  - **Terminal:** "ls, flag a…", so terminal mode was added.
  - "**It doesn't fit on the page**", so setup got two permission pages.
- **22:10:** the Commands history should save **the proper spelling** of what was opened.
- **22:21–22:26:** "give me some tests to run… **on my end**" (a hands-on checklist); "not the Python test, only the UI".
- **22:51:** "**it should auto enter even in terminal**, if it's on Auto-Enter".
- **22:53:** "**just say quit**" quits the app you're in; commands don't need a name.
- **22:56:** "double check you have all the tests… **you don't need to run them**". The assistant ran some anyway; the user replied "I said don't run the test".
- **22:58:** commit, push, merge: **PR #16**.

## Oct 1, late: documentation

- **22:59:** a `documentation` branch: "update all the READMEs, create as many as possible to fully explain every feature, every test, everything", plus "a knowledge base so somebody can pass it into Claude and understand all the project and all the chat history". Merged as **PR #17**.
- **23:12:** "**You didn't update any of the other files like I asked. Do exactly what my prompt asked.**" So, on branch `documentation-2`:
  - every existing doc was brought up to date;
  - READMEs were added to every folder;
  - one page per test file, documenting every test;
  - data formats;
  - this history was rebuilt from the real messages;
  - the full chat log was exported.
- **23:14:** "Push everything and merge when it's all done."


---

<!-- knowledge-base/03-decisions.md -->

# 3. Decisions and why

| Decision | Why |
|---|---|
| Fully local, MIT, free | Privacy (cloud dictation sends audio to third parties), auditability, no subscription |
| Never copy Wispr's code, sounds or assets | The user asked twice and was declined. Originals only, with a similar feel |
| Python engine plus SwiftUI app | The engine came first (PyObjC). Native SwiftUI was chosen for the main window. JSON lines over stdin/stdout keep them separate and testable |
| whisper.cpp large-v3-turbo q5_0 | Best accuracy/speed/memory trade-off on Apple Silicon (~1.1 s for 5–6 s of speech) |
| Gemma-3-4B for cleanup, with a no-invented-words guard | Won the 27-case eval. The guard falls back to raw text, so cleanup can never add words |
| Paste only into text boxes; otherwise copy and give an error cue | Pasting into Finder or the desktop does nothing or does odd things |
| Incognito types instead of pasting and never copies | The clipboard is shared and may be synced or logged |
| Local signing certificate, trusted by the user | macOS permissions (TCC) are tied to the code signature; ad-hoc signing lost them on every rebuild |
| The assistant never changes security or privacy settings itself | It gives the user the commands (`tccutil`, keychain trust) instead |
| Meeting notes save only on Save | Closing should just close. Close or new-note asks Save / Discard / Keep editing |
| Previews on their own thread with base.en | Previews on the single final-text queue starved it. Separating them made previews 3.5× and finals 1.6× faster |
| TitaNet plus join/confirm/merge rules | The user said one person must "never" switch labels. Prefer merging lookalikes over splitting a person (0% splits on AMI) |
| Gender = fingerprint classifier averaged with pitch at 145 Hz | Pitch alone failed on Zoom audio (women ~150 Hz); the classifier alone was weak; together they're better |
| Echo: audio gate on the mic, plus text dedup | Text dedup alone left flashes in the live preview, and audio gating also halves the transcription work |
| Apple's voice-processing echo canceller not used | It ducks other apps' audio, so the call would get quieter |
| Silero VAD before Whisper | Clicks became "okay"/"thank you" (Whisper hallucination). VAD scores clicks as 0 s of speech |
| Voice commands use the apps' own keyboard shortcuts | Works in every browser and most apps without per-app integration |
| Weak app matches never launch apps that aren't running | "Pro." opened Logic Pro. Generic words never match; ambiguity does nothing |
| Folder search: Spotlight first, then a level-by-level walk; Soundex sound-alikes | Instant, any depth; the highest match wins; Whisper mishears names ("clawed") |
| Full Disk Access instead of per-folder prompts | The user's choice ("the whole file system"). Checked without prompting by reading the TCC database |
| Permission checks never prompt; only Allow… asks | The setup window refreshes on a timer |
| Terminal mode output must use only words that were said | Prevents the model from adding `rm`, `-rf`, etc. |
| Auto-Enter also in terminals | First skipped for safety; the user asked for it |
| "Mute app" isn't possible outside browsers | macOS has no per-app volume without a virtual audio driver; it says so and suggests "pause" |
| Mute mic mutes input volume; holding the switch key re-opens it briefly | Otherwise "unmute mic" couldn't be heard. fn dictation stays muted, so nothing leaks into a call |


---

<!-- knowledge-base/04-research.md -->

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


---

<!-- knowledge-base/06-open-items.md -->

# 6. Open items and roadmap

## Next (queued by the user)

1. **First-run tutorial** of every feature, for someone who just downloaded the app (after the UI work).
2. **Strict security audit** suitable for open-source distribution. Verify nothing is sent over the internet except the hash-checked model downloads, and write the audit into `logs/`.

## Known limits

- On Zoom-processed audio, similar voices (especially men) merge into one speaker.
- The echo gate needs a second or two to learn the speakers' leak.
- VS Code's integrated terminal isn't detected for terminal mode.
- "Mute app" works only for browser tabs.
- Seek uses arrow keys, 5 s per press (Netflix and others differ).
- If the app quits while the mic is muted, the mic stays muted.
- The click-filter test with the real Silero model is skipped, because the test setup redirects the models folder (a one-line fix).
- One Swift echo test uses random audio and failed once in many runs.

## Later

- Languages (Whisper supports ~99).
- A personal dictionary and snippets.
- An installable app for other Macs (DMG / `.pkg` with bundled Python).


---

<!-- knowledge-base/08-your-messages.md -->

# 8. Every message from the user, in order

Exported from the Claude Code transcript(s) by `tools/export_chat_history.py`. Times are UTC. Tool calls and their output are left out; the work they did is in `logs/` and git history. The project began in an earlier claude.ai chat ("Whispr Clone") that isn't included here.

1. *2026-09-30 14:56:42* look at my claude chat called Whispr Clone. We are building our own whispr desktop app that uses "fn" presses to active stt pipleline - set up a folder in /claude/ folder and connect it to git with an empty readme
2. *2026-09-30 15:03:38* ok let me explain the problem - whispr desktop app allows you to press twice (within 1s) or hold "fn" key to activate voice dictation. It then uses the audio uses stt - passes the text through a light model for clean up then pasts the text in the current window you are working in. If its in claude it pastes in chat window, gpt online same thing. The problem with this is that it does all the processing in the cloud meaning its storing my voice data which is a huge security read flag. I want to build a clone system that does the same thing then deletes the audio file (we can just put the data of the new audio file at the same memory location start as the other with zeros padding or something). Ask me question you need to help plan this. Also sumerize what ive said clean/sophisticated in the readme. also create a new branch called planning and push the changes to the repo in this branch
3. *2026-09-30 15:14:15* @"/Users/cyb/desktop/screen-grabs/Screen Recording 2026-09-30 at 11.11.00 AM.mov" ok lets first build the widget that floats near the bottem when the app is open. Heres a video on how it works - you can hover over it and press record icon and it records. in the record mode you can cancle ot accept the recording. then it puts what you said in the text box. note - holding fn records, double pressing fn records hands free. the wave form is also shown. any aditionaly questions?
4. *2026-09-30 15:23:18* @"/Users/cyb/desktop/screen-grabs/whispr-2-indepth.mov"  *(sent while Claude was working)*
5. *2026-09-30 15:34:50* ok now run it so I can see it
6. *2026-09-30 15:35:00* we might want to make this a dmg  *(sent while Claude was working)*
7. *2026-09-30 15:35:10* so that others can download  *(sent while Claude was working)*
8. *2026-09-30 15:38:43* unsigned for now, do the dmg after dictation works
9. *2026-09-30 15:41:28* yes start on fn and mic, use ~/Documents/voice-recordings
10. *2026-09-30 15:42:14* wait no  *(sent while Claude was working)*
11. *2026-09-30 15:42:14* ~/Documents/meeting-recordings.  *(sent while Claude was working)*
12. *2026-09-30 15:42:40* think you should create a new branch called build  *(sent while Claude was working)*
13. *2026-09-30 15:45:56* lets test this part first before moving on
14. *2026-09-30 15:49:19* @"/var/folders/5f/nm62gx911k5bnsq1p612rcfh0000gq/T/TemporaryItems/NSIRD_screencaptureui_yp9EDp/Screen Recording 2026-09-30 at 11.49.00 AM.mov" works good but there seems to be duplucate icons
15. *2026-09-30 15:52:20* two waveform icons in the menu bar only once u hover over it
16. *2026-09-30 15:54:21* it was for a good for a second there but the second one came back - close both apps and only open the new one. delete the other old stuff
17. *2026-09-30 15:54:58* oh  *(sent while Claude was working)*
18. *2026-09-30 15:55:00* nevermine  *(sent while Claude was working)*
19. *2026-09-30 15:55:02* stop  *(sent while Claude was working)*
20. *2026-09-30 15:55:43* restart it
21. *2026-09-30 15:56:50* looks ok - when hoving the 2 icons need more padding on the bottom and also need to be about 25% -50 taller length wise
22. *2026-09-30 15:59:50* another problem is when you double press the fn button it works and starts recording but mac also opens the emoji window - which doesnt happen in whispr flow. Another problem is that refer back to the video. the "transcript cancelled" should have an undo button beside it so that they can undo the cancel before the timer goes down
23. *2026-09-30 16:04:22* the double click fn is still opening emoji window, also use a better looking icon for the record button - it looks unprofesional
24. *2026-09-30 16:10:25* looks great - the double fn press still an issue. when the double press menu is up I want "space" key to mean accept and and "delete" key to delete
25. *2026-09-30 16:15:11* pressing "delete" when the "transcription cancle" window should automaticlly bypass the the countdown time and cancle the clip  *(sent while Claude was working)*
26. *2026-09-30 16:17:49* emoji window is gone now, move on to transcription - before we move on tho, the goal is at the end to have a downlaodable dmg that will allow people to download this desktop app if they have mac pro m1 series of greater, the widgets that we have now seem to be written in python? will this be an issue or will we have to convert everything into swift
27. *2026-09-30 16:20:32* you can push these changes as "widgets-fn-record-complete"  *(sent while Claude was working)*
28. *2026-09-30 16:27:29* it works, before we move on to the LLM cleanup, I want to note that when the final ui is done there will be a incognetdo slider that turns on the voice recoding instant delete. for now the defualt should be saving them in /voice-recordings folder because alot of our UI will be tracking stuff later, ok?
29. *2026-09-30 16:28:46* also make "spacebar" and "enter" both keys for accept and "fn" (during recording) or "delete" the cancle/discard  *(sent while Claude was working)*
30. *2026-09-30 16:29:59* Folder: ~/Documents/voice-recordings/YYYY-MM-DD/, one .wav file per recording (16 kHz mono, about 32 KB per second). - this naming convention sucks should be granular down to the millisecond - in the json it should also track what app it pasted in and if in browser what website link
31. *2026-09-30 16:32:48* restart it so I can see where the audio files are bing saved and confirm
32. *2026-09-30 16:33:56* lol dont be dumb when I give a file location I obv mean starting with the project path - ~/Documents/voice-recordings makes no sense
33. *2026-09-30 16:36:14* ok this works. whats next
34. *2026-09-30 16:36:50* llm cleanup lets go
35. *2026-09-30 16:37:45* wait lets first push our changes. what did we update and what should the name of the commit be
36. *2026-09-30 16:38:24* tag/push it v0.1-dictation and continue with llm cleanup
37. *2026-09-30 16:38:47* i have Qwen2.5 already installed  *(sent while Claude was working)*
38. *2026-09-30 16:38:49* look for it  *(sent while Claude was working)*
39. *2026-09-30 16:41:17* no I have it Qwen 2 somthing model trust me check the file system  *(sent while Claude was working)*
40. *2026-09-30 16:42:44* ok just download the one u wanted to  *(sent while Claude was working)*
41. *2026-09-30 16:43:09* and make it madatroy install setp in the programs startup process  *(sent while Claude was working)*
42. *2026-09-30 16:48:54* then use a better model for this. I cant have it making up stuff i didnt say
43. *2026-09-30 16:57:54* So really though, what’s the difference between just normal dictation and using this AI pipeline?  *(sent while Claude was working)*
44. *2026-09-30 17:01:21* ok only issue is how do we make it madatory download at the beginning of the dmg download proscess
45. *2026-09-30 17:01:26* or startup  *(sent while Claude was working)*
46. *2026-09-30 17:03:22* no now I want you to push changes with an appropriate title.
47. *2026-09-30 17:06:16* maybe im dumb but iv just been merging everythin to main on get website
48. *2026-09-30 17:06:32* says my build is 4 behind main  *(sent while Claude was working)*
49. *2026-09-30 17:07:52* ok next i want a coomit called unit tests. Every single function you’ve written so far that gives an output, I need you to make multiple or as many unit tests as possible for each function. Just so everything’s always working and functions that aren’t returning properly are flagged.
50. *2026-09-30 17:20:43* Sure, stress test the shit out of the test that you just created, and every test that fails, inspect it deeply and rewrite it using proper design patterns.
51. *2026-09-30 17:22:06* log all this stress testing  *(sent while Claude was working)*
52. *2026-09-30 17:22:15* and save it in /logs  *(sent while Claude was working)*
53. *2026-09-30 17:22:37* as todays_data_and_time_stresstest  *(sent while Claude was working)*
54. *2026-09-30 17:28:59* i also mean store the actual results of the stress test in the logs  *(sent while Claude was working)*
55. *2026-09-30 17:45:04* how long is this ganna take  *(sent while Claude was working)*
56. *2026-09-30 18:12:41* ok finsish up now and restart the app we got shit to do  *(sent while Claude was working)*
57. *2026-09-30 18:13:54* i gave you a whole whole this better work perfectly  *(sent while Claude was working)*
58. *2026-09-30 18:14:00* hour  *(sent while Claude was working)*
59. *2026-09-30 18:16:20* letsss goooo its taking to longgg  *(sent while Claude was working)*
60. *2026-09-30 18:25:53* restart
61. *2026-09-30 18:27:21* ok awesome work - name the commit and push to build
62. *2026-09-30 18:29:05* Now create a new branch called Rebranding
63. *2026-09-30 18:30:13* did you pause the widget or did it stop working after really long audio
64. *2026-09-30 18:31:35* go back into build branch and fix this  *(sent while Claude was working)*
65. *2026-09-30 18:33:40* track all this in /logs  *(sent while Claude was working)*
66. *2026-09-30 18:34:24* and whats happening  *(sent while Claude was working)*
67. *2026-09-30 18:41:12* do not rerunn all tests unless they impact the changes u made  *(sent while Claude was working)*
68. *2026-09-30 18:45:03* i dont see the push?
69. *2026-09-30 18:46:06* Okay, merge with main and then switch back to the rebranding.
70. *2026-09-30 18:48:48* [image attached]  Okay, now in rebranding, I want you to find every instance of the word W-H-I-S-P-R and change it to M-H-I-S-P-R. this is going to be the name of the app. also make this image the app icon and the git repo icon. Also change instances of "whispr ... clone " to "Mhispr_Flow"
71. *2026-09-30 18:50:39* All 93 replaced, and no "whispr" remains outside logs/. The competitor's name, "Wispr Flow", is untouched. Spot-checking the user-visible results: - even change the names in the logs  *(sent while Claude was working)*
72. *2026-09-30 18:53:00* yes
73. *2026-09-30 18:55:00* Okay, cool. Now create a new branch called… Oh no, actually just switch into the plan branch. Switch the file name of plan instead of all capitals. Do it under lower cases. And then also we need to now update the plan and update the README with all the new information about what we’ve done and how everything works.
74. *2026-09-30 18:55:23* Yeah, merge the rebranding with Maine first.  *(sent while Claude was working)*
75. *2026-09-30 18:56:45* Okay, I don't really care if you have to make a new branch or whatever. I just want the plan file and the README to be updated with all the new information and for you to create any other documents needed for support of how to run this program or how this program works.  *(sent while Claude was working)*
76. *2026-09-30 18:58:47* You can also add that Misper Flow was an M-H-I, whatever we just named it, is a clone of Whisper Flow that was created because one, I wanted it to be open source. Two, I wanted it to be free. Three, I didn't want my voice audio clips sent to the cloud and processed in their servers. And four, I wanted granular control over the icons, everything, so fully customizable and also supports multiple languages, etc., etc.  *(sent while Claude was working)*
77. *2026-09-30 19:00:19* i messed up the name of the real app is "Wispr Flow" so mine should be "Mispr Flow" or "Mispr" change it  *(sent while Claude was working)*
78. *2026-09-30 19:01:13* Okay, make a license file and then also make it so it can handle French and Spanish at the very least. perosnlly we should just do every language  *(sent while Claude was working)*
79. *2026-09-30 19:03:32* lets do that later  for now merge everything  and make sure the documentation is excelentt
80. *2026-09-30 19:03:51* ^  *(sent while Claude was working)*
81. *2026-09-30 19:03:51* and restart the app  *(sent while Claude was working)*
82. *2026-09-30 19:04:46* Merge everything.  *(sent while Claude was working)*
83. *2026-09-30 19:04:46* Where are we in the project timeline?  *(sent while Claude was working)*
84. *2026-09-30 19:15:34* <pasted_content id="4c33"> Comparing speech-to-text and summarization model benchmarks. Got it — two benchmarks, two winners needed. And you didn't answer the scope question yet either. Three quick ones:  1. STT engine benchmark (ticket 04) — which engine won on your M1? 2. LLM summarization benchmark (ticket 21) — which model won (still guessing Llama 3, or something else)? 3. Scope (ticket 01) — is LLM summarization now officially part of v1, or still a side add-on? </pasted_content id="4c33">
85. *2026-09-30 19:22:27* Let’s do first run set up screens permission checklist. Before we do all that though, I want to talk. Well, I mean, we kind of already decided to do it in Python, right? I just want to make sure, for sure, for sure, that it's still able to download a DMG. Like we're still able to bundle all this Python into a DMG executable. And I can send that to other people who have M1 plus MacBooks and it'll work on their laptop.
86. *2026-09-30 19:24:47* Okay, cool, that’s fine. Let’s begin.
87. *2026-09-30 19:27:36* delte this branch
88. *2026-09-30 19:27:56* First-run setup screens (permissions checklist) - ment start with this  *(sent while Claude was working)*
89. *2026-09-30 19:28:28* ask me  *(sent while Claude was working)*
90. *2026-09-30 19:31:17* make a new branch if ur making changes  *(sent while Claude was working)*
91. *2026-09-30 19:31:58* lets also delete - 2026-09-30_15-25-21_packaging-proof.md - if it doesnt matter  *(sent while Claude was working)*
92. *2026-09-30 19:39:58* up merge and lets talk about whats next
93. *2026-09-30 19:40:09* yup  *(sent while Claude was working)*
94. *2026-09-30 19:41:04* Okay, is there now a way to restart the app or restart it with the installer so I can go through everything and see how it opens?
95. *2026-09-30 19:43:09* I think I forgot to mention, but I want an actual app window. The widget that we created right now is only visible when the app window isn’t visible. That’s how it works. Refer back to the video. So I think we should work on the UI element before we do language or DMG or any of that stuff.
96. *2026-09-30 19:44:34* I’ll also make a new video for you of all the different screens that the UI has.  *(sent while Claude was working)*
97. *2026-09-30 19:44:34* Give me one moment.  *(sent while Claude was working)*
98. *2026-09-30 19:47:41* which is wispr made with
99. *2026-09-30 19:53:19* first lets go into the build - and change something quick - look thru the wispr flow app folder and find the sounds it makes for when the voice dictation starts and ends and implement the same sounds - also do this for any other audio sound effects you find that wispr desktop app uses so go thru its source code, then we will touch ui
100. *2026-09-30 19:54:40* @"/Users/cyb/desktop/screen-grabs/Screen Recording 2026-09-30 at 3.51.21 PM.mov" also on the first time you start using the dictation since the apps been open, it puts the name of the input mic name clearly visable - do the same  *(sent while Claude was working)*
101. *2026-09-30 19:56:37* ok then to make sure no copy right - I would like to to edit the audio clips and add some random spectrum noise that is undetectable by human ears - that way the wave form is techically altered and origianal  *(sent while Claude was working)*
102. *2026-09-30 19:57:30* yes just make them 99.99999% similar to the sounds  *(sent while Claude was working)*
103. *2026-09-30 19:58:18* also make the app icon - use the app image we have  *(sent while Claude was working)*
104. *2026-09-30 20:00:29* yes make original sounds with the same eaxact feel
105. *2026-09-30 20:06:53* It’s good like the startup makes a sound and the stop of the audio makes a sound, but pace doesn’t make a sound. So just double check that everything, all the sounds are hooked up to all the things that it can be hooked up to right now. Because obviously I know some of the sounds are UI dependent.
106. *2026-09-30 20:09:17* It makes the paste sound even when it doesn't successfully paste or there's no item to paste into. So make sure that when it doesn't paste into any text box that it makes the proper sound.
107. *2026-09-30 20:11:08* contiune
108. *2026-09-30 20:13:21* Update README, change log and plan.
109. *2026-09-30 20:15:14* Merge.
110. *2026-09-30 20:16:32* Okay, we’re going to be building UI now, so create a UI branch. And what I mean by app icon is, you know the bottom app icons on a MacBook with the big ones like system setting, messages, all that. I want ours to be like that every time it opens, but with our image, like our logo image.
111. *2026-09-30 20:17:16* Also, we never decided are we going to be making it in Swift or Python or which one’s the best? Which one did they use?  *(sent while Claude was working)*
112. *2026-09-30 20:19:04* We will use SwiftUI then.
113. *2026-09-30 20:19:34* @"/Users/cyb/desktop/screen-grabs/Screen Recording 2026-09-30 at 3.48.07 PM.mov" Here’s the app and all the pages. Ask me any questions you need.  *(sent while Claude was working)*
114. *2026-09-30 20:22:08* Why don't you make it easier on yourself and just go into the Whisper app directory and then look at how it renders its UI and then just copy all the pages and the business logic behind it.  *(sent while Claude was working)*
115. *2026-10-01 00:55:05* run the python backend again - it stoped bc i ran out of credits
116. *2026-10-01 00:57:57* restart
117. *2026-10-01 00:59:16* restart the app  *(sent while Claude was working)*
118. *2026-10-01 01:28:31* The feature where when you aren't in a text box, it still copies it to your paste thing isn't working anymore, Claude, so fix it. Come on.
119. *2026-10-01 01:31:42* now commit, make a good name, commit it, push it, and then we’re going to discuss the next item
120. *2026-10-01 01:34:56* I don't know what that means but can you fix it and then just run it and open the UI?
121. *2026-10-01 01:38:21* yo cluade the widget and deskapp arnt connected. shit keeps breaking  *(sent while Claude was working)*
122. *2026-10-01 01:41:44* the scrolling is not smooth at all
123. *2026-10-01 02:14:35* it has all ther permisions arlredy - it shoulfd not need to reload them everytime that dumb
124. *2026-10-01 02:19:45* rerun it
125. *2026-10-01 02:20:29* <bash-input>tools/make_signing_cert.sh</bash-input><bash-stdout>zsh: no such file or directory: tools/make_signing_cert.sh</bash-stdout><bash-stderr></bash-stderr>
126. *2026-10-01 02:20:55* just do it
127. *2026-10-01 02:22:30* [image attached]  still doesnt have the permisions even tho u click it and its alrady toggelled on
128. *2026-10-01 02:23:04* just reset it for me
129. *2026-10-01 02:23:18* <bash-input>tccutil reset Accessibility io.github.maxwelldalrymple.MisprFlow</bash-input><bash-stdout>Successfully reset Accessibility approval status for io.github.maxwelldalrymple.MisprFlow</bash-stdout><bash-stderr></bash-stderr>
130. *2026-10-01 02:33:26* its fine but when you restart it it better know that everything already permitted
131. *2026-10-01 02:36:10* @"/Users/cyb/desktop/screen-grabs/whispr-1.mov" now make the meeting record look and act like this - opening a side window - make it exact same
132. *2026-10-01 02:37:36* also make incogonito mode a slider in the top right corner with a hover info tip that explains  *(sent while Claude was working)*
133. *2026-10-01 02:39:53* also the image used in the home page of the app looks really blury  *(sent while Claude was working)*
134. *2026-10-01 02:41:07* also have it so it has "profile" in settings where you can change name, nickname, theme (add like 5 cool colour themes) and other stuff that would be in a profile setting page  *(sent while Claude was working)*
135. *2026-10-01 02:43:31* also in incoginito mode - it should never copy to clip board - either pastes in a text box or nothing  *(sent while Claude was working)*
136. *2026-10-01 02:47:00* Now we should change style to something more related to prompting and the page should give like options like text areas to put in system prompts for how the model cleans and actually outputs the text. Also put in that box the current prompt they’re using right now for cleaning but yeah I want to be able to change that prompt for whatever we want.
137. *2026-10-01 02:47:54* also add more cool insights to the page, be creative  *(sent while Claude was working)*
138. *2026-10-01 02:49:06* Also, something should be different when you’re in incognito mode. I don’t know exactly what, but it should look a little different, just so when you toggle back and forth, you clearly know you’re in incognito.  *(sent while Claude was working)*
139. *2026-10-01 02:49:53* In the settings page also make the button FN so you can click on it and change it to different any key that you want to trigger it.  *(sent while Claude was working)*
140. *2026-10-01 02:51:26* Also should have a tab that says notes where you can access all your old notes and go through and it should show who was in the meetings, what their name was, the duration of the talk. And in the notes thing, there should also be like an insights tab. When you go into a notes meeting, like one meeting, should you be able to click into it and it’ll show you all the insights, the names of the people, blah, blah, blah.  *(sent while Claude was working)*
141. *2026-10-01 02:56:32* The nine to five isn't working. Also add more insights because your creativity is awesome. Keep going.  *(sent while Claude was working)*
142. *2026-10-01 03:00:20* And I’ll make more for the Your Voice Insights.  *(sent while Claude was working)*
143. *2026-10-01 03:01:11* In the settings-general page also make the button FN so you can click on it and change it to different any key that you want to trigger it.  *(sent while Claude was working)*
144. *2026-10-01 03:05:43* Everything’s working great. The next step would be making some fake data for the recording page, just because I just don’t have a meeting going on, so I need you to create, let’s say, three to four fake meetings before, each on an average duration of like 10 minutes. Make up whatever text you want about it, but I just want the output of what the page will look like to actually be like that, and then I’ll test the actual record feature for the meeting and see how that goes too.  *(sent while Claude was working)*
145. *2026-10-01 03:08:44* I also add some fake data for the actual voice text homepage. I just want to make sure that it works for multiple days or whatnot. You don't need to actually make it from the audio files. Just put placeholders. I just want to make sure that it’ll work. If you want, make some fake audio files. Honestly, that’ll probably be the best thing. But I just want to make sure that it really works.  *(sent while Claude was working)*
146. *2026-10-01 03:14:21* how would it now if it was google meet or a zoom or live meeting just being recorded. create a solution
147. *2026-10-01 03:18:41* @"/Users/cyb/desktop/screen-grabs/Screen Recording 2026-09-30 at 11.15.35 PM.mov" make it behave like this, also have the ^M stuff. its able to audio record on ur screen and mic at the same time
148. *2026-10-01 03:21:18* make sure if theres multiple people it adds sum colour cordination  *(sent while Claude was working)*
149. *2026-10-01 03:22:56* [image attached] seems broken  *(sent while Claude was working)*
150. *2026-10-01 03:25:50* [image attached] you should be able to click on each person and it brings up all the meetings you attended together, also if you select multiple all the meetings you all were present - add other usefull features or sup pages whatever u think  *(sent while Claude was working)*
151. *2026-10-01 03:28:03* [image attached] [image attached] make this button that autmaticlly splits windows when in a meeting, google meets, zoom, teams, etc  *(sent while Claude was working)*
152. *2026-10-01 03:50:00* ok resatart
153. *2026-10-01 03:51:46* "you should be able to click on each person and it brings up all the meetings you attended together, also if you select multiple all the meetings you all were present - add other usefull features or sup pages whatever u think" u didnt do this?
154. *2026-10-01 03:57:25* [image attached]  [image attached]  make the bottom widget a little more dark llike this
155. *2026-10-01 04:03:31* restart the app from the beginning im making a screen reordoing of it
156. *2026-10-01 04:16:08* the notes side panel isnt trascibing meeting from my broswer
157. *2026-10-01 04:20:53* For some reason the meeting recording side panel is so large now it doesn't even fit on the screen.
158. *2026-10-01 04:23:35* The same problem keeps happening. It keeps asking for all the same permission. But if you go in, it says sliders on. It has permission, but it always asks for permission and it never works. It can never connect.
159. *2026-10-01 04:26:38* It’s still not working. And also a good thought is when you don’t know who the speaker is, you just say like male one or male two or female one or female two or unknown one, unknown two or person one, person two or animal one. You know, just make it fit.
160. *2026-10-01 04:30:39* <bash-input>/Users/cyb/documents/software-projects/claude/Mispr_Flow/tools/trust_signing_cert.sh</bash-input><bash-stdout>Trusted "Mispr Flow Local Signing" for code signing. Now reset the old grant, then allow Mispr Flow once more and restart it:   tccutil reset ScreenCapture io.github.maxwelldalrymple.MisprFlow</bash-stdout><bash-stderr></bash-stderr>
161. *2026-10-01 04:30:47* <bash-input>tccutil reset ScreenCapture io.github.maxwelldalrymple.MisprFlow</bash-input><bash-stdout>Successfully reset ScreenCapture approval status for io.github.maxwelldalrymple.MisprFlow</bash-stdout><bash-stderr></bash-stderr>
162. *2026-10-01 04:31:06* <bash-input>osascript -e 'quit app "Mispr Flow"'; sleep 2; open "/Users/cyb/documents/software-projects/claude/Mispr_Flow/build/Mispr Flow.app"</bash-input><bash-stdout>[No output was captured. The command ran in the terminal pane (tab 0); if it should have printed something, use read_terminal with tab_id "0" to check.]</bash-stdout><bash-stderr></bash-stderr>
163. *2026-10-01 04:31:27* <bash-input>tccutil reset ScreenCapture io.github.maxwelldalrymple.MisprFlow</bash-input><bash-stdout>Successfully reset ScreenCapture approval status for io.github.maxwelldalrymple.MisprFlow</bash-stdout><bash-stderr></bash-stderr>
164. *2026-10-01 04:31:40* <bash-input>osascript -e 'quit app "Mispr Flow"'; sleep 2; open "/Users/cyb/documents/software-projects/claude/Mispr_Flow/build/Mispr Flow.app"</bash-input><bash-stdout>[No output was captured. The command ran in the terminal pane (tab 0); if it should have printed something, use read_terminal with tab_id "0" to check.]</bash-stdout><bash-stderr></bash-stderr>
165. *2026-10-01 04:32:03* <bash-input>osascript -e 'quit app "Mispr Flow"'; sleep 2; open "/Users/cyb/documents/software-projects/claude/Mispr_Flow/build/Mispr Flow.app"</bash-input><bash-stdout>[No output was captured. The command ran in the terminal pane (tab 0); if it should have printed something, use read_terminal with tab_id "0" to check.]</bash-stdout><bash-stderr></bash-stderr>
166. *2026-10-01 04:34:02* It worked, the permissions worked, and I was able to transcribe some stuff I’m hearing. But one, it needs to update a lot faster. As soon as it hears it, I want to see it on the screen. Also, two, it just stopped working for some reason.
167. *2026-10-01 05:51:37* I hit my usage limit while you were working, but it has reset now. Please continue from where you left off.
168. *2026-10-01 14:48:43* fishish what you were doing
169. *2026-10-01 14:57:00* merge it
170. *2026-10-01 14:57:46* merge
171. *2026-10-01 15:03:22* restart the app
172. *2026-10-01 15:05:02* first lets check that ever UI function has unit tests. make sure all functions do any tests as each function as it needs
173. *2026-10-01 15:11:06* make sure your tracking all the tests and what they do in the logs  *(sent while Claude was working)*
174. *2026-10-01 15:31:29* the notes transcribe feature is having a hard time with multiperson conversation. it also updates slow at shit, and cant identify same people. cant we do something like cosign simularity to compare voices? we gatta fix that. also its slow - here are the video i used to test https://www.youtube.com/watch?v=lBVtvOpU80Q
175. *2026-10-01 15:42:52* [image attached] in the top bar - beside or something ingoc - there needs to be an automatic input icon you can click with a toop that explains but - basliclly it will press enter for you when you are in a text box so you can just talk - but needs to be a button they press so they manully set the overide  *(sent while Claude was working)*
176. *2026-10-01 15:43:43* no do it in this branch  *(sent while Claude was working)*
177. *2026-10-01 15:46:41* Also, right now, there's no way in the note taker tab to delete old notes that you don't want or anything. And then also we need to talk about the side panel. That’s when you exit out of the side panel, there should be like a save button. Because if you just exit out, it shouldn't save all the meetings that you don't want saved. Like, you know, like I thought exit out is just exiting out.  *(sent while Claude was working)*
178. *2026-10-01 15:53:31* I also want to add a new feature now that if you hold another key, like we’ll put it in the settings or whatnot, but this is going to be like the window select key. Basically, when you hold that, same thing happens like for the audio, but when you press enter, whatever application you say, it brings it to the foreground. So if I say Chrome, it puts Chrome at the foreground. If I say terminal, it puts terminal. And also you can set nicknames. So you can just say like C, like the letter C or C for Chrome or L for, you know, just say or random like Scooby Snacks is Chrome or whatever. All you have to say is set nickname or something to Chrome.  *(sent while Claude was working)*
179. *2026-10-01 15:56:11* Also, to note, after we’re done with the UI, I want to set up, when you first download it, a tutorial guide of all the different things and features for somebody fresh who just downloaded it.  *(sent while Claude was working)*
180. *2026-10-01 15:58:48* We also need to remember that we need to do a strict security audit in compliance with open source downloadable code. I also want to ensure that anything is never being sent over the Internet and everything is remaining local, given our plan. And then we'll write, obviously, all the security audit into log files.  *(sent while Claude was working)*
181. *2026-10-01 16:01:16* the switch key can be a combo of keys too  *(sent while Claude was working)*
182. *2026-10-01 16:01:39* or single  *(sent while Claude was working)*
183. *2026-10-01 16:25:55* restart the app and screw replays
184. *2026-10-01 16:28:44* [image attached]  I think the problem is that the screen is playing something, but then I also have it playing out loud in speakers because I don’t have it on headphones. So there’s cases where that’s going to be normal, right? But it’s making everything duplicate. And I’ll just send you a screenshot quick too.
185. *2026-10-01 18:26:41* restart it -
186. *2026-10-01 18:33:03* Okay, it's still not able to detect when one person speaking. It'll switch between male one and male two, even though it's the same guy. That needs to not ever happen. Two, it can't even pick up if it's a female voice or not. It says male. So actually do the detection if it's female or male. And then three, it's still slow. It's not updating fast enough. And four, the echo effect still happening where because I'm playing it out loud on a speaker, it flashes that it's me talking for a second, even though it has like two bars. It'll say male and you, and it'll say the same words, filling out at the same time for both of us, even though it should just be doing it for the male. Like I'm just have my shit on speaker.
187. *2026-10-01 18:35:10* https://www.youtube.com/watch?v=lBVtvOpU80Q - Use this link to test the model because you can see who’s talking based off of obviously OSR and then you can know their voice because whatever and just test that it actually works.  *(sent while Claude was working)*
188. *2026-10-01 18:44:33* Also something to note is when you click on the buttons while you’re recording the meeting and stuff, sometimes the buttons make it sound like you’re saying something. So the dictation will think you’re saying like, okay, or thank you, or whatever. Try to find a way to just remove like little button clicks. Like, you know, I feel like that’s going to be an issue.  *(sent while Claude was working)*
189. *2026-10-01 19:05:08* if you csn just stop now and restart  *(sent while Claude was working)*
190. *2026-10-01 19:14:44* Don’t try and fix anything yet, but also add that for some reason it’s not putting it in like a YouTube text box. Like when I put it, it says it copies it to the paste, whatever, instead of just putting it in and entering. I’ll try with the other way without automatic enter.
191. *2026-10-01 19:16:04* Yeah, it only happens when it’s on the automatic enter mode. Also, automatic enter mode should have like some sort of visual cue or auditory cue that you actually are in that mode. And then the settings should also have a turn off sound feature.
192. *2026-10-01 19:41:32* I hit my usage limit while you were working, but it has reset now. Please continue from where you left off.
193. *2026-10-01 19:50:52* lets do the voice detect stuff last
194. *2026-10-01 20:53:54* restart and tell me what u fixed
195. *2026-10-01 21:12:19* Okay, now we can go back to fixing the voice stuff, but what’s it called? But yeah, remember that we don't have a crazy amount of tokens, so try to be conservative with the token usage.
196. *2026-10-01 21:20:38* restart the app
197. *2026-10-01 21:27:21* ok - what else should i see that works UI wise
198. *2026-10-01 21:30:18* app swittcher works so far- but we need to add "close" "minimize" "expain" " window layout chrome beside vscode" - and it puts it beside vertcal - also make it so u can say "chrome 80%" and it makes the chrome window 80% of the screen
199. *2026-10-01 21:32:34* also need like close tab - new tab - and all the other settings that come with it
200. *2026-10-01 21:36:05* restart the app
201. *2026-10-01 21:37:17* should be able to pause and play on any app, volume increase drease - mute my mic "mute mic" "mute tab" "mute app"
202. *2026-10-01 21:39:55* ok then "unmute" for all the same settings
203. *2026-10-01 21:41:53* "skip foward/backward x seconds"
204. *2026-10-01 21:42:45* scoll up and down  *(sent while Claude was working)*
205. *2026-10-01 21:44:15* restart the app
206. *2026-10-01 21:45:23* [image attached]  add another section that talks about all the computer control commands too
207. *2026-10-01 21:47:31* the ui is messed up now, just put the inportant commands so it fits in the screen
208. *2026-10-01 21:49:20* It’s also not saving the command, the computer commands you send in the text chat history window. What’s going on with that?
209. *2026-10-01 21:50:03* Make them its own history page like tab that says commands.  *(sent while Claude was working)*
210. *2026-10-01 21:50:27* And I said Chrome, but for some reason I thought I said Logic Pro. So can we make sure that it really is confident on what I said because I don’t want to open up random apps.  *(sent while Claude was working)*
211. *2026-10-01 21:55:16* also have "open folder" - and it opens to the folder location u say. if there are duplicates goes to the highest level folder - opens the folder in finder - once in finder if u say "open _" it opens the folder in the same finder if its in the sub dir - opens file if in sub dir - says "_" cant be found in dir
212. *2026-10-01 21:56:16* Make sure you added in the permissions at the beginning in the setup.  *(sent while Claude was working)*
213. *2026-10-01 22:00:47* "Open clawed folder." instead of open clawed.
214. *2026-10-01 22:01:10* claud  *(sent while Claude was working)*
215. *2026-10-01 22:01:10* claude  *(sent while Claude was working)*
216. *2026-10-01 22:01:10* It also can't find any of the folders so it's got to search for them.  *(sent while Claude was working)*
217. *2026-10-01 22:02:13* For the permission, just have the whole file system.  *(sent while Claude was working)*
218. *2026-10-01 22:03:30* Also, when you’re in the terminal, there’s going to be stuff like ls, flag a, blah, blah, blah. We need to make sure that when in the terminal specifically, that the LLM knows that it should be optimizing for terminal code language.  *(sent while Claude was working)*
219. *2026-10-01 22:05:09* You have to make sure that it fits on the page better because visually that doesn't look good. Make all the sections smaller then I guess. Or just have it on two pages that you have to click to accept all the permissions.  *(sent while Claude was working)*
220. *2026-10-01 22:08:50* restart the app
221. *2026-10-01 22:10:48* In the commands history, it needs to save the text that actually opened it. Like right now it’s saying open Claude folder. But with the proper spelling, it needs to save the proper spelling.
222. *2026-10-01 22:11:04* clawed  *(sent while Claude was working)*
223. *2026-10-01 22:15:58* restart the app
224. *2026-10-01 22:21:33* Everything looks like it’s working well, but should I give some tests to run just so we can do the last checks of everything and then we’re going to move on to the final stage.
225. *2026-10-01 22:22:13* Not the Python test. We only need whatever is the UI.  *(sent while Claude was working)*
226. *2026-10-01 22:25:57* I meant on my end, just give me some things to do so I can test if it works, everything works.  *(sent while Claude was working)*
227. *2026-10-01 22:51:27* no should auto enter even in terminal
228. *2026-10-01 22:51:38* if its on auto enter  *(sent while Claude was working)*
229. *2026-10-01 22:53:34* You should just be able to say quit when you’re in an app on the whatever and it quits for you or the commands, but you don’t have to like say the name as long as the app that you’re open with.
230. *2026-10-01 22:55:59* restart
231. *2026-10-01 22:56:48* Cool, double check that you have all the tests written. You don't need to run them all, but make sure that you still have the benchmark of all the tests passing.
232. *2026-10-01 22:57:36* I said don't run the test.  *(sent while Claude was working)*
233. *2026-10-01 22:58:11* Alright, let's commit and push merge
234. *2026-10-01 22:59:29* Okay, now create a branch called documentation. What we’re going to be doing is we’re going to be updating all the readmes and creating as many readmes as possible to fully explain every feature, every test, everything to do with this code base. I also want you to create a knowledge base so that somebody can just pass it into their cloud and automatically understand all the project we did and all the chat history we’ve done.
235. *2026-10-01 23:11:12* push and merge it
236. *2026-10-01 23:12:09* You didn't update any of the other files like I asked. Do exactly what my prompt asked.
237. *2026-10-01 23:14:45* Push everything and merge when it’s all done.  *(sent while Claude was working)*


---

<!-- docs/features/dictation.md -->

# Dictation

Hold a key, speak, let go: clean text appears in the app you're typing in. Everything runs on your Mac.

## Keys and gestures

| Do this | To |
|---|---|
| Hold `fn` (or your dictation key), speak, release | Push-to-talk: pastes when you let go |
| Double-tap the key (within 1 s) | Hands-free: keeps listening |
| `space` / `return` / `enter` while hands-free | Finish and paste |
| `delete` or the key while hands-free | Cancel ("Transcript cancelled · Undo" for 5 s) |
| `delete` on the Undo toast | Discard now |
| Click the widget's mic / long-press it | Hands-free / push-to-talk with the mouse |

- A quick tap does nothing, and `fn` + another key (fn + arrow) works as normal.
- **Choose any dictation key** in Settings → General: `fn`, one side of a modifier (Right ⌥), or a key (F5). Keys that would break hands-free (space, return, delete, Esc, Caps Lock) can't be picked.

## What happens to your words

1. **Transcription:** whisper.cpp, `large-v3-turbo` quantized, on the GPU. About 1.1 s for a 5–6 s clip.
2. **Cleanup:** Gemma-3-4B removes "um/uh/like", repeats and retracted phrases ("Tuesday, no wait, Wednesday" → "Wednesday"), and fixes punctuation. A code-level guard rejects any output with a word you didn't say; then the raw transcript is pasted instead. Edit the cleanup instructions on the **Prompts** page.
3. **Where it goes:**
   - **A text box is focused:** it pastes, then restores your clipboard (the dictated text is marked private so clipboard managers skip it).
   - **No text box** (Finder, the desktop, a page with nothing focused): nothing is pasted. The error sound plays, and the text is left on the clipboard with "No text box · Copied to clipboard".
   - **Browsers:** if a browser says "no text box", it checks once more 0.15 s later (YouTube's comment box takes focus as it opens). The log records what was focused.
4. **History:** audio plus a JSON record is saved under `voice-recordings/YYYY-MM-DD/`, unless Incognito is on.

## Incognito

The switch in the window's top-right corner (it turns purple, and so does the widget's outline).

- Nothing is written to disk.
- The audio lives only in locked RAM and is wiped after transcription.
- Text is **typed** instead of pasted, so it never touches the clipboard. With no text box, nothing is copied at all.

## Auto-Enter

The ⏎ button left of Incognito. When on, Return is pressed 0.25 s after your text lands in a text box, so chat messages send themselves.

- It never presses Return if the text was copied rather than pasted.
- **In terminals it runs the command too**; turn it off to check commands first.
- **Cues:** a blue ⏎ badge on the widget's corner while it's on, and a chime with an "Auto-Enter on/off" notice when it changes.

## Terminal mode

Dictating into Terminal, iTerm, Warp, Ghostty, kitty, Alacritty, WezTerm, Hyper, Tabby or Rio turns spoken syntax into shell syntax:

| Say | Typed |
|---|---|
| ls flag a | `ls -a` |
| LS dash L A | `ls -la` |
| cd tilde slash documents slash projects | `cd ~/documents/projects` |
| git commit dash m quote fix the login bug quote | `git commit -m "fix the login bug"` |
| grep dash r todo dot pipe head | `grep -r todo . \| head` |
| python three dash m pytest dash dash verbose | `python3 -m pytest --verbose` |
| npm run dev and and open localhost colon three thousand | `npm run dev && open localhost:3000` |

- The cleanup model gets terminal instructions, but its answer is used only if **every word in it was said**, so it can't add a command or flag (`rm`, `-rf`). Otherwise a plain word-for-symbol converter is used. Code: `mispr/terminal.py`.
- VS Code's built-in terminal isn't detected; its editor and terminal can't be told apart.

## The widget

The pill above the Dock:
- a live waveform while you talk, a spinner while it's working;
- hands-free ✓ / ✕ buttons and tooltips;
- on the first dictation after launch it names the mic in use;
- it follows the screen you're on and hides in fullscreen apps.

Hover it for the mic and ◉ (meeting note) buttons.

## Sounds

Every event has its own original sound: start, stop, lock, paste, cancel, alert, error, success, achievement. They're generated by `tools/make_sounds.py`. Turn them off in Settings → System → "Dictation and notification sounds".


---

<!-- docs/features/voice-commands.md -->

# Voice commands (app switcher)

Control your Mac by voice.

1. Pick an **app switcher key** in Settings → General. It can be:
   - a key (F5);
   - one side of a modifier (Right ⌥);
   - a combo of modifiers held together (⌃⌥);
   - modifiers plus a key (⌥S).
2. Hold it and say a command.
3. Let go.

The widget confirms what happened ("→ Google Chrome", "Volume 55%"). The command, with the real names, is saved in Home → **Commands** history (not in Incognito).

**Rules for every command:**
- With no app named, a command acts on **the app you're in**.
- Words like "please", "go", "open" in front are ignored.
- Numbers can be spoken ("eighty percent").

## Apps and windows

| Say | Does |
|---|---|
| "Chrome", "open the terminal", "switch to Slack" | Brings the app to the front (launches it if needed) |
| "close" / "close Chrome" | Closes the front window (doesn't quit) |
| "minimize" / "hide" | Minimizes the front window |
| "expand" / "maximize" | Fills the screen (menu bar and Dock stay) |
| "quit" / "quit Slack" / "exit" | Quits the app normally (it can still warn about unsaved work) |
| "Chrome beside VS Code" (also "put … next to …", "window layout …") | Side by side, half each; the first app named ends up in front |
| "Chrome 70% beside VS Code" | Chrome 70% of the width, VS Code the rest |
| "Chrome 80%" / "make Slack sixty percent" | That share of the screen's width and height, centred |
| "set nickname C to Chrome" | From then on, "C" means Chrome. Nicknames can also be managed in Settings → General |

**Never opening the wrong app.** A whisper of "Pro." once opened Logic Pro; now:
- **Strong matches may launch an app that isn't running:** a nickname, the exact name, the name without spaces ("face time"), or one distinctive word of 5+ letters ("chrome").
- **Weak matches only switch to apps already open:** a short word ("code"), a prefix ("term"), or a sound-alike ("sapari").
- **Generic words never match:** "pro", "app", "studio", "desktop", "mac"…
- **Shared words:** "chrome" means Google Chrome over Chrome Remote Desktop. A real toss-up does nothing.

## Tabs and pages (the app's own shortcuts)

| Say | Shortcut |
|---|---|
| new tab / close tab / reopen tab | ⌘T / ⌘W / ⇧⌘T |
| next tab / previous tab / tab 3 / last tab | ⌃⇥ / ⌃⇧⇥ / ⌘3 / ⌘9 |
| new window / close window / incognito (private) window | ⌘N / ⇧⌘W / ⇧⌘N |
| reload ("refresh") / back / forward | ⌘R / ⌘[ / ⌘] |
| address bar / find / bookmark | ⌘L / ⌘F / ⌘D |
| zoom in / zoom out / reset zoom / full screen | ⌘= / ⌘- / ⌘0 / ⌃⌘F |

Add "in Chrome" (or say "Chrome new tab") to bring that app forward first.

## Sound and media

| Say | Does |
|---|---|
| "pause" / "play" / "next song" / "previous track" | Media keys: whatever is playing |
| "skip forward 30 seconds" / "rewind 10 seconds" / "jump ahead 2 minutes" | Arrow keys, one press per 5 s (YouTube, web players, QuickTime) |
| "volume up" / "louder" / "volume down" / "volume 40%" | Output volume |
| "mute" / "unmute" | The Mac's sound |
| "mute mic" / "unmute mic" | Input volume to 0 and back. While muted, holding the switch key opens the mic just to hear you, so "unmute mic" works by voice |
| "mute tab" / "unmute tab" | Chrome, Brave, Edge, Arc: the tab menu's "Mute site". Directional, never toggles back |
| "mute Spotify" | In a browser it mutes the tab. macOS can't mute one app without extra audio software, so elsewhere it says so |

## Scrolling

| Say | Does |
|---|---|
| "scroll down" / "scroll up" | About half a screen, under the pointer |
| "… a little" / "… more" / "… a lot" / "… 3 times" | Less, more, repeat |
| "page down" / "page up" | About a screen |
| "scroll to the top" / "scroll to the bottom" | ⌘↑ / ⌘↓ |

## Folders and files

| Say | Does |
|---|---|
| "open folder Projects" / "open the Downloads folder" | Finds it under your home folder and opens it in Finder; the highest-level match wins if there are duplicates |
| In Finder: "open Taxes" | A folder inside the one you're viewing opens **in the same window** |
| In Finder: "open Budget" | A file inside it opens in its app (no need to say ".xlsx") |
| In Finder, nothing matches | "“receipts” can't be found in Docs" (or, if it's clearly an app, switches to it) |

**How folders are found:**
- Spotlight first (instant, any depth), then a level-by-level search as a backup.
- Names are loose: "mispr flow" finds `Mispr_Flow`.
- Sound-alikes count when nothing has the exact name: "clawed" / "claw to" → `claude` (Soundex).
- Hidden folders, Library and build/dependency folders are skipped.

**Permissions** (setup's **Optional features** page):
- **Full Disk Access**, so Documents, Desktop and Downloads can be searched.
- **Control Finder**, for same-window navigation.

Code: `mispr/apps.py` (parsing, matching, actions), `mispr/hotkey.py` (the switch key), `mispr/widget.py` (`switch_key`, `_do_switch_command`).


---

<!-- docs/features/meeting-notes.md -->

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


---

<!-- docs/features/notetaker.md -->

# Notetaker and People

The **Notetaker** page in the main window.

## Notes

- Past meetings grouped by day, with search across titles, people and transcripts.
- Click a note for its Summary, Transcript, Insights (talk time, longest stretch, turns per minute, questions, topics) and My thoughts.
- **Delete**, always after a "can't be undone" confirmation:
  - a trash button when you hover a note;
  - right-click → Delete…;
  - the Delete button on a note's page;
  - **Select** mode: tick several, then Delete.
- Deleting removes the note and its audio.

## People

- Everyone from your meetings. Click someone to see your meetings together, talk share, topics and their action items. ⌘-click several people to see only the meetings you were all in.
- **Edit name & details…** (right-click or ⋯):
  - **Rename** updates every note: participants, transcript lines, action items. Renaming onto an existing person merges them.
  - **Contact card:** role, company, email (click to mail), phone, notes. Stored in `meeting-recordings/people.json`.
- **Remove from People…** keeps the notes; that person's lines become "Unknown speaker".

## Insights tab

Patterns across all meetings: count, time in meetings, your talk share, open action items, who you meet with most, your busiest day.


---

<!-- docs/features/main-window.md -->

# The main window

A SwiftUI app (`macos/`). The Dock icon opens it; it hosts the Python engine in the background.

## Top bar

- **Auto-Enter (⏎)** and **Incognito** switches, each with a hover explanation.
- Your **profile photo**, which opens Settings → Profile.

## Pages

- **Home:**
  - a greeting and your dictation key;
  - **history** with tabs **Dictation | Commands**, search, playback, copy and delete;
  - side cards: stats (words, wpm, streak), **Shortcuts**, and **Voice commands** (the most useful ones, or a link to set up a switch key).
- **Insights:** pace, streaks, time saved, where your words go, your voice profile, and many fun facts, from your saved dictations.
- **Notetaker:** see [notetaker.md](notetaker.md).
- **Prompts:** edit the cleanup model's instructions, rules and examples, then **Try it** live. They're saved to `prompts.json` and used by the engine at once.
- **Settings** (a modal):
  - **Profile:** name, nickname, photo, and 6 colour themes plus appearance.
  - **General:** dictation key, app switcher key and nicknames, microphone, language, cleanup.
  - **System:** launch at login, sounds, Setup guide.
  - **Privacy.**

## Data

- Settings: `~/Library/Application Support/Mispr_Flow/settings.json`, shared with the engine.
- Dictations: `voice-recordings/`. Meetings: `meeting-recordings/`.

Sample-data tools (`tools/make_sample_dictations.py`, `make_sample_meetings.py`) fill these for screenshots and testing.


---

<!-- docs/features/setup-and-permissions.md -->

# Setup and permissions

A setup window appears on first launch, and again whenever something required is missing. Reopen it from the menu bar: **Setup Guide…**

1. **Welcome**
2. **Allow access** (required): **Microphone**, **Accessibility** (captures the dictation key, pastes, reads the browser URL)
3. **Optional features** (skippable):
   - **Screen & System Audio:** meeting notes hear the other people on a call.
   - **Full Disk Access:** "open folder" can search Documents, Desktop and Downloads. macOS has no prompt for this one, so Allow… opens the System Settings list; switch Mispr Flow on there.
   - **Control Finder:** "open …" in Finder opens folders in the same window. This is macOS's Automation prompt.
4. **Models:** downloads Whisper turbo (0.57 GB) and Gemma (2.5 GB) with SHA-256 checks.
5. **Ready**

Meeting-only models (`base.en`, TitaNet, Silero) download the first time you take meeting notes.

**How permissions are checked without nagging:**
- The window re-checks permissions on a timer without triggering prompts. Finder uses `AEDeterminePermissionToAutomateTarget` without asking; Full Disk Access reads the protected TCC database.
- Only clicking **Allow…** asks.

**Keeping permissions across rebuilds:** the app is signed with a local certificate, "Mispr Flow Local Signing" (`tools/make_signing_cert.sh`, made trusted with `tools/trust_signing_cert.sh`). If permissions keep resetting, see [troubleshooting](../troubleshooting.md).


---

<!-- docs/features/privacy.md -->

# Privacy and network use

**Your voice and text never leave your Mac.** Transcription, cleanup, speaker detection, summaries and answers all run locally.

## The only network traffic: one-time model downloads

| Model | From | Size | When |
|---|---|---|---|
| Whisper large-v3-turbo q5_0 | huggingface.co/ggerganov/whisper.cpp | 574 MB | first run |
| Gemma-3-4B-it Q4_K_M | huggingface.co/ggml-org/gemma-3-4b-it-GGUF | 2.49 GB | first run |
| Whisper base.en | huggingface.co/ggerganov/whisper.cpp | 148 MB | first meeting |
| TitaNet-large (speaker voices) | github.com/k2-fsa/sherpa-onnx releases | 101 MB | first meeting |
| Silero VAD (speech detection) | github.com/k2-fsa/sherpa-onnx releases | 0.6 MB | first meeting |

Each download is checked against a pinned SHA-256 before use (`mispr/models.py`). After that the app works offline. A full network audit is planned; see the roadmap.

## On disk

- **Dictations:** `voice-recordings/` in the project folder. **Meetings:** `meeting-recordings/`. Both are gitignored.
- **Incognito** writes nothing. Audio stays in locked RAM (`mlock`) and is zeroed after use, and text is typed rather than pasted.
- On SSDs, deleting doesn't guarantee data is gone, so Incognito is the only guaranteed erase.
- The pasted text is marked transient/concealed, and your previous clipboard is restored.

## What the app can see

- **Accessibility:** which app is in front, whether a text box is focused, and the page URL/title for browser history.
- **Screen & System Audio:** audio only, during a meeting.
- **Full Disk Access / Control Finder:** only for the "open folder" commands.


---

<!-- docs/architecture.md -->

# Architecture

How Mispr Flow turns a press of fn into pasted text. For decisions and roadmap, see [plan.md](../plan.md).

## The pipeline

```
 hold fn                 speak                   release fn
    │                      │                         │
    ▼                      ▼                         ▼
 hotkey.FnMonitor ──► widget: HOLD ──────────► widget: PROCESSING
 (HID event tap)      audio.Recorder.start()   audio.Recorder.stop()  (instant; engine stops in background)
                      AVAudioEngine tap                 │
                      → soxr 44.1k→16k                  ▼
                      → mlock'ed buffer        transcribe.Transcriber   (worker thread, ~1.1 s)
                      → live waveform level             │ raw text
                                                        ▼
                                               cleanup.Cleaner          (same worker, ~0.55 s)
                                               Gemma + check(): no invented words
                                                        │ text
                                                        ▼ (back on the main thread)
                                   context.frontmost() → paste.paste_text() → storage.save_recording()
                                                        │
                                                        ▼
                                               recorder.wipe() → widget: IDLE
```

## Threads

| Thread | Runs | Why |
|---|---|---|
| Main (AppKit run loop) | Event tap callbacks, widget state machine, 60 fps rendering, paste, saving | AppKit and the event tap require it |
| CoreAudio I/O | `Recorder._on_samples`: resample and append to the buffer, update the level | Real-time audio; guarded by `Recorder._lock` |
| `whisper-load`, `cleanup-load` | Load and warm up models at launch | 2-3 s of work that mustn't block the UI |
| `whisper-run` | Transcription + cleanup for one dictation | whisper.cpp and llama.cpp release the GIL, so the UI stays live |
| `mic-stop` | `AVAudioEngine.stop()` | Can never freeze the UI, even if CoreAudio hangs |
| `model-setup` | First-run downloads | Progress is stored as a float the widget draws |
| `meeting-worker` | Final meeting text: speech detection, Whisper turbo segments, speaker fingerprints, summaries, Q&A | One queue so chunks come back in order |
| `meeting-preview` | Live meeting previews with Whisper `base.en` | Its own thread so previews never delay final text |
| `find-folder` | "open folder" / "open …" searches (Spotlight, then a walk) | Up to 1.5 s of disk work off the main thread |

All workers use `threads.start_daemon()`, so none can keep the app from quitting. Results come back to the main thread through `AppHelper.callAfter`.

## The event tap (`hotkey.py`)

- An **active** tap at `kCGHIDEventTap` (needs Accessibility) sees keys before the window server. It swallows:
  - fn flag changes: drives `fn_down` / `fn_up`;
  - the 🌐 key's own key events (keycode 179): stops the Emoji & Symbols picker;
  - hands-free shortcuts, and the matching key-ups, when `WidgetController.handle_key` claims them (space/return/enter/delete).
- The callback only inspects state and defers work with `callAfter`. An active tap delays every keystroke system-wide until it returns, so it must stay fast.
- The same tap watches the **app switcher key** (`switch_trigger`): a key (swallowed), one side of a modifier (passes through), or a combo of modifiers with or without a key. It reports `down` / `up` / `combo` (another key pressed while held, which cancels) to `widget.switch_key`.
- ⌥M (new meeting note) is swallowed so it doesn't type "µ".
- Without Accessibility it falls back to a listen-only session tap, and upgrades itself every 2 s once Accessibility is granted.
- If macOS disables the tap for being slow, the callback re-enables it.

## The widget (`widget.py`)

`WidgetController` is a state machine drawn into a transparent, non-activating `NSPanel` at status-bar level. It never takes focus from the app you're typing in.

```
            hover                       long-press mic / hold fn
   IDLE ─────────► HOVER ───────────────────────────────► HOLD ──release──► PROCESSING ──► IDLE
    ▲  ◄───────────  │  click mic / double-tap fn                              ▲
    │   pointer out  └──────────────────────────► HANDSFREE ─ ✓/space/return ──┘
    │                                                │  ✕/delete/fn
    │                                                ▼
    └──── 5 s / delete ◄──────────────────────── CANCELLED ── Undo ──► PROCESSING
   HOVER ─ ◉ ─► MEETING ─ stop ─► (short) MISTAKE ─► IDLE        launch w/o models ─► SETUP ─► IDLE
```

- **Layout** (`layout(state)`) is a pure function returning the background shape and clickable elements. Its output is pinned by a golden snapshot test.
- **Frame loop** (`tick`, 60 fps): runs due scheduled callbacks (`_run_due`), polls the active screen every 0.5 s, updates hover and click-through, animates the waveform, eases the shape 30% per frame toward its target, fades content and tooltips, then redraws.
- **Scheduled callbacks** (`after`) carry the state's sequence number, so a timer from an old state (for example the Undo countdown after you pressed Undo) never fires.
- **Click-through:** the panel ignores the mouse except while the pointer is over a button, so it never blocks clicks on the app beneath it.

## Audio (`audio.py`)

- `MicEngine` is the only AVFoundation code. It taps input bus 0 at the device's native format and hands channel 0 to the recorder.
- `Recorder` owns the `SecureAudioBuffer` (10 min, `mlock`ed, zeroed after use), the `soxr` resampler, and the waveform level (RMS → dB → 0..1, fast attack and slow release).
- `stop()` gates capture off under the lock, so no sample arrives after it returns. It flushes the resampler tail and stops the engine on `mic-stop`. A stop that hasn't finished within 1 s is abandoned and the next start builds a fresh engine.
- Why not PortAudio: its macOS backend deadlocked in `Pa_StopStream` (lock-order inversion with CoreAudio's I/O thread). Full analysis in `logs/2026-09-30_14-34-34_mic-deadlock-fix.md`.

## Transcription and cleanup

- `Transcriber._transcribe` skips clips under 0.3 s or with a peak under 0.01, waits for the model to finish loading if needed, and strips `[BLANK_AUDIO]`-style annotations.
- `Cleaner.clean` sends a system prompt, six few-shot examples, and the dictation in `<dictation>` tags, using greedy decoding. `check(raw, cleaned)` then enforces:
  - no word in the output that isn't in the input (after normalizing case, punctuation, apostrophes, and number words);
  - at least 60% of the speaker's non-filler words kept.
  If either fails, the raw transcript is used and the reason is recorded.

## Paste and context

- `paste_text` snapshots the clipboard, puts the text plus transient/concealed markers on it, posts ⌘V (flags = ⌘ only, so a held fn doesn't leak in), and restores the snapshot 0.5 s later unless the user copied something in between.
- `context.frontmost()` names the app. For browsers it walks up the Accessibility tree from the focused element to the outermost `AXWebArea` to get the page URL and title (0.3 s timeout, max 60 hops).

## First-run setup (`onboarding.py`)

- `SetupFlow` is pure logic: the current step (Welcome, Permissions, Optional features, Models, Ready), which permissions are missing, whether Continue is allowed, and when the window should show (`needed()`). Microphone and Accessibility are required (page 2); Screen & System Audio, Full Disk Access and Control Finder are optional (page 3, never blocking).
- `allow(key)`: the first click shows the one-time system prompt; later clicks (or a microphone that was already denied) open the matching System Settings pane.
- Permission checks never prompt (the window refreshes on a timer): Finder control uses `AEDeterminePermissionToAutomateTarget` without asking, Full Disk Access reads the protected TCC database; only **Allow…** asks.
- `SetupWindow` draws the five pages with standard AppKit controls (so it follows light/dark mode) and refreshes every 0.5 s: checkmarks, the model progress bar (from the widget's download state), and the Continue button.
- Finishing sets `onboarded` in `settings.json`.

## Storage and settings

- `storage.save_recording` writes the 16 kHz 16-bit WAV and the JSON record (see [plan.md](../plan.md#recording-storage) for fields). The folder is the project's `voice-recordings/` from source, or Application Support when packaged.
- `settings.py` loads `settings.json` (unknown keys ignored, corrupt files fall back to defaults with a warning).
- `models.py` downloads to a `.part` file, verifies size and SHA-256, then renames into place. A bad download is never used.

## Lifecycle (`app.py`)

0. **Hosted mode:** when started by `Mispr Flow.app` (`MISPR_HOSTED=1`), the engine skips its own windows and menu, connects to the app (`_connect_host`), and quits when the app does.
1. Single-instance lock (`$TMPDIR/Mispr_Flow.lock`); a second copy exits.
2. Regular activation policy (Dock icon, like Wispr Flow); the process is renamed "Mispr Flow" (`_brand_process`) and the Dock tile uses `assets/AppIcon.icns`; an app menu (About, Setup Guide…, Hide, Quit); clicking the Dock icon opens the setup window until the main window exists; menu-bar template icon.
3. `WidgetController.start()`: builds the panel, prepares the mic engine, then either loads the models or enters SETUP.
4. Opens the setup window (`onboarding.py`) if setup is needed: first run, a required permission missing, or a model missing. Adds **Setup Guide…** to the menu.
5. Every second, `maintain_hotkey` installs the fn tap as soon as a permission allows it, and upgrades a listen-only tap to the active one once Accessibility is granted. No restart needed.
6. On Quit or SIGTERM/INT/HUP: stop the mic, zero and unlock the audio buffer, free the llama.cpp model (its Metal backend asserts otherwise), and remove the menu-bar icon.

## The app and the engine

Two processes:

- **Mispr Flow.app** (SwiftUI, `macos/`): the main window, the meeting side panel, the meeting audio recorder and the echo gate.
- **The Python engine** (`mispr/`): the widget, the hotkeys, dictation, voice commands and all the models.

The app starts the engine and restarts it if it crashes. They talk in JSON lines ([engine protocol](engine-protocol.md)) and share `settings.json`: the app writes it, then sends `reload_settings`.

## Voice commands

```
hold switch key ─► hotkey.FnMonitor (switch edge: down / up / combo)
                   └► widget.switch_key: record (opens a muted mic just for the command)
let go ──────────► Whisper (raw, no cleanup)
                   └► widget._on_switch_heard: save to history (status "command")
                      └► apps.parse(text) → ("switch" | "open" | "open_folder" | "close" | "minimize" | "expand"
                          | "beside" | "size" | "shortcut" | "media" | "seek" | "volume" | "mic" | "mute_tab"
                          | "mute_app" | "scroll" | "scroll_end" | "quit" | "nickname", …)
                          └► widget._do_switch_command → apps.* (match_scored, window_action, press_shortcut,
                             press_media, seek, scroll, set_volume, spotlight / find_in, finder_go …)
                             └► notice + sound; the outcome rewrites the history entry ("Opened claude")
```

Folder searches run on a background thread (`_in_background`). App matching is confidence-scored, so weak guesses never launch an app that isn't running.

## Meeting notes

```
App: MeetingRecorder ─ mic (AVAudioEngine) ──► Resampler 16k ─► EchoGate.mic ─► Segmenter("you") ─┐
                     └ system (ScreenCaptureKit) ► Resampler ─► EchoGate.system, Segmenter("them") ┤
     NoteModel: chunks at pauses ─► transcribe_chunk;  every 0.5 s ─► transcribe_chunk(partial) ───┘
Engine: MeetingWorker
   final queue (one thread): SpeechDetector (Silero) → Whisper turbo segments → VoiceClusters.split
                             (TitaNet fingerprints, join/confirm/merge, GenderModel + pitch) → chunk_text, speakers_merged
   preview queue (own thread): SpeechDetector → Whisper base.en → chunk_text(partial)
App: LiveTranscript.add (Echo text removal, merges) → the panel; Stop → summarize → Save note
```


---

<!-- docs/engine-protocol.md -->

# Engine ↔ app protocol

The SwiftUI app (`macos/`) starts the Python engine (`python -m mispr` with `MISPR_HOSTED=1`), and the two talk in **JSON lines** over the engine's stdin/stdout.

- **App → engine:** `{"cmd": "<name>", ...}`, one per line on stdin. Handled in `mispr/app.py: _connect_host`.
- **Engine → app:** lines starting with `@mispr ` followed by `{"event": "<name>", ...}`, on a private duplicate of stdout (`host.open_channel`). Ordinary prints and logs don't collide with it. Parsed in `MisprCore/EngineProtocol.swift`.
- The engine quits when stdin closes (the app quit or crashed). The app restarts a crashed engine.

## Commands (app → engine)

| cmd | Fields | Does |
|---|---|---|
| `open_setup` | | Shows the setup window |
| `reload_settings` | | Re-reads settings.json (dictation key, switch key, nicknames, Incognito…) |
| `quit` | | Quits the engine |
| `start_meeting` / `stop_meeting` | | The widget shows / hides its meeting pill |
| `meeting_level` | `level` | Live audio level for the widget during a meeting |
| `transcribe_chunk` | `id, path, stream ("you"/"them"), offset, delete, partial` | Final text (or a live preview when `partial`) for one WAV chunk |
| `summarize` | `id, lines` | Writes the meeting summary |
| `ask` | `id, question, lines` | Answers a question ("" = What did I miss?) |
| `try_prompt` | `text, system, extra, examples, guard` | Runs the Prompts page's draft on sample text |

## Events (engine → app)

| event | Fields | Means |
|---|---|---|
| `hello` | `recordings_dir, settings_path, prompts_path, default_prompts` | The engine started; where its data lives |
| `saved` | `path` | A dictation or command was saved (or updated): refresh history |
| `open_note` | `start` | ⌥M / ◉: show the note panel (and start or stop) |
| `meeting` | `active` | A meeting started or stopped from the widget |
| `chunk_text` | `id, stream, speaker, offset, text, voice, partial, last` | Transcript text. One chunk can become several lines (one per speaker); only the last has `last: true` |
| `speakers_merged` | `id, speaker, into` | Two voices were one person: relabel |
| `summary` | `id, summary` | Summary JSON: title, overview, decisions, action_items, open_questions |
| `answer` | `id, question, text` | The answer to `ask` |
| `tried` | `output, applied, rejected, ms` | The Prompts page's Try-it result |
| `settings_changed` | | The engine changed settings.json itself (a nickname set by voice) |

Unknown events are ignored (`EngineEvent.unknown`), so older apps keep working with newer engines.


---

<!-- docs/models.md -->

# Models

All models run locally. Each is downloaded once from its official source and checked against a pinned SHA-256 (`mispr/models.py`). Download any of them ahead of time with:

```bash
.venv/bin/python -m mispr.models whisper cleanup preview speakers vad
```

| Name in code | File | Size | Source | License | Used for |
|---|---|---|---|---|---|
| `WHISPER_TURBO_Q5` (default) | ggml-large-v3-turbo-q5_0.bin | 574 MB | HF ggerganov/whisper.cpp | MIT | Dictation and final meeting text |
| `GEMMA3_4B_Q4` (cleanup) | gemma-3-4b-it-Q4_K_M.gguf | 2.49 GB | HF ggml-org/gemma-3-4b-it-GGUF | Gemma Terms of Use | Cleanup, terminal mode, summaries, Q&A |
| `WHISPER_BASE_EN` (preview) | ggml-base.en.bin | 148 MB | HF ggerganov/whisper.cpp | MIT | Live meeting previews |
| `TITANET_LARGE` (speakers) | nemo_en_titanet_large.onnx | 101 MB | sherpa-onnx release | CC BY 4.0 (NVIDIA) | Voice fingerprints (diarization) |
| `SILERO_VAD` (vad) | silero_vad.onnx | 0.6 MB | sherpa-onnx release | MIT | Ignoring clicks and noise |
| `voice_gender.json` | (in the repo) | 192 weights | trained here | from AMI and LibriSpeech (CC BY 4.0) | Male/female from a fingerprint |

## Why these

- **Gemma-3-4B** beat Qwen2.5-1.5B/3B and Qwen3-4B in a 27-case eval: zero invented words, zero lost key words, the most conservative on self-corrections, ~550 ms on an M1 Pro (`tools/eval_cleanup.py`).
- **base.en for previews:** ~0.15 s per phrase versus ~1 s with turbo. Previews became a median 0.14 s instead of 0.49 s, and final text 1.27 s instead of 2.07 s.
- **TitaNet-large:** best of four speaker models on real meetings, with separation d′ 4.09 on AMI and 0.66 on a Zoom recording.
  - It beat WeSpeaker ResNet34 (3.10 / 0.57), CAM++ (0.74 / 0.32) and ResNet293 (2.95 / 0.25, and 7× slower).
- **Silero VAD:** mouse clicks and typing score 0 s of speech, while real speech passes.
- **Gender classifier:** logistic regression on TitaNet fingerprints, held out by person: 76/80 LibriSpeech and 13/16 AMI voices right. It's averaged with pitch, because on Zoom audio women measured ~150 Hz.

Details and raw numbers: `logs/` (speaker-id, diarization-gender, clicks-echo-speed).


---

<!-- docs/testing.md -->

# Testing

**Status at the end of the documentation branch:**
- Python: **1217 passed**, 10 skipped. The skipped ones are opt-in integration tests.
- Swift: **287 / 287**.
- Every function is covered. Python line coverage is 96%.
- **Every test, with what it checks, file by file:** [docs/tests/](tests/README.md). The same list as one file: [logs/2026-10-01_19-14-46_test-catalog.md](../logs/2026-10-01_19-14-46_test-catalog.md). Regenerate both with `python tools/test_catalog.py`.

## Running

```bash
.venv/bin/python -m pytest                           # Python, ~13 s
cd macos && swift test                               # Swift, ~70 s
.venv/bin/python -m pytest tests/test_apps.py        # one file
MISPR_INTEGRATION=1 .venv/bin/python -m pytest tests/test_integration.py   # real models and mic
UPDATE_GOLDEN=1 .venv/bin/python -m pytest           # after an intentional visual change; then review tests/golden/
```

During development, run only the tests that cover a change. Run the full suite when a change cuts across modules.

## Rules

- Tests never touch the real mic, clipboard, keyboard, models, recordings or settings: those are faked or redirected to temp folders (`tests/conftest.py`, `macos/Tests/MisprFlowTests/Helpers.swift`).
- **Any warning fails the run.**
- Things that would change the user's Mac (moving windows, quitting apps, pressing keys) are tested with fakes, or against a process that doesn't exist.
- **Golden files** (`tests/golden/`) pin the widget's layout and look, and the setup window's pages, pixel for pixel.

## Python (`tests/`)

| File | Covers |
|---|---|
| `test_widget.py` | The widget's state machine, gestures, paste/copy/type, sounds, notices, Auto-Enter (badge, chime, terminals), app switcher commands end to end, Commands history, terminal dictation, Incognito |
| `test_apps.py` | Command parsing (apps, windows, tabs, sound, seek, scroll, folders, quit), confident matching, folder search (Spotlight, walk, sound-alikes), Finder/permission helpers |
| `test_terminal.py` | Spoken syntax → shell; never adding commands |
| `test_meeting.py` | Meeting chunks, speech detection, diarization rules, gender, previews, summaries, Q&A |
| `test_hotkey.py` | The event tap: dictation key, switch key/combos, ⌥M, hands-free keys |
| `test_context_paste.py` | Text-box detection, paste/copy/type, Return and media keys |
| `test_onboarding.py` | Setup flow, permissions (required and optional pages), golden images |
| `test_cleanup.py`, `test_prompts.py` | The cleanup model wrapper and its no-invented-words guard; the Prompts file |
| `test_transcribe.py`, `test_audio.py` | Whisper wrapper (timed segments, lazy load); mic capture and wiping |
| `test_storage.py`, `test_settings_models_setup.py` | Saved recordings; settings; model specs and downloads |
| `test_host.py`, `test_entrypoints.py`, `test_threads.py`, `test_draw.py`, `test_screens_sounds_app.py` | The app protocol, entry points, threads, drawing, screens, sounds |
| `test_integration.py` | Opt-in: real models and mic |

## Swift (`macos/Tests/`)

| File | Covers |
|---|---|
| `MisprCoreTests/CoreTests.swift` | Engine protocol, recordings and stats, meetings and the store (delete, rename, remove person, contacts), live transcript, echo text removal, `EchoGate`, speaker merges, switch keys and combos, command history |
| `MisprCoreTests/EngineProcessTests.swift` | The engine as a real child process (stand-in script) |
| `MisprFlowTests/NoteModelTests.swift` | A meeting note from start to saved summary: save/discard/close questions, resume, merges |
| `MisprFlowTests/AppModelTests.swift` | Settings, keys, nicknames, notes and people actions |
| `MisprFlowTests/RenderTests.swift` | Every page, tab, theme and component drawn offscreen and checked non-blank |
| `MisprFlowTests/ViewLogicTests.swift` | Key picking (including combos), wording, layouts |
| `MisprFlowTests/SystemTests.swift`, `RemainingTests.swift` | Recorder parts, window behaviour, app shell |

## Quality tools (`tools/`)

- `stress_test.py`: repeated, random-order and parallel runs.
- `mutation_test.py`: plants bugs to check the tests catch them (last score 97.6%).
- `eval_cleanup.py`: scores the cleanup model.


---

<!-- docs/data-formats.md -->

# Data formats

Everything is plain files on the Mac.

## `settings.json`

Path: `~/Library/Application Support/Mispr_Flow/settings.json`. Written by both the app and the engine; unknown keys are kept by the app and ignored by the engine.

```json
{
  "incognito": false, "auto_enter": false, "cleanup": true, "sounds": true,
  "hotkey": {"kind": "fn", "keycode": 63, "label": "fn"},
  "switch_hotkey": {"kind": "combo", "mods": ["control", "option"], "keycode": null, "label": "⌃⌥"},
  "app_nicknames": {"c": "Google Chrome", "scooby snacks": "Google Chrome"},
  "onboarded": true
}
```

**`hotkey` kinds:**
- `fn`;
- `modifier` (one side, by key code: 54/55 ⌘, 56/60 ⇧, 58/61 ⌥, 59/62 ⌃);
- `key` (any key code).

**`switch_hotkey`** can also be `combo`: modifiers by name, with a key code or `null`. `null` turns it off.

## `prompts.json`

Same folder. The Prompts page's cleanup instructions: `system`, `extra` (your own rules), `examples` ("Said: … / Wrote: …" pairs), `guard` (the no-invented-words check).

## A dictation or command: `voice-recordings/YYYY-MM-DD/<id>.json` (+ `<id>.wav`, 16 kHz mono)

```json
{
  "id": "2026-10-01_18-00-13-182",
  "started_at": "2026-10-01T18:00:10.120-07:00", "ended_at": "2026-10-01T18:00:13.182-07:00", "duration_s": 3.06,
  "status": "pasted",
  "transcript": "Let's ship on Friday.", "raw_transcript": "um let's ship on friday", "words": 4,
  "recorded_in": {"app": "Slack", "bundle_id": "com.tinyspeck.slackmacgap"},
  "pasted_into": {"app": "Slack", "bundle_id": "com.tinyspeck.slackmacgap", "url": null, "page_title": null},
  "model": "ggml-large-v3-turbo-q5_0.bin",
  "cleanup": {"model": "gemma-3-4b-it-Q4_K_M.gguf", "applied": true, "ms": 540, "rejected": null},
  "audio_file": "2026-10-01_18-00-13-182.wav"
}
```

**`status` values:**
- `pasted`;
- `copied` (no text box);
- `cancelled`;
- `command` (a voice command: `transcript` is what it did, e.g. "Opened claude"; `raw_transcript` is what was heard).

Commands are kept out of word counts and speed stats.

## A meeting note: `meeting-recordings/YYYY-MM-DD/<id>.json` (+ `<id>/you.wav`, `<id>/them.wav`)

```json
{
  "id": "2026-10-01_14-29-38-270", "title": "Release plan", "app": "Zoom",
  "started_at": "…", "ended_at": "…", "duration_s": 612,
  "participants": [{"name": "You", "is_me": true}, {"name": "Priya", "role": null}],
  "transcript": [{"speaker": "You", "start_s": 0.5, "text": "Let's ship Friday."}],
  "summary": {"overview": "…", "decisions": ["…"], "action_items": [{"owner": "Priya", "task": "…", "due": "Thursday"}],
              "open_questions": ["…"]},
  "my_thoughts": "…"
}
```

## Contacts: `meeting-recordings/people.json`

```json
{"Priya": {"role": "Designer", "company": "Acme", "email": "p@acme.com", "phone": "", "notes": "Loves charts."}}
```

Cards with nothing filled in are dropped.

## Other

| What | Where |
|---|---|
| Models | `~/Library/Application Support/Mispr_Flow/models/` (see [models.md](models.md)) |
| Engine log | `~/Library/Logs/Mispr Flow/engine.log` |
| Full Disk Access probe | reads `~/Library/Application Support/com.apple.TCC/TCC.db` (read only, never changed) |


---

<!-- mispr/README.md -->

# `mispr/`: the Python engine

Runs dictation, the widget, voice commands and all the models. Start it alone with `.venv/bin/python -m mispr`, or let the app host it (`MISPR_HOSTED=1`, see [engine protocol](../docs/engine-protocol.md)).

| Module | What it does |
|---|---|
| `app.py` | Entry point: single-instance lock, menu bar, setup window, the hotkey monitor, and the host connection (commands from the Swift app) |
| `widget.py` | The floating pill: state machine (idle, hold, hands-free, processing, meeting…), drawing, mouse and keys, sounds and notices; dictation's paste/copy/Auto-Enter; the **app switcher** (`switch_key`, `_do_switch_command`) |
| `hotkey.py` | Quartz event tap: the dictation key (fn, a modifier side, or a key), the **switch key** (key, modifier side or combo), ⌥M, hands-free keys |
| `apps.py` | Voice commands: parsing, confident app matching, window layout, shortcuts, media/volume/mic, tab muting, seek, scroll, folder/file search (Spotlight, walk, Soundex), Finder control, permission checks |
| `terminal.py` | Terminal dictation: spoken syntax → shell, with a no-added-words check |
| `audio.py` | Mic capture into a locked (`mlock`), wipeable buffer |
| `transcribe.py` | whisper.cpp wrapper: text or timed segments; lazy loading |
| `cleanup.py` | Gemma cleanup with the no-invented-words guard; also summaries and answers (`complete`) |
| `meeting.py` | Meeting chunks: final text, live previews (own thread), speech detection (Silero), speaker diarization (TitaNet, `VoiceClusters`), gender (`GenderModel`), summaries, Q&A |
| `paste.py` | Paste with clipboard restore, typing (Incognito), copy, Return |
| `context.py` | Frontmost app, browser URL/title, "is a text box focused?" |
| `storage.py` | Saving dictations and commands (WAV and JSON) |
| `settings.py` | `settings.json` (shared with the app) |
| `models.py` | Model specs (pinned SHA-256), downloads, `python -m mispr.models` |
| `setup.py`, `onboarding.py` | Required model downloads; the setup window (5 steps, two permission pages) |
| `prompts.py` | The cleanup prompt the Prompts page edits |
| `host.py` | JSON lines to and from the app |
| `screens.py`, `draw.py`, `sounds.py`, `levels.py`, `threads.py` | Screen following, drawing helpers, sound cues, audio levels, daemon threads |
| `voice_gender.json` | The trained male/female weights for TitaNet fingerprints |
| `assets/` | Logo, app icon, menu-bar icon, sounds |

Guides: [docs/features/](../docs/features/). Tests: [tests/](../tests/README.md).


---

<!-- macos/README.md -->

# `macos/`: the SwiftUI app

A Swift package (`Package.swift`) with:

| Target | What |
|---|---|
| `MisprCore` | Testable logic with no UI: the engine process and protocol, settings file and keys (including combos), recordings and stats, meetings and the store (delete, rename, contacts), the live transcript (with echo text removal), `EchoGate` (mic echo silencing), meeting detection |
| `MisprFlow` | The app: `AppDelegate`, `AppModel`, `MeetingRecorder` (mic + ScreenCaptureKit), `SystemProbe`, `DevTools`, and the views (`Views/`: Home, Insights, Notetaker, People, Prompts, Settings, the note side panel, theme) |
| `MisprCoreTests`, `MisprFlowTests` | XCTest suites (287 tests) |

## Build and run

```bash
tools/make_signing_cert.sh      # once
tools/trust_signing_cert.sh     # once (asks for your password)
tools/build_app.sh --open       # builds build/Mispr Flow.app and opens it
cd macos && swift test          # tests
```

**Dev flags** for `MisprFlow`:
- `--detect` prints what kind of meeting it sees;
- `--segment file.wav` shows how audio is cut into chunks;
- `--record-test` checks real capture.

**Environment:** `MISPR_PAGE=Insights` opens on a page; `MISPR_PEOPLE="A,B"` opens People with them selected.

See [main window](../docs/features/main-window.md), [meeting notes](../docs/features/meeting-notes.md), [engine protocol](../docs/engine-protocol.md).


---

<!-- macos/Sources/MisprCore/README.md -->

# `MisprCore`: the app's testable logic (no UI)

| File | What |
|---|---|
| `Engine.swift` | Starts, watches and restarts the Python engine process; sends commands; publishes events (`hello`, `saved`, meeting events, `settings_changed`) |
| `EngineProtocol.swift` | `EngineEvent` (parsing `@mispr` JSON lines) and `EngineCommand` (see [the protocol](../../../docs/engine-protocol.md)) |
| `SettingsFile.swift` | Reads and writes `settings.json`, keeping unknown keys: booleans, the dictation key, the switch key (`null` = off), nicknames |
| `DictationKey.swift` | A shortcut: `fn`, a modifier side, a key, or a `combo` of modifiers (± key); labels like "⌃⌥S"; JSON in and out |
| `Recording.swift` | A saved dictation or command (`Status`: pasted/copied/cancelled/command, `isDictation`); `RecordingStore` loads and deletes them |
| `Stats.swift` | Insights: words, pace, streaks, time saved, where words go, voice profile, fun facts (dictation only) |
| `Meeting.swift` | A meeting note and its summary; `MeetingStore` (load, delete, rename person everywhere, remove person); `Contact` and `ContactBook`; `MeetingInsights`, `MeetingsOverview`, `PeopleIndex` |
| `LiveMeeting.swift` | `Segmenter` (cuts audio at pauses), `WAV`, `Echo` (text-level echo removal), `LiveTranscript` (lines, live partials, labels "Male 1"…, merges, the saved meeting) |
| `EchoGate.swift` | Silences the call coming back in through the mic: finds the echo delay, learns the leak, 3× margin, 160 ms hangover, 0.3 s hold |
| `MeetingSource.swift` | Detects the kind of meeting (Zoom, Meet, Teams, FaceTime, Webex, Slack huddle, in person) from running apps and window titles |
| `PromptsFile.swift` | The Prompts page's draft (`prompts.json`) |
| `ProfileInfo.swift` | Name and nickname rules (the greeting) |

Tests: `macos/Tests/MisprCoreTests/`.


---

<!-- macos/Sources/MisprFlow/README.md -->

# `MisprFlow`: the app

| File | What |
|---|---|
| `main.swift` | Entry point; dev flags `--detect`, `--segment file.wav`, `--record-test` |
| `AppDelegate.swift` | Menus, the main window, the note side window, launch and quit |
| `AppModel.swift` | The app's state: engine, settings and keys, nicknames, recordings, stats, meetings, contacts, notes and people actions (delete, rename, remove, save contact), profile |
| `Profile.swift` | Profile photo, theme and appearance |
| `MeetingRecorder.swift` | Mic (AVAudioEngine) + system audio (ScreenCaptureKit), `Resampler` to 16 kHz, `EchoGate`, segmenters, `StreamingWAV` files |
| `SystemProbe.swift` | Running apps, window titles, mic in use, and `WindowArranger` (split screen with a call window) |
| `DevTools.swift` | Reports for the dev flags |
| `Views/` | All the screens: see [Views/README.md](Views/README.md) |

Tests: `macos/Tests/MisprFlowTests/`.


---

<!-- macos/Sources/MisprFlow/Views/README.md -->

# Views

| File | Screens |
|---|---|
| `RootView.swift` | The window frame: sidebar, pages, top bar (`AutoEnterButton`, `IncognitoSwitch`, profile), engine banner, `InfoCard` hover cards |
| `HomeView.swift` | Home: greeting, history (Dictation \| Commands tabs, search, playback), stats, Shortcuts and Voice commands cards |
| `InsightsView.swift` | Insights: pace, streaks, time saved, voice profile, more insights |
| `NotesView.swift` | Notetaker: notes list (hover delete, right-click, Select mode), meeting detail (Summary, Transcript, Insights, My thoughts, Delete), notes insights |
| `PeopleView.swift` | People: list, one or several people's shared meetings, talk share, action items; `ContactEditor` (rename and contact card); remove |
| `NoteWindow.swift` | The meeting side panel (`NoteModel` + `NoteView`): recording, live transcript, tabs, ask, Save note / Discard card, the Save / Discard / Keep editing question, split screen, `SourceChip` |
| `PromptsView.swift` | Edit and try the cleanup prompt |
| `SettingsModal.swift` | Settings: Profile, General (dictation key, app switcher key, `NicknameList`, mic, cleanup), System (login, sounds, setup), Privacy; `KeyRecorder` and `ComboPicker` |
| `Theme.swift` | Colours and fonts for the 6 themes |


---

<!-- tools/README.md -->

# `tools/`

| Script | Use |
|---|---|
| `build_app.sh [--open]` | Build and sign `build/Mispr Flow.app` (`--open` launches it) |
| `make_signing_cert.sh`, `trust_signing_cert.sh` | A local code-signing certificate, so macOS permissions survive rebuilds |
| `export_chat_history.py` | Export the Claude Code conversation into `knowledge-base/07-chat-log.md` and `08-your-messages.md` |
| `build_knowledge_base.py` | Write `knowledge-base/ALL-IN-ONE.md` from the knowledge base and guides |
| `test_catalog.py` | Write `logs/<time>_test-catalog.md`: every Python and Swift test with what it checks |
| `stress_test.py` | Repeated, random-order and parallel test runs |
| `mutation_test.py` | Plant bugs and check the tests catch them |
| `eval_cleanup.py` | Score cleanup models (invented words must be zero) |
| `make_sounds.py` | Generate the original sound cues into `mispr/assets/sounds/` |
| `make_icon.py` | Build `AppIcon.icns` from the logo |
| `make_sample_dictations.py`, `make_sample_meetings.py` | Sample history and meetings for screenshots and testing |
| `render_states.py` | Render every widget state to images |
