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
import time
import re
import sys
import threading
import wave
from pathlib import Path

import numpy as np

from .models import PREVIEW_MODEL, SPEAKER_MODEL, VAD_MODEL, ensure_model
from .threads import start_daemon


def log(message):
    """One line in the engine log (stderr), with the time."""
    print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)

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


class SpeechDetector:
    """How much real speech a clip has (Silero VAD via sherpa-onnx), loaded on first use.
    Clicks, typing and background noise count as none. Returns None if the model is
    unavailable, so callers keep the clip rather than lose words."""

    MIN_SPEECH = 0.15  # seconds of speech for a clip to be worth transcribing
    THRESHOLD, MIN_SPEECH_RUN, MIN_SILENCE = 0.5, 0.1, 0.25  # tested: clicks/typing 0 s, short "yeah"s kept

    def __init__(self, spec=VAD_MODEL, ensure=ensure_model):
        self.spec, self.ensure = spec, ensure
        self._config = None
        self._failed = False
        self._lock = threading.Lock()

    def _load(self):
        if self._config is None and not self._failed:
            try:
                import sherpa_onnx
                config = sherpa_onnx.VadModelConfig()
                config.silero_vad.model = str(self.ensure(self.spec))
                config.silero_vad.threshold = self.THRESHOLD
                config.silero_vad.min_speech_duration = self.MIN_SPEECH_RUN
                config.silero_vad.min_silence_duration = self.MIN_SILENCE
                config.sample_rate = 16_000
                self._sherpa, self._config = sherpa_onnx, config
            except Exception as e:
                self._failed = True
                print(f"mispr: speech detector unavailable, transcribing every clip: {e}", file=sys.stderr)
        return self._config

    def speech_seconds(self, audio, rate=16_000):
        with self._lock:
            config = self._load()
            if config is None:
                return None
            vad = self._sherpa.VoiceActivityDetector(config, buffer_size_in_seconds=max(30, len(audio) / rate + 5))
            window = config.silero_vad.window_size
            for i in range(0, len(audio) - window + 1, window):
                vad.accept_waveform(audio[i:i + window])
            vad.flush()
            total = 0
            while not vad.empty():
                total += len(vad.front.samples)
                vad.pop()
        return total / rate

    def has_speech(self, audio, rate=16_000):
        """False only when the detector is sure there's no speech (a click, typing, silence)."""
        seconds = self.speech_seconds(audio, rate)
        return seconds is None or seconds >= self.MIN_SPEECH


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


class GenderModel:
    """Female probability from a voice fingerprint: logistic regression trained on TitaNet
    fingerprints of 96 voices (AMI Meeting Corpus and LibriSpeech, both CC BY 4.0; held out
    by person: 76/80 LibriSpeech and 13/16 AMI voices right). Weights: voice_gender.json."""

    PATH = Path(__file__).with_name("voice_gender.json")

    def __init__(self, weights, bias):
        self.weights, self.bias = np.asarray(weights, dtype=np.float32), float(bias)

    @classmethod
    def load(cls, path=None):
        try:
            data = json.loads(Path(path or cls.PATH).read_text())
            return cls(data["weights"], data["bias"])
        except (OSError, ValueError, KeyError):
            return None

    def female(self, vector):
        if len(vector) != len(self.weights):
            return None  # a fingerprint from another model
        return float(1 / (1 + np.exp(-(vector @ self.weights + self.bias))))


