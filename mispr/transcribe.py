"""Local speech-to-text with whisper.cpp (Metal), run off the main thread.

The audio array is handed to whisper.cpp directly (no Python copy) and the caller
wipes the recording buffer once the text comes back.
"""

import re
import sys
import threading
import time

import numpy as np
from PyObjCTools import AppHelper
from pywhispercpp.model import Model

from .models import DEFAULT_MODEL, ensure_model
from .threads import start_daemon

SAMPLE_RATE = 16_000
LANGUAGE = "en"
MIN_SECONDS = 0.3  # shorter than this is a slip, not speech
SILENCE_PEAK = 0.01  # below this the mic heard nothing; whisper would hallucinate

# Non-speech annotations whisper emits, e.g. [BLANK_AUDIO], (music), [typing].
_ANNOTATION = re.compile(r"\[[^\]]*\]|\([^)]*\)|\*[^*\n]{1,40}\*")  # [Music], (laughs), *Drums*
_SPACES = re.compile(r"\s+")


# What Whisper writes for clicks, breathing or silence (it learned from subtitled videos).
_CREDITS = re.compile(r"\b(?:captions?|subtitles?|subtitled|transcri(?:bed|ption)s?)\s+(?:by|from)\b|amara\.org|"
                      r"gettranscribed|please subscribe|subscribe to (?:my|the|our)", re.I)
_STOCK = {"thank you", "thanks", "thank you very much", "thank you for watching", "thanks for watching", "you", "bye",
          "bye bye", "okay", "ok", "so", "the end", "sorry", "i m sorry", "hmm", "uh", "um"}
SPEECH_MIN_SECONDS = 0.1  # less real speech than this is nothing said (measured: clicks and silence 0.00 s, "Claude." 0.20 s)
STOCK_MAX_SECONDS = 2.0  # a stock phrase from a clip this short, with no speech check, is a guess


def phantom(text, speech_s=None, seconds=0.0):
    """True when `text` is something Whisper made up from noise, not what was said: only
    punctuation (". . ."), subtitle credits ("Captions by …"), or, when the speech detector found
    (almost) no speech, anything at all. Without a speech check, a lone stock phrase ("Thank
    you.") from a very short clip is dropped too."""
    if not re.search(r"[A-Za-z0-9]", text or ""):
        return True
    if _CREDITS.search(text):
        return True
    if speech_s is not None:
        return speech_s < SPEECH_MIN_SECONDS
    said = " ".join(re.findall(r"[a-z]+", text.lower()))
    return said in _STOCK and seconds < STOCK_MAX_SECONDS


CHUNK_PROMPT_CHARS = 200  # how much of the previous piece primes the next


def split_points(audio, rate=SAMPLE_RATE, every=12.0, search=4.0, frame=0.1):
    """Where to cut a long recording into pieces of about `every` seconds: at the quietest
    `frame` within `search` seconds of each target, so a cut falls in a pause, not a word.
    Returns [(start, end)] sample ranges covering the whole recording. Energy is measured
    frame by frame (np.dot on views), so no copy of the audio is made."""
    total, step = len(audio), int(frame * rate)
    bounds, start = [], 0
    while total - start > (every + search) * rate:
        target = start + int(every * rate)
        lo, hi = target - int(search * rate), min(total - step, target + int(search * rate))
        best, best_energy = target, None
        for at in range(lo, hi, step):
            piece = audio[at:at + step]
            energy = float(np.dot(piece, piece))
            if best_energy is None or energy < best_energy:
                best, best_energy = at + step // 2, energy
        bounds.append((start, best))
        start = best
    bounds.append((start, total))
    return bounds


# Names Whisper often mishears: "chat GBT", "git hub". Fixed in every transcript.
_NAMES = [
    (re.compile(r"\bchat\s*-?\s*g\.?\s*[bp]\.?\s*t\b\.?", re.I), "ChatGPT"),
    (re.compile(r"\b(?:git|get)\s*-?\s*hub\b", re.I), "GitHub"),
    (re.compile(r"\byou\s*-?\s*tube\b", re.I), "YouTube"),
    (re.compile(r"\blinked\s*-?\s*in\b(?=\s+(?:profile|post|message|messages|page|account|connections?|feed|learning)\b)|\blinkedin\b", re.I), "LinkedIn"),
    (re.compile(r"\bg\s*-?\s*mail\b", re.I), "Gmail"),
    (re.compile(r"\bmac\s*os\b", re.I), "macOS"),
    (re.compile(r"\bi\s*phone\b", re.I), "iPhone"),
]
# Primes Whisper toward the right spelling of common names when dictating.
DICTATION_VOCABULARY = "ChatGPT, GitHub, YouTube, LinkedIn, Gmail, Google Docs, Slack, Notion, Figma, macOS, iPhone."


def fix_names(text):
    for pattern, name in _NAMES:
        text = pattern.sub(name, text)
    return text


def clean_text(text):
    from .sites import fix_addresses
    return fix_addresses(fix_names(_SPACES.sub(" ", _ANNOTATION.sub("", text)).strip()))


