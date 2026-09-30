"""Saving recordings locally (when Incognito is off) for history and usage stats.

Each recording becomes two files in ~/Documents/voice-recordings/YYYY-MM-DD/, named by
the recording's start time down to the millisecond:
    2026-09-30_12-28-33-123.wav   16 kHz mono 16-bit PCM
    2026-09-30_12-28-33-123.json  metadata: times, duration, status, transcript, words,
                                  app recorded in, app (and browser page) pasted into
Nothing here is ever uploaded.
"""

import json
import wave
from pathlib import Path

import numpy as np

RECORDINGS_DIR = Path.home() / "Documents" / "voice-recordings"
SAMPLE_RATE = 16_000

# Status values written to the metadata.
PASTED = "pasted"
CANCELLED = "cancelled"


def _stem(t):
    return f"{t:%Y-%m-%d_%H-%M-%S}-{t.microsecond // 1000:03d}"


def save_recording(audio, *, status, transcript, started_at, ended_at, recorded_in, pasted_into, model):
    """Write the audio and its metadata; returns the .wav path. `audio` is float32 in [-1, 1].

    `recorded_in` / `pasted_into` are context dicts (app, bundle_id, url, page_title);
    `pasted_into` is None for recordings that were never pasted.
    """
    day_dir = RECORDINGS_DIR / f"{started_at:%Y-%m-%d}"
    day_dir.mkdir(parents=True, exist_ok=True)
    stem = _stem(started_at)
    wav_path = day_dir / f"{stem}.wav"

    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())

    meta = {
        "id": stem,
        "started_at": started_at.astimezone().isoformat(timespec="milliseconds"),
        "ended_at": ended_at.astimezone().isoformat(timespec="milliseconds"),
        "duration_s": round(len(audio) / SAMPLE_RATE, 3),
        "status": status,
        "transcript": transcript,
        "words": len(transcript.split()),
        "recorded_in": {k: recorded_in.get(k) for k in ("app", "bundle_id")},
        "pasted_into": pasted_into,
        "model": model,
        "audio_file": wav_path.name,
    }
    (day_dir / f"{stem}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return wav_path
