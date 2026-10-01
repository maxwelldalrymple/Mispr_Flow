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
_ANNOTATION = re.compile(r"\[[^\]]*\]|\([^)]*\)")
_SPACES = re.compile(r"\s+")


def clean_text(text):
    return _SPACES.sub(" ", _ANNOTATION.sub("", text)).strip()


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

    def transcribe_async(self, audio, on_done, post=None):
        """Transcribe on a worker thread; `on_done(text, raw, info, seconds)` runs on the main thread.

        `post(raw) -> (text, info)` optionally refines the transcript on the same worker
        (LLM cleanup). `audio` must stay untouched until on_done fires (it is a view of the
        live buffer).
        """

        def work():
            started = self.clock()
            raw = self._transcribe(audio)
            text, info = post(raw) if (post and raw) else (raw, None)
            AppHelper.callAfter(on_done, text, raw, info, self.clock() - started)

        start_daemon(work, "whisper-run")

    def transcribe(self, audio):
        """Transcribe on the calling thread (meeting chunks; serialized with dictation)."""
        return self._transcribe(audio)

    def segments(self, audio):
        """Like transcribe, but timed: [(start_s, end_s, text)] per Whisper segment (meeting
        chunks are split where the speaker changes)."""
        return [(s.t0 / 100, s.t1 / 100, text) for s in self._segments(audio) if (text := clean_text(s.text))]

    def _transcribe(self, audio):
        return clean_text(" ".join(s.text for s in self._segments(audio)))

    def _segments(self, audio):
        if len(audio) < MIN_SECONDS * SAMPLE_RATE:
            return []
        # max/min reduce in place; np.abs() would make an unwiped copy of the audio.
        if max(float(audio.max()), -float(audio.min())) < SILENCE_PEAK:
            return []
        self._ready.wait()
        if self._model is None:
            return []
        with self._lock:
            return self._model.transcribe(audio, language=self.language)
