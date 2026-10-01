"""Meeting notes in the engine: the app captures the audio (mic = "you", system audio =
"them"), cuts it into chunks at pauses, and asks the engine to transcribe each one; at the
end it asks for a summary. Answers questions about the meeting too. All local.

Final text runs on one worker thread, in order, so transcript chunks come back in sequence.
Live previews (the words still being said) run on their own thread with a small, fast
Whisper model, so they never hold up the final text and keep up with the speaker.

Who's talking: each stretch of "them" audio gets a voice fingerprint (WeSpeaker, 256
numbers), compared by cosine similarity with the people heard so far. A chunk is split where
Whisper's segments change speaker.
"""

import json
import queue
import re
import sys
import threading
import wave
from pathlib import Path

import numpy as np

from .models import PREVIEW_MODEL, SPEAKER_MODEL, ensure_model
from .threads import start_daemon

SUMMARY_PROMPT = """You write meeting notes from a transcript. "You" is the person taking notes; "Them" is everyone else on the call.
Return only JSON with these keys:
{"title": short meeting title (max 6 words),
 "overview": 2-3 sentence summary,
 "decisions": [decisions that were made],
 "action_items": [{"owner": "You" or "Them" or a name mentioned, "task": "...", "due": "when, or empty"}],
 "open_questions": [questions left unanswered]}
Only include things actually said. Use empty lists when there are none."""

ASK_PROMPT = """You answer questions about a meeting using only its transcript. "You" is the note taker; "Them" is everyone else.
Be brief (1-4 sentences). If the transcript doesn't say, answer "The meeting didn't cover that." """

MISSED_QUESTION = "Summarize what was said in the last few minutes in 2-3 sentences, as if catching someone up."


def read_wav(path):
    """16-bit mono WAV -> float32 samples in [-1, 1]."""
    with wave.open(str(path)) as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            raise ValueError(f"expected 16-bit mono, got {w.getsampwidth() * 8}-bit x{w.getnchannels()}")
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768


class SpeakerEmbedder:
    """Voice fingerprints from the WeSpeaker model (via sherpa-onnx), loaded on first use.
    `embed` returns a unit vector, or None if the model isn't available (then the meeting
    falls back to the rougher spectral signature)."""

    def __init__(self, spec=SPEAKER_MODEL, ensure=ensure_model):
        self.spec, self.ensure = spec, ensure
        self._extractor = None
        self._failed = False
        self._lock = threading.Lock()

    def _load(self):
        if self._extractor is None and not self._failed:
            try:
                import sherpa_onnx
                path = self.ensure(self.spec)
                self._extractor = sherpa_onnx.SpeakerEmbeddingExtractor(
                    sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(path), num_threads=2))
            except Exception as e:  # missing package, no download yet (offline), bad file
                self._failed = True
                print(f"mispr: speaker model unavailable, using the simple voice signature: {e}", file=sys.stderr)
        return self._extractor

    def embed(self, audio, rate=16_000):
        with self._lock:
            extractor = self._load()
            if extractor is None:
                return None
            stream = extractor.create_stream()
            stream.accept_waveform(rate, audio)
            stream.input_finished()
            vector = np.array(extractor.compute(stream), dtype=np.float32)
        norm = np.linalg.norm(vector)
        return vector / norm if norm else None


