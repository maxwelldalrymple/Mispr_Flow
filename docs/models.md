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
