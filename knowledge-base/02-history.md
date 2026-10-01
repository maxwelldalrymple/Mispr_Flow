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