def echoes(text, prompt):
    """True when Whisper just repeated its prompt back (it can, on near-silence): at least half
    of the prompt, word for word. A short command that's also in the prompt ("close tab",
    "YouTube tab") is what was said, not an echo."""
    said = re.findall(r"[a-z0-9]+", text.lower())
    words = re.findall(r"[a-z0-9]+", prompt.lower())
    return (len(said) >= max(3, len(words) // 2)
            and f" {' '.join(said)} " in f" {' '.join(words)} ")  # whole words: "One." isn't "iPhone"


class Transcriber:
    def __init__(self, spec=DEFAULT_MODEL, language=LANGUAGE, clock=time.monotonic):
        self.spec = spec
        self.clock = clock
        self.language = language
        self.error = None
        self._model = None
        self._ready = threading.Event()
        self._lock = threading.Lock()  # whisper.cpp contexts are not re-entrant
        self._loading = False

    @property
    def ready(self):
        return self._ready.is_set() and self._model is not None

    def load_async(self):
        self._loading = True
        start_daemon(self._load, "whisper-load")

    def _load(self):
        try:
            path = ensure_model(self.spec)
            model = Model(
                str(path),
                print_realtime=False,
                print_progress=False,
                redirect_whispercpp_logs_to=None,
            )
            # The first inference compiles Metal pipelines (~1 s); do it now, not on the user's clip.
            model.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), language=self.language)
            self._model = model
        except Exception as e:
            self.error = e
            print(f"mispr: speech model unavailable: {e}", file=sys.stderr)
        finally:
            self._ready.set()

    def ensure_loaded(self):
        """Load on the calling thread if nobody started loading yet (models used only for
        meetings load on first use)."""
        if not self._ready.is_set() and not self._loading:
            self._loading = True
            self._load()

    def transcribe_async(self, audio, on_done, post=None, prompt="", speech=None):
        """Transcribe on a worker thread; `on_done(text, raw, info, seconds)` runs on the main thread.

        `post(raw) -> (text, info)` optionally refines the transcript on the same worker
        (LLM cleanup). `audio` must stay untouched until on_done fires (it is a view of the
        live buffer). `prompt` primes Whisper with expected words (voice commands). `speech(audio)`
        returns seconds of real speech (or None if it can't tell): with too little, nothing is
        transcribed, so a button click never becomes "Thank you." or ".".
        """

        def work():
            started = self.clock()
            speech_s = speech(audio) if speech else None
            raw = "" if speech_s is not None and speech_s < SPEECH_MIN_SECONDS else self._transcribe(audio, prompt)
            if raw and (phantom(raw, speech_s, len(audio) / SAMPLE_RATE) or (prompt and echoes(raw, prompt))):
                raw = ""
            text, info = post(raw) if (post and raw) else (raw, None)
            AppHelper.callAfter(on_done, text, raw, info, self.clock() - started)

        start_daemon(work, "whisper-run")

    def transcribe_chunks_async(self, audio, bounds, on_chunk, on_done, post=None, speech=None):
        """Transcribe a long recording piece by piece, so text can appear while the rest is still
        being worked on. `bounds` are (start, end) sample ranges (split_points). For each piece,
        `on_chunk(i, text, raw, info)` runs on the main thread, then `on_done(seconds)` once.
        Each piece is primed with the end of the one before, so sentences carry over."""

        def work():
            started, before = self.clock(), ""
            for i, (a, b) in enumerate(bounds):
                piece = audio[a:b]
                speech_s = speech(piece) if speech else None
                raw = ("" if speech_s is not None and speech_s < SPEECH_MIN_SECONDS
                       else self._transcribe(piece, f"{DICTATION_VOCABULARY} {before[-CHUNK_PROMPT_CHARS:]}".strip()))
                if raw and (phantom(raw, speech_s, (b - a) / SAMPLE_RATE) or echoes(raw, DICTATION_VOCABULARY)):
                    raw = ""
                text, info = post(raw) if (post and raw) else (raw, None)
                before = raw or before
                AppHelper.callAfter(on_chunk, i, text, raw, info)
            AppHelper.callAfter(on_done, self.clock() - started)

        start_daemon(work, "whisper-chunks")

    def transcribe(self, audio):
        """Transcribe on the calling thread (meeting chunks; serialized with dictation)."""
        return self._transcribe(audio)

    def segments(self, audio):
        """Like transcribe, but timed: [(start_s, end_s, text)] per Whisper segment (meeting
        chunks are split where the speaker changes)."""
        return [(s.t0 / 100, s.t1 / 100, text) for s in self._segments(audio) if (text := clean_text(s.text))]

    def _transcribe(self, audio, prompt=""):
        return clean_text(" ".join(s.text for s in self._segments(audio, prompt)))

    def _segments(self, audio, prompt=""):
        if len(audio) < MIN_SECONDS * SAMPLE_RATE:
            return []
        # max/min reduce in place; np.abs() would make an unwiped copy of the audio.
        if max(float(audio.max()), -float(audio.min())) < SILENCE_PEAK:
            return []
        self._ready.wait()
        if self._model is None:
            return []
        with self._lock:
            # Always pass the prompt: pywhispercpp keeps parameters between calls, so an empty one
            # clears a command hint before the next dictation.
            return self._model.transcribe(audio, language=self.language, initial_prompt=prompt)
