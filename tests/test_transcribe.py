import threading

import numpy as np
import pytest

from whispr import transcribe
from whispr.transcribe import Transcriber, clean_text


class TestCleanText:
    @pytest.mark.parametrize("raw,expected", [
        ("Hello world", "Hello world"),
        ("  padded  ", "padded"),
        ("[BLANK_AUDIO]", ""),
        ("Hello [BLANK_AUDIO] world", "Hello world"),
        ("(music) Hi there (applause)", "Hi there"),
        ("[typing] (door closes) done", "done"),
        ("multiple   spaces\tand\nnewlines", "multiple spaces and newlines"),
        ("", ""),
    ])
    def test_cases(self, raw, expected):
        assert clean_text(raw) == expected

    def test_keeps_normal_punctuation(self):
        assert clean_text("Wait, what? Yes!") == "Wait, what? Yes!"


class Segment:
    def __init__(self, text):
        self.text = text


class FakeModel:
    """Stub + spy for pywhispercpp's Model."""

    def __init__(self, texts=("Hello world.",)):
        self.texts = texts
        self.seen = []

    def transcribe(self, audio, language):
        self.seen.append((audio, language))
        return [Segment(t) for t in self.texts]


class Clock:
    def __init__(self, *readings):
        self.readings = list(readings)

    def __call__(self):
        return self.readings.pop(0)


def ready_transcriber(model, **kw):
    t = Transcriber(**kw)
    t._model = model
    t._ready.set()
    return t


def tone(seconds, amplitude):
    return np.full(int(round(seconds * transcribe.SAMPLE_RATE)), amplitude, np.float32)


class TestGates:
    """Boundary-value tables for the two gates that stop Whisper hallucinating on non-speech."""

    @pytest.mark.parametrize("seconds,transcribed", [(0.0, False), (0.29, False), (0.3, True), (5.0, True)])
    def test_minimum_length(self, seconds, transcribed):
        model = FakeModel()
        out = ready_transcriber(model)._transcribe(tone(seconds, 0.5))
        assert out == ("Hello world." if transcribed else "")  # always a str, never None
        assert len(model.seen) == int(transcribed)

    # Audio is float32: 0.01 itself is stored as 0.0099999998 (< the float64 threshold), so the
    # boundary is probed with representable values just either side of it.
    @pytest.mark.parametrize("peak,transcribed", [(0.0, False), (0.0099, False), (0.01001, True), (0.5, True)])
    def test_silence_threshold(self, peak, transcribed):
        model = FakeModel()
        out = ready_transcriber(model)._transcribe(tone(1.0, peak))
        assert out == ("Hello world." if transcribed else "")

    def test_thresholds_are_the_documented_values(self):
        assert transcribe.MIN_SECONDS == 0.3 and transcribe.SILENCE_PEAK == 0.01

    def test_negative_only_signal_counts_as_loud(self, speech):
        assert ready_transcriber(FakeModel())._transcribe(-np.abs(speech)) == "Hello world."

    def test_waits_for_model_to_finish_loading(self, speech):
        t = Transcriber()
        model = FakeModel()

        class Loading:  # the load completes while the dictation is waiting
            waits = 0

            def wait(self, timeout=None):
                Loading.waits += 1
                t._model = model
                return True

        t._ready = Loading()
        assert t._transcribe(speech) == "Hello world." and Loading.waits == 1

    def test_model_unavailable_returns_empty(self, speech):
        t = Transcriber()
        t._ready.set()
        assert t._transcribe(speech) == ""

    def test_audio_is_passed_without_copy(self, speech):
        model = FakeModel()
        ready_transcriber(model)._transcribe(speech)
        assert model.seen[0][0] is speech  # the buffer view itself, so wiping covers it
        assert model.seen[0][1] == "en"

    def test_segments_joined_and_cleaned(self, speech):
        model = FakeModel(texts=(" Hello", " [BLANK_AUDIO]", " world. "))
        assert ready_transcriber(model)._transcribe(speech) == "Hello world."

    def test_language_is_configurable(self, speech):
        model = FakeModel()
        ready_transcriber(model, language="fr")._transcribe(speech)
        assert model.seen[0][1] == "fr"


class TestTranscribeAsync:
    @staticmethod
    def run(t, audio, post=None):
        results = []
        t.transcribe_async(audio, lambda *args: results.append(args), post=post)
        (result,) = results  # inline_threads + immediate callAfter: exactly one synchronous callback
        return dict(zip(("text", "raw", "info", "secs"), result))

    def test_without_post(self, speech):
        r = self.run(ready_transcriber(FakeModel(), clock=Clock(1.0, 1.9)), speech)
        assert r == {"text": "Hello world.", "raw": "Hello world.", "info": None, "secs": pytest.approx(0.9)}

    def test_runs_on_named_daemon_worker(self, speech, inline_threads):
        self.run(ready_transcriber(FakeModel(), clock=Clock(0, 0)), speech)
        assert inline_threads == ["whisper-run"]

    def test_post_processing_applied(self, speech):
        post = lambda raw: (raw.upper(), {"applied": True})
        r = self.run(ready_transcriber(FakeModel(), clock=Clock(0, 0)), speech, post=post)
        assert r["raw"] == "Hello world."
        assert r["text"] == "HELLO WORLD." and r["info"] == {"applied": True}

    def test_post_skipped_for_empty_transcript(self):
        calls = []
        r = self.run(ready_transcriber(FakeModel(), clock=Clock(0, 0)), np.zeros(100, np.float32),
                     post=lambda raw: calls.append(raw))
        assert r["text"] == "" and calls == []

    def test_elapsed_includes_post_processing(self, speech):
        r = self.run(ready_transcriber(FakeModel(), clock=Clock(5.0, 7.5)), speech, post=lambda raw: (raw, {}))
        assert r["secs"] == pytest.approx(2.5)


class TestTranscriberLifecycle:
    def test_ready_property(self):
        t = Transcriber()
        assert not t.ready
        t._ready.set()
        assert not t.ready  # ready flag without a model is still not usable
        t._model = FakeModel()
        assert t.ready

    @pytest.fixture
    def model_spy(self, monkeypatch, tmp_path):
        models = []

        class FakeModelCls(FakeModel):
            def __init__(self, path, **kw):
                super().__init__()
                self.path, self.kw = path, kw
                models.append(self)

        monkeypatch.setattr(transcribe, "Model", FakeModelCls)
        monkeypatch.setattr(transcribe, "ensure_model", lambda spec: tmp_path / "w.bin")
        return models

    def test_load_configures_quiet_model(self, model_spy, tmp_path):
        t = Transcriber()
        t._load()
        (m,) = model_spy
        assert t.ready and t.error is None and m.path == str(tmp_path / "w.bin")
        assert m.kw == {"print_realtime": False, "print_progress": False, "redirect_whispercpp_logs_to": None}

    def test_load_warms_up_with_one_second_of_silence(self, model_spy):
        Transcriber()._load()
        (audio, lang), = model_spy[0].seen
        assert len(audio) == transcribe.SAMPLE_RATE and not audio.any() and lang == "en"

    def test_load_failure_recorded(self, monkeypatch):
        def boom(spec):
            raise OSError("disk full")

        monkeypatch.setattr(transcribe, "ensure_model", boom)
        t = Transcriber()
        t._load()
        assert t._ready.is_set() and not t.ready and isinstance(t.error, OSError)

    def test_load_async_uses_named_daemon_worker(self, monkeypatch, inline_threads):
        monkeypatch.setattr(Transcriber, "_load", lambda self: None)
        Transcriber().load_async()
        assert inline_threads == ["whisper-load"]
