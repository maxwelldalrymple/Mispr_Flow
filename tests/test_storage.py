import json
import sys
import wave
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from mispr import storage

T0 = datetime(2026, 9, 30, 12, 28, 33, 123456)
APP = {"app": "Notes", "bundle_id": "com.apple.Notes", "url": "ignored", "page_title": "ignored"}
PAGE = {"app": "Google Chrome", "bundle_id": "com.google.Chrome", "url": "https://example.com", "page_title": "Example"}


def save(audio=None, **overrides):
    kw = dict(status=storage.PASTED, transcript="hello there world", started_at=T0,
              ended_at=T0 + timedelta(seconds=2), recorded_in=APP, pasted_into=PAGE, model="m.bin")
    kw.update(overrides)
    if audio is None:
        audio = np.full(32000, 0.25, np.float32)
    return storage.save_recording(audio, **kw)


def meta_of(wav_path):
    return json.loads(wav_path.with_suffix(".json").read_text())


class TestStem:
    @pytest.mark.parametrize("micro,expected_ms", [(0, "000"), (1_000, "001"), (123_456, "123"), (999_999, "999")])
    def test_milliseconds(self, micro, expected_ms):
        assert storage._stem(T0.replace(microsecond=micro)) == f"2026-09-30_12-28-33-{expected_ms}"

    def test_zero_padded_fields(self):
        assert storage._stem(datetime(2026, 1, 2, 3, 4, 5, 6000)) == "2026-01-02_03-04-05-006"

    def test_sorts_chronologically(self):
        stamps = [T0 + timedelta(milliseconds=ms) for ms in (5, 900, 1500, 61000)]
        stems = [storage._stem(t) for t in stamps]
        assert stems == sorted(stems)


class TestDataRoot:
    def test_source_checkout_uses_project_folder(self, monkeypatch):
        monkeypatch.delattr(sys, "frozen", raising=False)
        assert storage._data_root() == Path(storage.__file__).resolve().parent.parent

    def test_packaged_app_uses_application_support(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        assert storage._data_root() == Path.home() / "Library" / "Application Support" / "Mispr_Flow"


class TestSaveRecording:
    def test_files_named_by_start_time_in_day_folder(self, isolated_paths):
        wav = save()
        assert wav == isolated_paths / "voice-recordings" / "2026-09-30" / "2026-09-30_12-28-33-123.wav"
        assert wav.exists() and wav.with_suffix(".json").exists()

    def test_wav_format(self):
        with wave.open(str(save())) as w:
            assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 16000, 32000)

    def test_samples_scaled_to_int16(self):
        audio = np.array([0.0, 0.5, -0.5, 1.0, -1.0], np.float32)
        with wave.open(str(save(audio))) as w:
            pcm = np.frombuffer(w.readframes(5), "<i2")
        assert pcm.tolist() == [0, 16383, -16383, 32767, -32767]

    def test_out_of_range_samples_clipped(self):
        audio = np.array([2.0, -3.0], np.float32)
        with wave.open(str(save(audio))) as w:
            assert np.frombuffer(w.readframes(2), "<i2").tolist() == [32767, -32767]

    def test_does_not_modify_input_audio(self):
        audio = np.array([2.0, 0.5], np.float32)
        save(audio)
        assert audio.tolist() == [2.0, 0.5]

    def test_metadata_fields(self):
        m = meta_of(save())
        assert m["id"] == "2026-09-30_12-28-33-123"
        assert m["started_at"].startswith("2026-09-30T12:28:33.123")
        assert m["ended_at"].startswith("2026-09-30T12:28:35.123")
        assert m["duration_s"] == 2.0
        assert m["status"] == "pasted"
        assert m["transcript"] == "hello there world"
        assert m["words"] == 3
        assert m["model"] == "m.bin"
        assert m["audio_file"] == "2026-09-30_12-28-33-123.wav"

    def test_timestamps_include_timezone_offset(self):
        m = meta_of(save())
        assert m["started_at"][-6] in "+-" and m["started_at"][-3] == ":"

    def test_duration_precision(self):
        assert meta_of(save(np.zeros(12345, np.float32)))["duration_s"] == round(12345 / 16000, 3)

    def test_recorded_in_keeps_only_app_fields(self):
        assert meta_of(save())["recorded_in"] == {"app": "Notes", "bundle_id": "com.apple.Notes"}

    def test_recorded_in_missing_keys_become_null(self):
        assert meta_of(save(recorded_in={}))["recorded_in"] == {"app": None, "bundle_id": None}

    def test_pasted_into_stored_verbatim(self):
        assert meta_of(save())["pasted_into"] == PAGE

    def test_cancelled_recording_has_no_paste_target(self):
        m = meta_of(save(status=storage.CANCELLED, transcript="", pasted_into=None))
        assert m["status"] == "cancelled" and m["pasted_into"] is None and m["words"] == 0

    def test_raw_transcript_defaults_to_transcript(self):
        assert meta_of(save())["raw_transcript"] == "hello there world"

    def test_raw_transcript_and_cleanup_recorded(self):
        info = {"model": "gemma", "applied": True, "ms": 512, "rejected": None}
        m = meta_of(save(transcript="Hello there.", raw_transcript="um hello there", cleanup=info))
        assert m["raw_transcript"] == "um hello there" and m["cleanup"] == info

    def test_json_is_pretty_printed_with_two_spaces(self):
        text = save().with_suffix(".json").read_text()
        assert text.startswith('{\n  "id": ') and '\n    "app": ' in text

    def test_unicode_preserved_not_escaped(self):
        wav = save(transcript="Café in São Paulo — naïve 😀")
        raw_json = wav.with_suffix(".json").read_text()
        assert "São Paulo" in raw_json and "\\u" not in raw_json

    def test_word_count_ignores_extra_whitespace(self):
        assert meta_of(save(transcript="  one   two\tthree\n"))["words"] == 3

    def test_two_recordings_same_second_do_not_collide(self):
        a = save(started_at=T0)
        b = save(started_at=T0 + timedelta(milliseconds=1))
        assert a != b and a.exists() and b.exists()

    def test_recordings_on_different_days_get_different_folders(self):
        a = save(started_at=T0)
        b = save(started_at=T0 + timedelta(days=1))
        assert a.parent.name == "2026-09-30" and b.parent.name == "2026-10-01"

    def test_empty_audio_still_writes_valid_files(self):
        wav = save(np.zeros(0, np.float32))
        with wave.open(str(wav)) as w:
            assert w.getnframes() == 0
        assert meta_of(wav)["duration_s"] == 0.0


def test_set_transcript_keeps_what_was_heard(tmp_path):
    wav = tmp_path / "x.wav"
    wav.with_suffix(".json").write_text('{"transcript": "Open clawed folder.", "raw_transcript": "Open clawed folder.", "words": 3}')
    storage.set_transcript(wav, "Opened claude")
    import json
    meta = json.loads(wav.with_suffix(".json").read_text())
    assert meta == {"transcript": "Opened claude", "raw_transcript": "Open clawed folder.", "words": 2}
