"""Saving recordings locally (when Incognito is off) for history and usage stats.

Each recording becomes two files in <project>/voice-recordings/YYYY-MM-DD/, named by
the recording's start time down to the millisecond:
    2026-09-30_12-28-33-123.wav   16 kHz mono 16-bit PCM
    2026-09-30_12-28-33-123.json  metadata: times, duration, status, transcript (raw and
                                  cleaned), words, app recorded in, app (and browser page)
                                  pasted into, models used
Nothing here is ever uploaded.
"""

import json
import os
import sys
import wave
from pathlib import Path

import numpy as np



def _data_root():
    """The project folder when running from source; Application Support once packaged as an .app."""
    if getattr(sys, "frozen", False):
        return Path.home() / "Library" / "Application Support" / "Mispr_Flow"
    return Path(__file__).resolve().parent.parent


RECORDINGS_DIR = _data_root() / "voice-recordings"
SAMPLE_RATE = 16_000

# Status values written to the metadata.
PASTED = "pasted"
COPIED = "copied"  # no text box was focused: left on the clipboard instead
CANCELLED = "cancelled"
COMMAND = "command"  # a voice command to the app switcher ("new tab", "chrome beside vs code")


def _stem(t):
    return f"{t:%Y-%m-%d_%H-%M-%S}-{t.microsecond // 1000:03d}"


def save_recording(audio, *, status, transcript, started_at, ended_at, recorded_in, pasted_into, model,
                   raw_transcript=None, cleanup=None):
    """Write the audio and its metadata; returns the .wav path. `audio` is float32 in [-1, 1].

    `recorded_in` / `pasted_into` are context dicts (app, bundle_id, url, page_title);
    `pasted_into` is None for recordings that were never pasted. `transcript` is the text that
    was pasted; `raw_transcript` is Whisper's output before LLM `cleanup` (info dict or None).
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
        "raw_transcript": raw_transcript if raw_transcript is not None else transcript,
        "words": len(transcript.split()),
        "recorded_in": {k: recorded_in.get(k) for k in ("app", "bundle_id")},
        "pasted_into": pasted_into,
        "model": model,
        "cleanup": cleanup,
        "audio_file": wav_path.name,
    }
    (day_dir / f"{stem}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return wav_path


def set_transcript(wav_path, text):
    """Replace a saved recording's text (a voice command's outcome, with the real names: "Opened
    claude", "→ Google Chrome"); what was heard stays in raw_transcript."""
    meta_path = Path(wav_path).with_suffix(".json")
    meta = json.loads(meta_path.read_text())
    meta["transcript"], meta["words"] = text, len(text.split())
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return meta_path


LOG_DIR = Path.home() / "Library" / "Logs" / "Mispr Flow"


def private_dirs():
    """Folders holding the user's words and audio: only their own account may read them."""
    from .settings import SETTINGS_PATH
    return [RECORDINGS_DIR, RECORDINGS_DIR.parent / "meeting-recordings", SETTINGS_PATH.parent,
            LOG_DIR]


def lock_down(dirs=None):
    """Make each existing data folder owner-only (0700), so other accounts on the Mac can't read
    dictations, meetings, settings or the log. Returns the folders changed."""
    changed = []
    for d in dirs if dirs is not None else private_dirs():
        try:
            if Path(d).is_dir() and Path(d).stat().st_mode & 0o077:
                os.chmod(d, 0o700)
                changed.append(Path(d))
        except OSError:
            pass
    return changed
