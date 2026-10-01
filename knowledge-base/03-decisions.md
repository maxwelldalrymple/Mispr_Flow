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
