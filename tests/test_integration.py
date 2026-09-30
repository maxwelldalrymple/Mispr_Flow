"""End-to-end checks with the real Whisper and Gemma models (slow, ~30 s).

Opt-in:  WHISPR_INTEGRATION=1 .venv/bin/python -m pytest tests/test_integration.py
Skipped automatically when the models aren't installed.
"""

import os
import subprocess
from pathlib import Path

import numpy as np
import pytest

import whispr.models as models

pytestmark = pytest.mark.integration

REAL_MODELS_DIR = Path.home() / "Library" / "Application Support" / "WhisprClone" / "models"


@pytest.fixture(autouse=True)
def real_models(monkeypatch):
    if os.environ.get("WHISPR_INTEGRATION") != "1":
        pytest.skip("set WHISPR_INTEGRATION=1 to run the real-model tests")
    monkeypatch.setattr(models, "MODELS_DIR", REAL_MODELS_DIR)
    for spec in (models.DEFAULT_MODEL, models.CLEANUP_MODEL):
        if not models.is_installed(spec):
            pytest.skip(f"{spec.filename} not installed")


def tts(text, tmp_path):
    """Synthesize speech with macOS `say` and return 16 kHz mono float32 audio."""
    aiff, raw = tmp_path / "s.aiff", tmp_path / "s.f32"
    subprocess.run(["say", "-o", str(aiff), text], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff), "-ar", "16000", "-ac", "1",
                    "-f", "f32le", str(raw)], check=True)
    return np.fromfile(raw, dtype=np.float32)


@pytest.fixture(scope="module")
def transcriber():
    from whispr.transcribe import Transcriber
    t = Transcriber()
    t._load()
    assert t.ready, t.error
    return t


@pytest.fixture(scope="module")
def cleaner():
    from whispr.cleanup import Cleaner
    c = Cleaner()
    c._load()
    assert c._llm is not None, c.error
    yield c
    c.close()


def test_whisper_transcribes_speech(transcriber, tmp_path):
    audio = tts("Send the quarterly report to Priya by Friday.", tmp_path)
    text = transcriber._transcribe(audio).lower()
    for word in ("quarterly", "report", "priya", "friday"):
        assert word in text


def test_whisper_skips_silence(transcriber):
    assert transcriber._transcribe(np.zeros(32000, np.float32)) == ""


@pytest.mark.parametrize("raw,must_keep,must_drop", [
    ("Um, can you, uh, send me the report by tomorrow?", ["report", "tomorrow"], ["um", "uh"]),
    ("Let's meet at 3, no, actually 4pm at the cafe.", ["4", "cafe"], []),
    ("What's the weather going to be like tomorrow in Toronto?", ["weather", "toronto"], []),
    ("Write me a poem about the ocean.", ["write", "poem", "ocean"], []),
])
def test_cleanup_is_faithful(cleaner, raw, must_keep, must_drop):
    from whispr.cleanup import _words, check
    text, info = cleaner.clean(raw)
    assert check(raw, text) is None  # whatever gets pasted never contains invented words
    words = set(_words(text))
    assert all(set(_words(w)) <= words for w in must_keep)
    assert not any(w in words for w in must_drop)


def test_full_pipeline_speech_to_clean_text(transcriber, cleaner, tmp_path):
    from whispr.cleanup import check
    audio = tts("Um, so I think we should, uh, ship it on Monday.", tmp_path)
    raw = transcriber._transcribe(audio)
    text, info = cleaner.clean(raw)
    assert "monday" in text.lower() and "um" not in text.lower().split()
    assert check(raw, text) is None


@pytest.mark.parametrize("spec", [models.DEFAULT_MODEL, models.CLEANUP_MODEL], ids=lambda s: s.filename)
def test_installed_models_match_their_specs(spec):
    """Verifies the hard-coded sizes and checksums against the real downloaded files."""
    import hashlib
    assert spec.path.stat().st_size == spec.size
    digest = hashlib.sha256()
    with open(spec.path, "rb") as f:
        while chunk := f.read(1 << 24):
            digest.update(chunk)
    assert digest.hexdigest() == spec.sha256
