import threading

import numpy as np
import pytest

from mispr import transcribe
from mispr.transcribe import Transcriber, clean_text


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
    def __init__(self, text, t0=0, t1=100):
        self.text, self.t0, self.t1 = text, t0, t1  # pywhispercpp times are in centiseconds


class FakeModel:
    """Stub + spy for pywhispercpp's Model."""

    def __init__(self, texts=("Hello world.",)):
        self.texts = texts
        self.seen = []

    def transcribe(self, audio, language, initial_prompt=""):
        self.seen.append((audio, language))
        self.prompts = getattr(self, "prompts", []) + [initial_prompt]
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


class TestTimedSegments:
    """Meeting chunks get Whisper's segments with times, to split where the speaker changes."""

    def test_seconds_and_clean_text(self, speech):
        model = FakeModel()
        model.transcribe = lambda audio, language, initial_prompt="": [Segment(" Hi [MUSIC] there.", 0, 150), Segment(" (laughs) ", 150, 200),
                                                    Segment(" Bye.", 200, 310)]
        assert ready_transcriber(model).segments(speech) == [(0.0, 1.5, "Hi there."), (2.0, 3.1, "Bye.")]

    def test_silence_and_short_audio_have_none(self):
        t = ready_transcriber(FakeModel())
        assert t.segments(tone(2, 0.001)) == [] and t.segments(tone(0.1, 0.5)) == []


class TestEnsureLoaded:
    def test_loads_once_on_the_calling_thread(self, monkeypatch):
        loads = []
        monkeypatch.setattr(Transcriber, "_load", lambda self: loads.append(1) or self._ready.set())
        t = Transcriber()
        t.ensure_loaded()
        t.ensure_loaded()
        assert loads == [1]

    def test_not_again_while_a_background_load_runs(self, monkeypatch, inline_threads):
        loads = []
        monkeypatch.setattr(Transcriber, "_load", lambda self: loads.append(1))  # never finishes
        t = Transcriber()
        t.load_async()
        t.ensure_loaded()
        assert loads == [1]


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


def test_a_command_hint_never_sticks_to_the_next_dictation(speech):
    model = FakeModel()
    t = ready_transcriber(model)
    t._transcribe(speech, "Voice commands: tab left.")
    t._transcribe(speech)
    assert model.prompts == ["Voice commands: tab left.", ""]  # cleared, since pywhispercpp keeps parameters


class TestPhantoms:
    """Whisper's made-up text for clicks and silence never reaches the user."""

    @pytest.mark.parametrize("text", [".", ". . . . .", "…", "Captions by GetTranscribed.com", "Subtitles by the Amara.org community"])
    def test_always_phantoms(self, text):
        from mispr.transcribe import phantom
        assert phantom(text, None, 5.0) and phantom(text, 2.0, 5.0)

    def test_no_speech_means_nothing_was_said(self):
        from mispr.transcribe import phantom
        assert phantom("Thank you.", 0.0, 1.2)
        assert not phantom("Thank you.", 0.6, 1.2)  # really said

    def test_stock_phrase_without_a_speech_check_only_when_very_short(self):
        from mispr.transcribe import phantom
        assert phantom("Thank you.", None, 1.2)
        assert not phantom("Thank you.", None, 3.0)
        assert not phantom("chatgpt.com", None, 1.6)  # a real web address stays

    def test_speech_gate_skips_whisper(self, speech):
        model = FakeModel()
        t = ready_transcriber(model, clock=Clock(0, 0))
        results = []
        t.transcribe_async(speech, lambda *a: results.append(a), speech=lambda audio: 0.0)
        assert results[0][0] == "" and model.seen == []

    def test_phantom_output_is_dropped(self, speech):
        t = ready_transcriber(FakeModel(texts=("Thank you.",)), clock=Clock(0, 0))
        results = []
        t.transcribe_async(speech, lambda *a: results.append(a), speech=lambda audio: 0.05)
        assert results[0][0] == ""


