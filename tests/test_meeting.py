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

    def __init__(self, text="hello there", reply=None):
        self.sent = []
        transcriber = type("T", (), {"transcribe": lambda _self, audio: text})()
        cleaner = type("C", (), {"complete": lambda _self, messages, max_tokens=400: reply})()
        self.worker = meeting.MeetingWorker(transcriber, cleaner, lambda event, **f: self.sent.append((event, f)),
                                            start=lambda target, name: None)
        self.worker._jobs.put = lambda job: job()


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
        assert s.sent == [("chunk_text", {"id": "m1", "stream": "you", "offset": 12.5, "text": "hello there", "speaker": 0, "voice": "person"})]
        assert not (tmp_path / "c.wav").exists()

    def test_them_chunks_get_speaker_numbers(self, tmp_path):
        s = Sync()
        for i, voice in enumerate([LOW, HIGH, LOW]):
            write_wav(tmp_path / f"{i}.wav", tone(voice, seed=i))
            s.worker.transcribe_chunk(id="m1", path=str(tmp_path / f"{i}.wav"), stream="them", offset=i)
        assert [f["speaker"] for _, f in s.sent] == [1, 2, 1]

    def test_bad_file_still_reports_and_never_raises(self, tmp_path, capsys):
        s = Sync()
        with pytest.raises(Exception):
            s.worker.transcribe_chunk(id="m1", path=str(tmp_path / "missing.wav"), stream="you", offset=0)
        assert s.sent[0][1]["text"] == ""


class TestVoiceClusters:
    def test_same_voice_same_speaker(self):
        v = meeting.VoiceClusters()
        assert [v.assign(tone(LOW, seed=i)) for i in range(3)] == [1, 1, 1]

    def test_different_voices(self):
        v = meeting.VoiceClusters()
        assert v.assign(tone(LOW)) == 1 and v.assign(tone(HIGH)) == 2

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

    def test_male_female_person(self):
        v = meeting.VoiceClusters()
        low, high = v.assign(tone(LOW)), v.assign(tone(HIGH))
        assert (v.voice(low), v.voice(high)) == ("male", "female")
        mid = [(160 * k, 1 / k) for k in range(1, 12)]  # in the overlap: don't guess
        v2 = meeting.VoiceClusters()
        assert v2.voice(v2.assign(tone(mid))) == "person"
        assert v.voice(99) == "person"

    def test_reported_with_each_chunk(self, tmp_path):
        s = Sync()
        write_wav(tmp_path / "c.wav", tone(HIGH))
        s.worker.transcribe_chunk(id="m1", path=str(tmp_path / "c.wav"), stream="them", offset=0)
        assert s.sent[0][1]["voice"] == "female"


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