class VoiceClusters:
    """Tells the other people on a call apart. Each stretch of speech gets a voice
    fingerprint; it's the same person as the closest one heard so far when their cosine
    similarity is high enough, otherwise a new person. Names can be fixed by hand afterwards.

    With the WeSpeaker model (`embedder`), tested on a real 4-person meeting (AMI EN2002b):
    the same voice scores ~0.75 and different voices ~0.48, so 0.60 splits them and found
    exactly 4 people. Without it, a spectral signature with a much higher bar is used.
    """

    SAME_SPEAKER = 0.60  # cosine similarity for one voice (WeSpeaker fingerprints)
    SAME_SPEAKER_SIGNATURE = 0.93  # for the fallback spectral signature
    MIN_SECONDS = 1.0  # shorter speech is too little to fingerprint: it joins its neighbour
    NEW_SPEAKER_SECONDS = 1.5  # only this much clear speech can start a new person or teach a voice
    MAX_SPEAKERS = 8
    BANDS = 24

    # Typical speaking pitch: men ~85-155 Hz, women ~165-255 Hz. In between, or no clear
    # pitch (music, noise, a dog), the voice is just "person".
    MALE_MAX, FEMALE_MIN = 155.0, 168.0

    def __init__(self, embedder=None):
        self.embedder = embedder
        self.centroids, self.counts, self.pitches = [], [], []
        self.last = 0  # the most recent speaker, for stretches too short to tell

    @staticmethod
    def pitch(audio, rate=16_000):
        """Median fundamental frequency (Hz) of the voiced frames, or None."""
        frame = 1024
        if len(audio) < frame * 2:
            return None
        found = []
        for start in range(0, len(audio) - frame, frame // 2):
            x = audio[start:start + frame]
            x = x - x.mean()
            energy = float(x @ x)
            if energy < 1e-4:
                continue
            ac = np.correlate(x, x, "full")[frame - 1:] / energy
            lo, hi = int(rate / 300), int(rate / 70)  # 70-300 Hz
            lag = lo + int(np.argmax(ac[lo:hi]))
            if ac[lag] > 0.45:  # clearly periodic: a voice
                found.append(rate / lag)
        return float(np.median(found)) if len(found) >= 3 else None

    def voice(self, speaker):
        """"male", "female", or "person" for a 1-based speaker number."""
        values = self.pitches[speaker - 1] if 0 < speaker <= len(self.pitches) else []
        if len(values) == 0:
            return "person"
        f0 = float(np.median(values))
        return "male" if f0 <= self.MALE_MAX else "female" if f0 >= self.FEMALE_MIN else "person"

    @classmethod
    def signature(cls, audio, rate=16_000):
        frame, hop = 1024, 256  # 64 ms frames (16 Hz resolution, enough for low voices), 16 ms hop
        if len(audio) < frame * 4:
            return None
        frames = np.lib.stride_tricks.sliding_window_view(audio, frame)[::hop] * np.hanning(frame)
        energy = (frames ** 2).mean(axis=1)
        voiced = frames[energy > max(1e-6, np.percentile(energy, 60))]  # the louder, voiced frames
        if len(voiced) < 5:
            return None
        spectrum = np.abs(np.fft.rfft(voiced, axis=1))
        freqs = np.fft.rfftfreq(frame, 1 / rate)
        edges = np.geomspace(100, 4000, cls.BANDS + 1)  # voice range, log-spaced like hearing
        cols = []
        for lo, hi in zip(edges, edges[1:]):
            inside = (freqs >= lo) & (freqs < hi)
            if not inside.any():  # a band narrower than one bin: use the nearest bin
                inside = np.abs(freqs - (lo + hi) / 2) == np.abs(freqs - (lo + hi) / 2).min()
            cols.append(spectrum[:, inside].mean(axis=1))
        bands = np.stack(cols, axis=1)
        logs = np.log(bands + 1e-6)
        sig = np.concatenate([logs.mean(axis=0) - logs.mean(), logs.std(axis=0)])
        norm = np.linalg.norm(sig)
        return sig / norm if norm else None

    def fingerprint(self, audio):
        """(vector, threshold) for this audio, or (None, None) if it can't be measured."""
        if self.embedder is not None:
            vector = self.embedder.embed(audio)
            if vector is not None:
                return vector, self.SAME_SPEAKER
        sig = self.signature(audio)
        return (sig, self.SAME_SPEAKER_SIGNATURE) if sig is not None else (None, None)

    def assign(self, audio, rate=16_000):
        """1-based speaker number for this stretch of speech."""
        speaker = self._assign(audio, rate)
        f0 = self.pitch(audio)
        while len(self.pitches) < speaker:
            self.pitches.append([])
        if f0 is not None:
            self.pitches[speaker - 1].append(f0)
        self.last = speaker
        return speaker

    def _assign(self, audio, rate):
        fallback = self.last or (int(np.argmax(self.counts)) + 1 if self.counts else 1)
        if len(audio) < self.MIN_SECONDS * rate:
            return fallback
        vector, threshold = self.fingerprint(audio)
        if vector is None:
            return fallback
        clear = len(audio) >= self.NEW_SPEAKER_SECONDS * rate
        if self.centroids:
            sims = [float(vector @ c / np.linalg.norm(c)) for c in self.centroids]
            best = int(np.argmax(sims))
            if sims[best] >= threshold or not clear or len(self.centroids) >= self.MAX_SPEAKERS:
                if clear:  # only clear speech refines what a voice sounds like
                    self.centroids[best] = self.centroids[best] + vector
                self.counts[best] += 1
                return best + 1
        self.centroids.append(vector.copy())
        self.counts.append(1)
        return len(self.centroids)

    def split(self, audio, segments, rate=16_000):
        """Whisper's timed segments -> [(start_s, end_s, text, speaker)], with neighbouring
        segments by the same person joined. Short segments ("yeah") join the speaker around them."""
        pieces = []
        for start, end, text in segments:
            clip = audio[int(start * rate):int(end * rate)]
            long_enough = len(clip) >= self.MIN_SECONDS * rate
            speaker = self.assign(clip, rate) if long_enough else None
            pieces.append([start, end, text, speaker])
        known = [p[3] for p in pieces if p[3] is not None]
        if not known:  # all short: the chunk as a whole decides
            whole = self.assign(audio, rate)
            known = [whole]
        prev = known[0]
        for p in pieces:
            prev = p[3] = p[3] if p[3] is not None else prev
        merged = []
        for start, end, text, speaker in pieces:
            if merged and merged[-1][3] == speaker:
                merged[-1][1], merged[-1][2] = end, f"{merged[-1][2]} {text}"
            else:
                merged.append([start, end, text, speaker])
        return [tuple(p) for p in merged]


def transcript_text(lines):
    """[{"speaker", "text"}...] -> 'You: …' lines for the LLM."""
    return "\n".join(f"{line.get('speaker', 'Them')}: {line.get('text', '')}" for line in lines if line.get("text"))


def parse_summary(text):
    """The model's JSON reply -> summary dict with every key present, or None."""
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    items = []
    for item in data.get("action_items") or []:
        if isinstance(item, dict) and item.get("task"):
            items.append({"owner": str(item.get("owner") or "You"), "task": str(item["task"]), "due": str(item.get("due") or "")})
    as_list = lambda key: [str(x) for x in (data.get(key) or []) if str(x).strip()]
    return {
        "title": str(data.get("title") or "").strip(),
        "overview": str(data.get("overview") or "").strip(),
        "decisions": as_list("decisions"),
        "action_items": items,
        "open_questions": as_list("open_questions"),
    }


class MeetingWorker:
    """`preview` is the fast Whisper model for live text (its own thread); without one,
    previews share the final-text queue. `embedder` fingerprints voices."""

    def __init__(self, transcriber, cleaner, send, start=start_daemon, preview=None, embedder=None):
        self.transcriber, self.cleaner, self.send = transcriber, cleaner, send
        self.preview = preview
        self.embedder = embedder
        self._jobs = queue.Queue()
        self._preview_jobs = queue.Queue() if preview is not None else self._jobs
        self._voices = {}  # meeting id -> VoiceClusters for "them"
        self._partials = {}  # (meeting id, stream) -> newest live-preview request
        self._partials_lock = threading.Lock()
        start(lambda: self._run(self._jobs), "meeting-worker")
        if preview is not None:
            start(lambda: self._run(self._preview_jobs), "meeting-preview")

    def _run(self, jobs=None):
        jobs = jobs or self._jobs
        while True:
            job = jobs.get()
            try:
                job()
            except Exception as e:  # one bad chunk must never stop the meeting
                print(f"mispr: meeting job failed: {e}", file=sys.stderr)

    # Commands from the app (host.listen calls these with the message's arguments).

    def transcribe_chunk(self, id="", path="", stream="them", offset=0.0, delete=True, partial=False):
        if partial:
            return self._preview(id, path, stream, offset, delete)

        def job():
            # [(offset, text, speaker)]: one line per speaker in this chunk. The last event for
            # a chunk carries last=True so the app knows the chunk is done.
            lines = []
            try:
                audio = read_wav(path)
                if stream == "them":
                    segments = self.transcriber.segments(audio)
                    if segments:
                        voices = self._voices.setdefault(id, VoiceClusters(self.embedder))
                        lines = [(offset + start, text, speaker) for start, _, text, speaker in voices.split(audio, segments)]
                else:
                    text = self.transcriber.transcribe(audio)
                    lines = [(offset, text, 0)] if text else []
            finally:
                if delete:
                    Path(path).unlink(missing_ok=True)
                voices = self._voices.get(id)
                for i, (at, text, speaker) in enumerate(lines or [(offset, "", 0)]):
                    voice = voices.voice(speaker) if (voices and speaker) else "person"
                    self.send("chunk_text", id=id, stream=stream, offset=at, text=text, speaker=speaker, voice=voice,
                              last=i == max(len(lines), 1) - 1)
        self._jobs.put(job)

    def _preview(self, id, path, stream, offset, delete):
        """Live text for the phrase still being spoken. Only the newest request per stream
        runs; older ones still waiting are dropped, so previews never fall behind."""
        key = (id, stream)
        with self._partials_lock:
            stale = self._partials.get(key)
            self._partials[key] = (path, offset, delete)
        if stale is not None:
            if stale[2]:
                Path(stale[0]).unlink(missing_ok=True)
            return  # a run is already queued; it will pick up this newer audio

        def job():
            with self._partials_lock:
                path_, offset_, delete_ = self._partials.pop(key)
            text = ""
            try:
                if self.preview is not None:
                    self.preview.ensure_loaded()  # first meeting: fetch/load the small model here, off the final queue
                text = (self.preview or self.transcriber).transcribe(read_wav(path_))
            finally:
                if delete_:
                    Path(path_).unlink(missing_ok=True)
                self.send("chunk_text", id=id, stream=stream, offset=offset_, text=text, speaker=0, voice="", partial=True)
        self._preview_jobs.put(job)

    def summarize(self, id="", lines=()):
        def job():
            summary = None
            if lines:
                reply = self.cleaner.complete(
                    [{"role": "system", "content": SUMMARY_PROMPT},
                     {"role": "user", "content": transcript_text(lines)}], max_tokens=700)
                summary = parse_summary(reply)
            self.send("summary", id=id, summary=summary)
        self._jobs.put(job)

    def ask(self, id="", question="", lines=()):
        def job():
            q = question.strip() or MISSED_QUESTION
            if not lines:
                answer = "Nothing has been said yet."
            else:
                recent = list(lines)[-40:] if q == MISSED_QUESTION else list(lines)
                answer = (self.cleaner.complete(
                    [{"role": "system", "content": ASK_PROMPT},
                     {"role": "user", "content": f"Transcript:\n{transcript_text(recent)}\n\nQuestion: {q}"}],
                    max_tokens=220) or "").strip() or "I couldn't answer that."
            self.send("answer", id=id, question=question, text=answer)
        self._jobs.put(job)
