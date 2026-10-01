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
