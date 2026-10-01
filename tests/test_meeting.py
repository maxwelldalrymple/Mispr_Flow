import json
import wave

import numpy as np
import pytest

from mispr import levels, meeting


def write_wav(path, samples, rate=16_000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())


def tone(freqs, seconds=1.5, rate=16_000, seed=0):
    """A buzzy 'voice': harmonics of a fundamental, with a little noise."""
    t = np.arange(int(rate * seconds)) / rate
    rng = np.random.default_rng(seed)
    sig = sum(a * np.sin(2 * np.pi * f * t) for f, a in freqs)
    return (0.3 * sig / max(1e-9, np.abs(sig).max()) + 0.01 * rng.standard_normal(len(t))).astype(np.float32)


LOW = [(110 * k, 1 / k) for k in range(1, 12)]            # deep voice, strong low harmonics
HIGH = [(260 * k, 1 / (k ** 0.5)) for k in range(1, 10)]   # higher, brighter voice


class Sync:
    """Runs MeetingWorker jobs right away and records what it sends."""

    def __init__(self, text="hello there", reply=None, segments=None, preview=None, embedder=None, speech=None):
        self.sent = []
        # segments(audio) -> [(start, end, text)]: by default one segment covering the chunk.
        segs = segments or (lambda audio: [(0.0, len(audio) / 16_000, text)] if text else [])
        transcriber = type("T", (), {"transcribe": lambda _self, audio: text, "segments": lambda _self, audio: segs(audio)})()
        cleaner = type("C", (), {"complete": lambda _self, messages, max_tokens=400: reply})()
        self.threads = []
        self.worker = meeting.MeetingWorker(transcriber, cleaner, lambda event, **f: self.sent.append((event, f)),
                                            start=lambda target, name: self.threads.append(name),
                                            preview=preview, embedder=embedder, speech=speech)
        self.worker._jobs.put = lambda job: job()
        if preview is not None:
            self.worker._preview_jobs.put = lambda job: job()