class TestSplitPoints:
    def test_cuts_land_in_pauses(self):
        from mispr.transcribe import split_points
        sr = 16000
        a = np.random.default_rng(0).normal(0, 0.1, sr * 40).astype(np.float32)
        a[int(13.5 * sr):int(14 * sr)] = 0
        a[int(27 * sr):int(27.4 * sr)] = 0
        bounds = split_points(a)
        assert len(bounds) == 3 and bounds[0][0] == 0 and bounds[-1][1] == len(a)
        assert 13.5 <= bounds[0][1] / sr <= 14 and 27 <= bounds[1][1] / sr <= 27.4
        assert all(b[1] == n[0] for b, n in zip(bounds, bounds[1:]))  # no gaps, no overlaps

    def test_short_audio_is_one_piece(self):
        from mispr.transcribe import split_points
        a = np.zeros(16000 * 15, np.float32)
        assert split_points(a) == [(0, len(a))]


class TestTranscribeChunks:
    def test_each_piece_reported_in_order_with_the_previous_as_prompt(self, speech):
        class OneAtATime(FakeModel):
            def transcribe(self, audio, language, initial_prompt=""):
                super().transcribe(audio, language, initial_prompt)
                return [Segment(("One.", "Two.")[len(self.seen) - 1])]
        model = OneAtATime()
        t = ready_transcriber(model, clock=Clock(0, 3.0))
        audio = np.concatenate([speech, speech])
        pieces, done = [], []
        t.transcribe_chunks_async(audio, [(0, 16000), (16000, 32000)], lambda *a: pieces.append(a), done.append,
                                  post=lambda raw: (raw.upper(), {"applied": True}))
        assert [p[:3] for p in pieces] == [(0, "ONE.", "One."), (1, "TWO.", "Two.")]
        assert done == [pytest.approx(3.0)]
        assert model.prompts[1].endswith("One.")

    def test_silent_piece_is_skipped(self, speech):
        model = FakeModel(texts=("Hi.",))
        t = ready_transcriber(model, clock=Clock(0, 0))
        pieces = []
        t.transcribe_chunks_async(speech, [(0, 16000)], lambda *a: pieces.append(a), lambda s: None, speech=lambda a: 0.0)
        assert pieces[0][1] == "" and model.seen == []


def test_sound_labels_in_asterisks_are_removed():
    assert clean_text("*Drums*") == "" and clean_text("*repeat* *repeat*") == ""
    assert clean_text("Hello *music* world") == "Hello world"


class TestNamesAndEchoes:
    @pytest.mark.parametrize("raw, expected", [
        ("Open chat GBT and git hub", "Open ChatGPT and GitHub"), ("I watched it on you tube", "I watched it on YouTube"),
        ("my linked in profile", "my LinkedIn profile"), ("I got linked in to the call", "I got linked in to the call"),
        ("go to chat gbt dot com", "go to chatgpt.com"), ("email bob dot com", "email bob dot com"),
        ("I will get up early", "I will get up early"),
    ])
    def test_names_fixed(self, raw, expected):
        assert clean_text(raw) == expected

    def test_prompt_echo(self):
        from mispr.transcribe import DICTATION_VOCABULARY, echoes
        assert echoes("ChatGPT, GitHub, YouTube, LinkedIn, Gmail, Google Docs, Slack.", DICTATION_VOCABULARY)
        assert not echoes("ChatGPT, GitHub.", DICTATION_VOCABULARY)  # a short real sentence
        assert not echoes("One.", DICTATION_VOCABULARY) and not echoes("Open GitHub please", DICTATION_VOCABULARY)

    @pytest.mark.parametrize("command", ["YouTube tab.", "GitHub tab", "close tab", "New tab.", "tab left", "tabs side by side"])
    def test_commands_in_the_hint_are_never_echoes(self, command):
        from mispr import apps
        from mispr.transcribe import echoes
        assert not echoes(command, apps.command_prompt())  # 1.1.0/1.1.1 dropped these