class VoiceClusters:
    """Tells the people on a call apart (speaker diarization), and guesses male/female.

    Each stretch of speech gets a voice fingerprint (TitaNet). It joins the most similar
    person when cosine similarity >= JOIN. Otherwise it waits as "maybe someone new" (shown
    as the closest known person); a second stretch that matches it (>= CONFIRM) makes a new
    person. People whose voices turn out alike (>= MERGE) are merged, and `merges` reports it
    so the app relabels their lines. One odd-sounding sentence never creates a new person.

    Tested on 6 real AMI meetings (23 people): the old rule (new person below 0.60) made 45
    people and switched labels mid-person 9% of the time; these rules: 0% switches, 100% of each
    person's speech under one label, at the cost of merging a few alike voices (18 found).
    """

    JOIN, CONFIRM, MERGE = 0.40, 0.30, 0.60  # TitaNet cosine similarities
    SIGNATURE_JOIN, SIGNATURE_CONFIRM, SIGNATURE_MERGE = 0.93, 0.95, 0.97  # fallback spectral signature
    MIN_SECONDS = 1.0  # shorter speech is too little to fingerprint: it joins its neighbour
    NEW_SPEAKER_SECONDS = 1.5  # only this much clear speech can start a new person or teach a voice
    MAX_SPEAKERS = 8
    BANDS = 24
    # Male/female: the average of a fingerprint classifier (trained on 96 voices: AMI +
    # LibriSpeech) and a pitch score centred on 145 Hz (in a Zoom recording women measured
    # ~150-155 Hz and men 115-132; in AMI women 163-227 and men 113-142).
    PITCH_MIDDLE, PITCH_SPREAD = 145.0, 10.0

    def __init__(self, embedder=None, gender=None):
        self.embedder = embedder
        self.gender = gender if gender is not None else GenderModel.load()
        self.centroids, self.counts, self.pitches, self.female = {}, {}, {}, {}  # by speaker id
        self.pending = []  # fingerprints of "maybe someone new": [(vector, shown as)]
        self.merges = []  # [(from, into)] since the worker last looked
        self.next_id = 1
        self.last = 0  # the most recent speaker, for stretches too short to tell
        self._thresholds = (self.JOIN, self.CONFIRM, self.MERGE)

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
        """"male", "female", or "person" (nothing heard to judge by) for a speaker id."""
        scores = []
        if self.female.get(speaker):
            scores.append(float(np.mean(self.female[speaker])))
        if self.pitches.get(speaker):
            f0 = float(np.median(self.pitches[speaker]))
            scores.append(1 / (1 + np.exp(-(f0 - self.PITCH_MIDDLE) / self.PITCH_SPREAD)))
        if not scores:
            return "person"
        return "female" if np.mean(scores) >= 0.5 else "male"

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
        """This audio's voice vector (or None), using the signature thresholds if it's the fallback."""
        if self.embedder is not None:
            vector = self.embedder.embed(audio)
            if vector is not None:
                self._thresholds = (self.JOIN, self.CONFIRM, self.MERGE)
                return vector, True
        sig = self.signature(audio)
        self._thresholds = (self.SIGNATURE_JOIN, self.SIGNATURE_CONFIRM, self.SIGNATURE_MERGE)
        return sig, False

    def assign(self, audio, rate=16_000):
        """Speaker id (1, 2, ...) for this stretch of speech."""
        self._sure = True
        speaker = self._assign(audio, rate)
        f0 = self.pitch(audio) if self._sure else None  # a "maybe someone new" doesn't teach anyone's voice
        if f0 is not None:
            self.pitches.setdefault(speaker, []).append(f0)
        self.last = speaker
        return speaker

    def _new(self, vector, female):
        speaker, self.next_id = self.next_id, self.next_id + 1
        self.centroids[speaker], self.counts[speaker] = vector.copy(), 1
        if female is not None:
            self.female[speaker] = [female]
        return speaker

    def _assign(self, audio, rate):
        fallback = self.last or (max(self.counts, key=self.counts.get) if self.counts else 1)
        if len(audio) < self.MIN_SECONDS * rate:
            return fallback
        vector, real = self.fingerprint(audio)
        if vector is None:
            return fallback
        join, confirm, _ = self._thresholds
        female = self.gender.female(vector) if (real and self.gender) else None
        clear = len(audio) >= self.NEW_SPEAKER_SECONDS * rate
        if not self.centroids:
            return self._new(vector, female) if clear else 1
        sims = {k: float(vector @ c / np.linalg.norm(c)) for k, c in self.centroids.items()}
        best = max(sims, key=sims.get)
        if sims[best] >= join or not clear or len(self.centroids) >= self.MAX_SPEAKERS:
            if clear:  # only clear speech refines what a voice sounds like
                self.centroids[best] = self.centroids[best] + vector
                if female is not None:
                    self.female.setdefault(best, []).append(female)
            self.counts[best] += 1
            self._merge_alike()
            return best
        for i, (waiting, _) in enumerate(self.pending):  # a second match: someone new for sure
            if float(vector @ waiting) >= confirm:
                self.pending.pop(i)
                return self._new(vector + waiting, female)
        self.pending = (self.pending + [(vector, best)])[-5:]
        self._sure = False
        self.counts[best] += 1
        return best  # shown as the closest known person until confirmed

    def _merge_alike(self):
        _, _, merge = self._thresholds
        while True:
            ids = sorted(self.centroids)
            pair = next(((a, b) for i, a in enumerate(ids) for b in ids[i + 1:]
                         if float(self.centroids[a] @ self.centroids[b]
                                  / np.linalg.norm(self.centroids[a]) / np.linalg.norm(self.centroids[b])) >= merge), None)
            if pair is None:
                return
            into, gone = pair  # the earlier person keeps their label
            self.centroids[into] = self.centroids[into] + self.centroids.pop(gone)
            self.counts[into] += self.counts.pop(gone)
            self.pitches.setdefault(into, []).extend(self.pitches.pop(gone, []))
            self.female.setdefault(into, []).extend(self.female.pop(gone, []))
            self.last = into if self.last == gone else self.last
            self.merges.append((gone, into))

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

    def __init__(self, transcriber, cleaner, send, start=start_daemon, preview=None, embedder=None, speech=None,
                 clock=time.monotonic):
        self.transcriber, self.cleaner, self.send = transcriber, cleaner, send
        self.preview = preview
        self.embedder = embedder
        self.speech = speech  # SpeechDetector: clips with no real speech (clicks, typing) are skipped
        self.clock = clock
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

        queued = self.clock()

        def job():
            # [(offset, text, speaker)]: one line per speaker in this chunk. The last event for
            # a chunk carries last=True so the app knows the chunk is done.
            lines = []
            started = self.clock()
            try:
                audio = read_wav(path)
                if self.speech is not None and not self.speech.has_speech(audio):
                    log(f"meeting: {stream} {len(audio) / 16_000:.1f}s chunk skipped, no speech (a click or noise)")
                    return
                if stream == "them":
                    segments = self.transcriber.segments(audio)
                    if segments:
                        voices = self._voices.setdefault(id, VoiceClusters(self.embedder))
                        lines = [(offset + start, text, speaker) for start, _, text, speaker in voices.split(audio, segments)]
                else:
                    text = self.transcriber.transcribe(audio)
                    lines = [(offset, text, 0)] if text else []
                log(f"meeting: {stream} {len(audio) / 16_000:.1f}s chunk -> {len(lines)} line(s) "
                    f"in {self.clock() - started:.2f}s, waited {started - queued:.2f}s in line")
            finally:
                if delete:
                    Path(path).unlink(missing_ok=True)
                voices = self._voices.get(id)
                for gone, into in (voices.merges if voices else []):  # same person after all: relabel
                    self.send("speakers_merged", id=id, speaker=gone, into=into)
                if voices:
                    voices.merges = []
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
                audio = read_wav(path_)
                if self.speech is None or self.speech.has_speech(audio):
                    text = (self.preview or self.transcriber).transcribe(audio)
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