class TestReadWav:
    def test_round_trip(self, tmp_path):
        write_wav(tmp_path / "a.wav", np.array([0.0, 0.5, -0.5], dtype=np.float32))
        assert np.allclose(meeting.read_wav(tmp_path / "a.wav"), [0, 0.5, -0.5], atol=1e-3)

    def test_rejects_stereo(self, tmp_path):
        with wave.open(str(tmp_path / "s.wav"), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\0" * 8)
        with pytest.raises(ValueError):
            meeting.read_wav(tmp_path / "s.wav")


class TestTranscribeChunk:
    def test_sends_text_and_deletes_the_chunk(self, tmp_path):
        s = Sync()
        write_wav(tmp_path / "c.wav", tone(LOW))
        s.worker.transcribe_chunk(id="m1", path=str(tmp_path / "c.wav"), stream="you", offset=12.5)
        assert s.sent == [("chunk_text", {"id": "m1", "stream": "you", "offset": 12.5, "text": "hello there", "speaker": 0,
                                          "voice": "person", "last": True})]
        assert not (tmp_path / "c.wav").exists()

    def test_them_chunks_get_speaker_numbers(self, tmp_path):
        s = Sync()
        for i, voice in enumerate([LOW, HIGH, HIGH, LOW]):
            write_wav(tmp_path / f"{i}.wav", tone(voice, seed=i))
            s.worker.transcribe_chunk(id="m1", path=str(tmp_path / f"{i}.wav"), stream="them", offset=i)
        # a new voice is shown as the closest person until a second sentence confirms them
        assert [f["speaker"] for _, f in s.sent] == [1, 1, 2, 1]

    def test_bad_file_still_reports_and_never_raises(self, tmp_path, capsys):
        s = Sync()
        with pytest.raises(Exception):
            s.worker.transcribe_chunk(id="m1", path=str(tmp_path / "missing.wav"), stream="you", offset=0)
        assert s.sent[0][1]["text"] == ""


class TestSplitAtSpeakerChanges:
    """One chunk with two people in it comes back as two lines, one per person."""

    def two_voices(self, tmp_path, segments):
        s = Sync(segments=lambda audio: segments)
        known = meeting.VoiceClusters(gender=False)  # both people already heard (HIGH confirmed)
        known.assign(tone(LOW, 2.0)); known.assign(tone(HIGH, 2.0, seed=1)); known.assign(tone(HIGH, 2.0, seed=2))
        s.worker._voices["m1"] = known
        write_wav(tmp_path / "c.wav", np.concatenate([tone(LOW, 2.0), tone(HIGH, 2.0, seed=1)]))
        s.worker.transcribe_chunk(id="m1", path=str(tmp_path / "c.wav"), stream="them", offset=10.0)
        return [(f["offset"], f["text"], f["speaker"], f["last"]) for _, f in s.sent]

    def test_two_people_two_lines_at_their_times(self, tmp_path):
        got = self.two_voices(tmp_path, [(0.0, 2.0, "Hi there."), (2.0, 4.0, "Hello!")])
        assert got == [(10.0, "Hi there.", 1, False), (12.0, "Hello!", 2, True)]

    def test_same_person_segments_are_joined(self, tmp_path):
        got = self.two_voices(tmp_path, [(0.0, 1.0, "One,"), (1.0, 2.0, "two."), (2.0, 4.0, "Three.")])
        assert [(t, spk) for _, t, spk, _ in got] == [("One, two.", 1), ("Three.", 2)]

    def test_a_short_word_joins_the_speaker_before_it(self, tmp_path):
        got = self.two_voices(tmp_path, [(0.0, 2.0, "So we ship."), (2.0, 2.4, "Yeah."), (2.4, 4.0, "Friday.")])
        assert [(t, spk) for _, t, spk, _ in got] == [("So we ship. Yeah.", 1), ("Friday.", 2)]

    def test_all_short_segments_use_the_whole_chunk(self, tmp_path):
        got = self.two_voices(tmp_path, [(0.0, 0.5, "Ok."), (0.5, 0.9, "Sure.")])
        assert got == [(10.0, "Ok. Sure.", 1, True)]

    def test_nothing_said_still_reports_once(self, tmp_path):
        got = self.two_voices(tmp_path, [])
        assert got == [(10.0, "", 0, True)]


class FakeEmbedder:
    """Fingerprints by loudness: a stand-in for WeSpeaker with known similarities."""

    def __init__(self, vectors):
        self.vectors = vectors  # rounded peak -> vector
        self.calls = 0

    def embed(self, audio):
        self.calls += 1
        v = np.array(self.vectors[round(float(np.abs(audio).max()), 1)], dtype=np.float32)
        return v / np.linalg.norm(v)


class TestEmbeddingClusters:
    """Diarization rules with voice fingerprints: join >= 0.40, a new person only after a second
    matching sentence (>= 0.30), people who turn out alike (>= 0.60) merged and reported."""

    A, B = [1, 0, 0], [0, 1, 0]
    NEAR_A = [0.8, 0.5, 0]  # 0.85 to A
    D = [0.35, 0.937, 0]  # 0.35 to A: a different person
    F = [0.67, 0.74, 0]  # close to D (0.93), drifts D's voice toward A

    def voice(self, peak, seconds=2.0):
        return np.full(int(16_000 * seconds), peak, dtype=np.float32)

    def clusters(self):
        return meeting.VoiceClusters(FakeEmbedder({0.1: self.A, 0.2: self.B, 0.3: self.NEAR_A, 0.5: self.D, 0.6: self.F}),
                                     gender=False)

    def test_joins_the_closest_person(self):
        v = self.clusters()
        assert [v.assign(self.voice(0.1)), v.assign(self.voice(0.3))] == [1, 1]
        assert meeting.VoiceClusters.JOIN == 0.40

    def test_one_odd_sentence_never_makes_a_new_person(self):
        v = self.clusters()
        assert [v.assign(self.voice(p)) for p in (0.1, 0.2, 0.1)] == [1, 1, 1]  # B once: still person 1
        assert v.assign(self.voice(0.2)) == 2  # B again: confirmed, someone new

    def test_people_who_turn_out_alike_are_merged_and_reported(self):
        v = self.clusters()
        for p in (0.1, 0.5, 0.5):
            v.assign(self.voice(p))
        assert set(v.centroids) == {1, 2}
        for _ in range(10):
            v.assign(self.voice(0.6))
            if v.merges:
                break
        assert v.merges == [(2, 1)] and set(v.centroids) == {1}
        assert v.assign(self.voice(0.5)) == 1  # their voice now belongs to person 1

    def test_short_unclear_speech_never_starts_a_new_person(self):
        v = self.clusters()
        v.assign(self.voice(0.1))
        assert v.assign(self.voice(0.2, seconds=1.2)) == 1 and v.pending == []
        assert [v.assign(self.voice(0.2, seconds=1.6)) for _ in range(2)] == [1, 2]

    def test_only_clear_speech_refines_a_voice(self):
        v = self.clusters()
        v.assign(self.voice(0.1))
        before = v.centroids[1].copy()
        v.assign(self.voice(0.3, seconds=1.2))
        assert np.array_equal(v.centroids[1], before)
        v.assign(self.voice(0.3, seconds=2.0))
        assert not np.array_equal(v.centroids[1], before)

    def test_too_short_to_fingerprint_is_the_last_speaker(self):
        v = self.clusters()
        for p in (0.1, 0.2, 0.2):
            v.assign(self.voice(p))
        e = v.embedder.calls
        assert v.assign(self.voice(0.1, seconds=0.5)) == 2 and v.embedder.calls == e

    def test_at_most_eight_people(self):
        vectors = {round(0.1 * (i + 1), 1): np.eye(10)[i] for i in range(10)}
        v = meeting.VoiceClusters(FakeEmbedder(vectors), gender=False)
        for i in range(10):
            for _ in range(2):
                v.assign(self.voice(round(0.1 * (i + 1), 1)))
        assert len(v.centroids) <= 8

    def test_falls_back_to_the_signature_without_a_model(self):
        dead = type("E", (), {"embed": lambda self, audio: None})()
        v = meeting.VoiceClusters(dead, gender=False)
        assert [v.assign(tone(LOW)), v.assign(tone(HIGH)), v.assign(tone(HIGH, seed=1))] == [1, 1, 2]
        assert v._thresholds[0] == meeting.VoiceClusters.SIGNATURE_JOIN

    def test_merges_are_sent_to_the_app(self, tmp_path):
        s = Sync()
        v = self.clusters()
        v.merges = [(2, 1)]
        s.worker._voices["m1"] = v
        write_wav(tmp_path / "c.wav", tone(LOW))
        s.worker.transcribe_chunk(id="m1", path=str(tmp_path / "c.wav"), stream="them", offset=0)
        assert ("speakers_merged", {"id": "m1", "speaker": 2, "into": 1}) in s.sent and v.merges == []


class TestGender:
    """Male/female: fingerprint classifier averaged with pitch."""

    def test_shipped_weights_load_for_titanet(self):
        g = meeting.GenderModel.load()
        assert g is not None and len(g.weights) == 192

    def test_missing_or_mismatched_is_none(self, tmp_path):
        assert meeting.GenderModel.load(tmp_path / "nope.json") is None
        assert meeting.GenderModel([0.1] * 4, 0).female(np.ones(3)) is None

    def test_fingerprint_and_pitch_are_averaged(self):
        v = meeting.VoiceClusters(gender=False)
        v.female[1] = [0.9]  # the fingerprint says female...
        v.pitches[1] = [120.0]  # ...pitch says male (score ~0.08): average 0.49 -> male
        assert v.voice(1) == "male"
        v.pitches[1] = [140.0]  # ~0.38: average 0.64 -> female
        assert v.voice(1) == "female"
        v2 = meeting.VoiceClusters(gender=False)
        v2.female[1] = [0.2]
        assert v2.voice(1) == "male"  # no pitch: the fingerprint alone

    def test_classifier_output_is_a_probability(self):
        g = meeting.GenderModel([1.0, -1.0], 0.0)
        assert g.female(np.array([2.0, 0.0])) > 0.85 and g.female(np.array([0.0, 2.0])) < 0.15


class TestSpeakerEmbedder:
    def test_unavailable_model_means_none_once(self, capsys):
        tries = []

        def ensure(spec):
            tries.append(spec)
            raise OSError("offline")

        e = meeting.SpeakerEmbedder(ensure=ensure)
        assert e.embed(tone(LOW)) is None and e.embed(tone(LOW)) is None
        assert len(tries) == 1 and "speaker model unavailable" in capsys.readouterr().err

    def test_uses_sherpa_onnx_and_returns_a_unit_vector(self, monkeypatch, tmp_path):
        import sys, types
        got = {}

        class Stream:
            def accept_waveform(self, rate, audio): got["rate"], got["n"] = rate, len(audio)
            def input_finished(self): got["finished"] = True

        class Extractor:
            def __init__(self, config): got["model"] = config.model
            def create_stream(self): return Stream()
            def compute(self, stream): return [3.0, 4.0]

        fake = types.SimpleNamespace(SpeakerEmbeddingExtractor=Extractor,
                                     SpeakerEmbeddingExtractorConfig=lambda model, num_threads: types.SimpleNamespace(model=model))
        monkeypatch.setitem(sys.modules, "sherpa_onnx", fake)
        e = meeting.SpeakerEmbedder(ensure=lambda spec: tmp_path / spec.filename)
        assert np.allclose(e.embed(np.zeros(16_000, dtype=np.float32)), [0.6, 0.8])
        assert got == {"model": str(tmp_path / "nemo_en_titanet_large.onnx"), "rate": 16_000, "n": 16_000, "finished": True}

    def test_zero_vector_is_none(self, monkeypatch, tmp_path):
        import sys, types
        ext = type("X", (), {"__init__": lambda self, c: None, "create_stream": lambda self: types.SimpleNamespace(
            accept_waveform=lambda r, a: None, input_finished=lambda: None), "compute": lambda self, s: [0.0, 0.0]})
        monkeypatch.setitem(sys.modules, "sherpa_onnx", types.SimpleNamespace(
            SpeakerEmbeddingExtractor=ext, SpeakerEmbeddingExtractorConfig=lambda model, num_threads: None))
        assert meeting.SpeakerEmbedder(ensure=lambda spec: tmp_path).embed(np.zeros(10, dtype=np.float32)) is None


class TestVoiceClusters:
    def test_same_voice_same_speaker(self):
        v = meeting.VoiceClusters()
        assert [v.assign(tone(LOW, seed=i)) for i in range(3)] == [1, 1, 1]

    def test_different_voices_after_a_second_sentence(self):
        v = meeting.VoiceClusters()
        assert [v.assign(tone(LOW)), v.assign(tone(HIGH)), v.assign(tone(HIGH, seed=1))] == [1, 1, 2]

    def test_too_short_to_measure_joins_the_main_speaker(self):
        v = meeting.VoiceClusters()
        v.assign(tone(LOW))
        assert v.assign(np.zeros(100, dtype=np.float32)) == 1


class TestSummary:
    LINES = [{"speaker": "You", "text": "Let's ship Friday."}, {"speaker": "Them", "text": "I'll write the notes."}]

    def test_parses_the_model_json(self):
        reply = 'Sure! {"title": "Release plan", "overview": "Ship Friday.", "decisions": ["Ship Friday"], ' \
                '"action_items": [{"owner": "Them", "task": "Write notes", "due": ""}, {"task": ""}], "open_questions": []}'
        s = Sync(reply=reply)
        s.worker.summarize(id="m1", lines=self.LINES)
        event, fields = s.sent[0]
        assert event == "summary" and fields["summary"]["title"] == "Release plan"
        assert fields["summary"]["action_items"] == [{"owner": "Them", "task": "Write notes", "due": ""}]

    def test_unparseable_reply_is_none(self):
        s = Sync(reply="no json here")
        s.worker.summarize(id="m1", lines=self.LINES)
        assert s.sent[0][1]["summary"] is None

    def test_empty_meeting_skips_the_model(self):
        s = Sync(reply=None)
        s.worker.summarize(id="m1", lines=[])
        assert s.sent == [("summary", {"id": "m1", "summary": None})]

    def test_transcript_text(self):
        assert meeting.transcript_text(self.LINES + [{"speaker": "Them", "text": ""}]) == \
            "You: Let's ship Friday.\nThem: I'll write the notes."


class TestAsk:
    def test_answers(self):
        s = Sync(reply=" Friday. ")
        s.worker.ask(id="m1", question="When do we ship?", lines=TestSummary.LINES)
        assert s.sent == [("answer", {"id": "m1", "question": "When do we ship?", "text": "Friday."})]

    def test_what_did_i_miss_is_an_empty_question(self):
        asked = []
        s = Sync()
        s.worker.cleaner = type("C", (), {"complete": lambda _s, messages, max_tokens=0: asked.append(messages) or "Recap."})()
        s.worker.ask(id="m1", question="", lines=TestSummary.LINES)
        assert meeting.MISSED_QUESTION in asked[0][1]["content"] and s.sent[0][1]["text"] == "Recap."

    def test_nothing_said_yet(self):
        s = Sync()
        s.worker.ask(id="m1", question="Anything?", lines=[])
        assert s.sent[0][1]["text"] == "Nothing has been said yet."


class TestPushedLevels:
    def test_push_then_decay(self):
        now = [0.0]
        p = levels.PushedLevelSource(clock=lambda: now[0])
        p.push(0.8)
        assert p.level(0) == 0.8
        now[0] = 0.4
        assert 0 < p.level(0) < 0.8
        now[0] = 2.0
        assert p.level(0) == 0.0

    def test_clamped(self):
        p = levels.PushedLevelSource(clock=lambda: 0.0)
        p.push(5)
        assert p.level(0) == 1.0


class TestVoiceKind:
    def test_pitch_of_a_low_and_a_high_voice(self):
        assert 100 < meeting.VoiceClusters.pitch(tone(LOW)) < 120
        assert 245 < meeting.VoiceClusters.pitch(tone(HIGH)) < 275

    def test_noise_has_no_pitch(self):
        rng = np.random.default_rng(1)
        assert meeting.VoiceClusters.pitch((0.2 * rng.standard_normal(32000)).astype(np.float32)) is None

    def test_male_female_by_pitch_around_145_hz(self):
        v = meeting.VoiceClusters(gender=False)
        low = v.assign(tone(LOW)); v.assign(tone(HIGH)); high = v.assign(tone(HIGH, seed=1))
        assert (v.voice(low), v.voice(high)) == ("male", "female")
        zoom_woman = [(152 * k, 1 / k) for k in range(1, 12)]  # women measured ~150 Hz in a Zoom call
        v2 = meeting.VoiceClusters(gender=False)
        assert v2.voice(v2.assign(tone(zoom_woman))) == "female"
        assert v.voice(99) == "person"  # nothing heard

    def test_reported_with_each_chunk(self, tmp_path):
        s = Sync()
        write_wav(tmp_path / "c.wav", tone(HIGH))
        s.worker.transcribe_chunk(id="m1", path=str(tmp_path / "c.wav"), stream="them", offset=0)
        assert s.sent[0][1]["voice"] == "female"


class TestPreviewThread:
    """Live previews run on their own thread with the small model, so final text never waits."""

    class Small:
        def __init__(self):
            self.loaded = 0

        def ensure_loaded(self):
            self.loaded += 1

        def transcribe(self, audio):
            return "fast words"

    def test_two_threads_and_previews_use_the_small_model(self, tmp_path):
        small = self.Small()
        s = Sync(preview=small)
        assert s.threads == ["meeting-worker", "meeting-preview"]
        assert s.worker._preview_jobs is not s.worker._jobs
        write_wav(tmp_path / "p.wav", tone(LOW))
        s.worker.transcribe_chunk(id="m1", path=str(tmp_path / "p.wav"), stream="you", offset=1.0, partial=True)
        assert s.sent[-1][1]["text"] == "fast words" and small.loaded == 1
        write_wav(tmp_path / "f.wav", tone(LOW))
        s.worker.transcribe_chunk(id="m1", path=str(tmp_path / "f.wav"), stream="you", offset=1.0)
        assert s.sent[-1][1]["text"] == "hello there"  # finals still use the big model

    def test_without_a_small_model_previews_share_the_queue(self):
        s = Sync()
        assert s.threads == ["meeting-worker"] and s.worker._preview_jobs is s.worker._jobs


class TestPreview:
    def test_preview_is_marked_partial_and_skips_speakers(self, tmp_path):
        s = Sync()
        write_wav(tmp_path / "p.wav", tone(HIGH))
        s.worker.transcribe_chunk(id="m1", path=str(tmp_path / "p.wav"), stream="them", offset=4.0, partial=True)
        assert s.sent == [("chunk_text", {"id": "m1", "stream": "them", "offset": 4.0, "text": "hello there",
                                          "speaker": 0, "voice": "", "partial": True})]
        assert "m1" not in s.worker._voices  # previews don't train the speaker groups

    def test_only_the_newest_preview_runs(self, tmp_path):
        s = Sync()
        queued = []
        s.worker._jobs.put = queued.append  # hold jobs, like a busy worker
        for i in range(3):
            write_wav(tmp_path / f"{i}.wav", tone(LOW))
            s.worker.transcribe_chunk(id="m1", path=str(tmp_path / f"{i}.wav"), stream="them", offset=float(i), partial=True)
        assert len(queued) == 1
        assert not (tmp_path / "0.wav").exists() and not (tmp_path / "1.wav").exists()  # stale ones dropped
        queued[0]()
        assert [f["offset"] for _, f in s.sent] == [2.0]

    def test_streams_preview_independently(self, tmp_path):
        s = Sync()
        queued = []
        s.worker._jobs.put = queued.append
        for stream in ("you", "them"):
            write_wav(tmp_path / f"{stream}.wav", tone(LOW))
            s.worker.transcribe_chunk(id="m1", path=str(tmp_path / f"{stream}.wav"), stream=stream, offset=0, partial=True)
        assert len(queued) == 2
