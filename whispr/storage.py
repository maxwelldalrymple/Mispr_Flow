"""Saving recordings locally (when Incognito is off) for history and usage stats.

Each recording becomes two files in ~/Documents/voice-recordings/YYYY-MM-DD/:
    HHMMSS-<id>.wav   16 kHz mono 16-bit PCM
    HHMMSS-<id>.json  metadata: time, duration, status, transcript, word count, target app
Nothing here is ever uploaded.
"""

import json
import uuid
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
from AppKit import NSWorkspace

RECORDINGS_DIR = Path.home() / "Documents" / "voice-recordings"
SAMPLE_RATE = 16_000

# Status values written to the metadata.
PASTED = "pasted"
CANCELLED = "cancelled"


def save_recording(audio, *, status, transcript, started_at, app_name, bundle_id, model):
    """Write the audio and its metadata; returns the .wav path. `audio` is float32 in [-1, 1]."""
    day_dir = RECORDINGS_DIR / started_at.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    rec_id = uuid.uuid4().hex[:8]
    stem = f"{started_at.strftime('%H%M%S')}-{rec_id}"
    wav_path = day_dir / f"{stem}.wav"

    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())

    meta = {
        "id": rec_id,
        "created_at": started_at.astimezone().isoformat(timespec="seconds"),
        "duration_s": round(len(audio) / SAMPLE_RATE, 2),
        "status": status,
        "transcript": transcript,
        "words": len(transcript.split()),
        "app": app_name,
        "bundle_id": bundle_id,
        "model": model,
        "audio_file": wav_path.name,
    }
    (day_dir / f"{stem}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return wav_path


def frontmost_app():
    """(name, bundle id) of the app being dictated into."""
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return None, None
    return app.localizedName(), app.bundleIdentifier()
