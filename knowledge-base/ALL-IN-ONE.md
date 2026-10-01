# Mispr Flow: complete knowledge base

You are being given the full context of the Mispr Flow project: what it is, how it's built, every
decision and why, the history of the work, research results, and how the project owner likes to
work. Read section 1 (overview) and section 2 (working preferences) first, and follow those
preferences when helping. Paths are relative to the repository root
(github.com/maxwelldalrymple/Mispr_Flow).

_Built 2026-10-01 19:05 from 20 files by tools/build_knowledge_base.py._


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
- **Logs:** every change gets a `logs/<YYYY-MM-DD_HH-MM-SS>_<topic>.md` with real results, including which tests ran and what they check.
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

All workers use `threads.start_daemon()`, so none can keep the app from quitting. Results come back to the main thread through `AppHelper.callAfter`.

## The event tap (`hotkey.py`)

- An **active** tap at `kCGHIDEventTap` (needs Accessibility) sees keys before the window server. It swallows:
  - fn flag changes: drives `fn_down` / `fn_up`;
  - the 🌐 key's own key events (keycode 179): stops the Emoji & Symbols picker;
  - hands-free shortcuts, and the matching key-ups, when `WidgetController.handle_key` claims them (space/return/enter/delete).
- The callback only inspects state and defers work with `callAfter`. An active tap delays every keystroke system-wide until it returns, so it must stay fast.
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

- `SetupFlow` is pure logic: the current step, which permissions are missing, whether Continue is allowed, and when the window should show (`needed()`). Microphone and Accessibility are required; Screen & System Audio is optional.
- `allow(key)`: the first click shows the one-time system prompt; later clicks (or a microphone that was already denied) open the matching System Settings pane.
- `SetupWindow` draws the four pages with standard AppKit controls (so it follows light/dark mode) and refreshes every 0.5 s: checkmarks, the model progress bar (from the widget's download state), and the Continue button.
- Finishing sets `onboarded` in `settings.json`.

## Storage and settings

- `storage.save_recording` writes the 16 kHz 16-bit WAV and the JSON record (see [plan.md](../plan.md#recording-storage) for fields). The folder is the project's `voice-recordings/` from source, or Application Support when packaged.
- `settings.py` loads `settings.json` (unknown keys ignored, corrupt files fall back to defaults with a warning).
- `models.py` downloads to a `.part` file, verifies size and SHA-256, then renames into place. A bad download is never used.

## Lifecycle (`app.py`)

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
- [logs/2026-10-01_18-57-46_test-catalog.md](../logs/2026-10-01_18-57-46_test-catalog.md) lists every test with what it checks. Regenerate it with `python tools/test_catalog.py`.

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

<!-- tools/README.md -->

# `tools/`

| Script | Use |
|---|---|
| `build_app.sh [--open]` | Build and sign `build/Mispr Flow.app` (`--open` launches it) |
| `make_signing_cert.sh`, `trust_signing_cert.sh` | A local code-signing certificate, so macOS permissions survive rebuilds |
| `build_knowledge_base.py` | Write `knowledge-base/ALL-IN-ONE.md` from the knowledge base and guides |
| `test_catalog.py` | Write `logs/<time>_test-catalog.md`: every Python and Swift test with what it checks |
| `stress_test.py` | Repeated, random-order and parallel test runs |
| `mutation_test.py` | Plant bugs and check the tests catch them |
| `eval_cleanup.py` | Score cleanup models (invented words must be zero) |
| `make_sounds.py` | Generate the original sound cues into `mispr/assets/sounds/` |
| `make_icon.py` | Build `AppIcon.icns` from the logo |
| `make_sample_dictations.py`, `make_sample_meetings.py` | Sample history and meetings for screenshots and testing |
| `render_states.py` | Render every widget state to images |
