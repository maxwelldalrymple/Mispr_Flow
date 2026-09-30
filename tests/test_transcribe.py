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
    def __init__(self, texts=("Hello world.",)):
        self.texts = texts
        self.seen = []

    def transcribe(self, audio, language):
        self.seen.append((audio, language))
        return [Segment(t) for t in self.texts]


def ready_transcriber(model):
    t = Transcriber()
    t._model = model
    t._ready.set()
    return t


class TestTranscribeGates:
    def test_too_short_is_skipped_without_model(self):
        model = FakeModel()
        t = ready_transcriber(model)
        assert t._transcribe(np.full(int(0.29 * 16000), 0.5, np.float32)) == ""
        assert model.seen == []

    def test_silence_is_skipped(self):
        model = FakeModel()
        assert ready_transcriber(model)._transcribe(np.full(16000, 0.005, np.float32)) == ""
        assert model.seen == []

    def test_negative_only_signal_counts_as_loud(self, speech):
        model = FakeModel()
        audio = -np.abs(speech)  # peak comes from the minimum
        assert ready_transcriber(model)._transcribe(audio) == "Hello world."

    def test_exactly_min_length_is_transcribed(self):
        model = FakeModel()
        audio = np.full(int(transcribe.MIN_SECONDS * 16000), 0.5, np.float32)
        assert ready_transcriber(model)._transcribe(audio) == "Hello world."

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
        t = Transcriber(language="fr")
        t._model, _ = model, t._ready.set()
        t._transcribe(speech)
        assert model.seen[0][1] == "fr"


class TestTranscribeAsync:
    def run(self, t, audio, post=None):
        result, done = {}, threading.Event()

        def on_done(text, raw, info, secs):
            result.update(text=text, raw=raw, info=info, secs=secs, thread=threading.current_thread())
            done.set()

        t.transcribe_async(audio, on_done, post=post)
        assert done.wait(5)
        return result

    def test_without_post(self, speech):
        r = self.run(ready_transcriber(FakeModel()), speech)
        assert r["text"] == r["raw"] == "Hello world." and r["info"] is None
        assert r["secs"] >= 0

    def test_runs_off_the_calling_thread(self, speech):
        r = self.run(ready_transcriber(FakeModel()), speech)
        assert r["thread"] is not threading.main_thread()

    def test_post_processing_applied(self, speech):
        post = lambda raw: (raw.upper(), {"applied": True})
        r = self.run(ready_transcriber(FakeModel()), speech, post=post)
        assert r["raw"] == "Hello world."
        assert r["text"] == "HELLO WORLD." and r["info"] == {"applied": True}

    def test_post_skipped_for_empty_transcript(self):
        calls = []
        r = self.run(ready_transcriber(FakeModel()), np.zeros(100, np.float32), post=lambda raw: calls.append(raw))
        assert r["text"] == "" and calls == []


class TestTranscriberLifecycle:
    def test_ready_property(self):
        t = Transcriber()
        assert not t.ready
        t._ready.set()
        assert not t.ready  # ready flag without a model is still not usable
        t._model = FakeModel()
        assert t.ready

    def test_load_success_warms_up(self, monkeypatch, tmp_path):
        models = []

        class FakeModelCls(FakeModel):
            def __init__(self, path, **kw):
                super().__init__()
                self.path, self.kw = path, kw
                models.append(self)

        monkeypatch.setattr(transcribe, "Model", FakeModelCls)
        monkeypatch.setattr(transcribe, "ensure_model", lambda spec: tmp_path / "w.bin")
        t = Transcriber()
        t._load()
        assert t.ready and t.error is None
        m = models[0]
        assert m.path == str(tmp_path / "w.bin")
        assert m.kw["redirect_whispercpp_logs_to"] is None  # whisper logs silenced
        assert len(m.seen) == 1 and len(m.seen[0][0]) == transcribe.SAMPLE_RATE  # 1 s warm-up

    def test_load_failure_recorded(self, monkeypatch):
        def boom(spec):
            raise OSError("disk full")

        monkeypatch.setattr(transcribe, "ensure_model", boom)
        t = Transcriber()
        t._load()
        assert t._ready.is_set() and not t.ready and isinstance(t.error, OSError)

    def test_load_async_runs_in_background(self, monkeypatch):
        done = threading.Event()
        monkeypatch.setattr(Transcriber, "_load", lambda self: done.set())
        Transcriber().load_async()
        assert done.wait(2)
