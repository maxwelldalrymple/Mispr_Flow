"""Microphone capture into a locked, wipeable in-memory buffer.

Privacy rules (see README):
- Audio never touches disk; it lives in one preallocated NumPy buffer.
- The buffer's pages are mlock'ed so they cannot be swapped out.
- After use the written region is zeroed in place (`wipe`), and the buffer is
  never converted to immutable `bytes`, which could not be wiped.
Known limitation: PortAudio's transient callback buffers are owned by the
library; we copy out of them immediately and cannot zero them ourselves.
"""

import ctypes
import ctypes.util
import math
import sys
import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000  # what whisper.cpp expects
MAX_SECONDS = 10 * 60
BLOCK = 512  # ~32 ms per callback

# Map RMS loudness to the 0..1 waveform range.
FLOOR_DB, CEIL_DB = -55.0, -12.0

_libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


class SecureAudioBuffer:
    def __init__(self, seconds=MAX_SECONDS, rate=SAMPLE_RATE):
        self.data = np.zeros(seconds * rate, dtype=np.float32)
        self.length = 0
        self._ptr = ctypes.c_void_p(self.data.ctypes.data)
        self._nbytes = ctypes.c_size_t(self.data.nbytes)
        self.locked = _libc.mlock(self._ptr, self._nbytes) == 0
        if not self.locked:
            print(f"whispr: mlock failed (errno {ctypes.get_errno()}); audio may be swappable", file=sys.stderr)

    def append(self, samples):
        n = min(len(samples), len(self.data) - self.length)
        self.data[self.length:self.length + n] = samples[:n]
        self.length += n
        return n == len(samples)  # False once the buffer is full

    def view(self):
        """Zero-copy view of the recorded samples. Do not keep it past wipe()."""
        return self.data[:self.length]

    def wipe(self):
        self.data[:self.length].fill(0.0)
        self.length = 0

    def close(self):
        self.data.fill(0.0)
        self.length = 0
        if self.locked:
            _libc.munlock(self._ptr, self._nbytes)
            self.locked = False


class Recorder:
    """Opens the mic only while recording, so the macOS mic indicator is honest."""

    def __init__(self):
        self.buffer = SecureAudioBuffer()
        self._stream = None
        self._lock = threading.Lock()
        self._level = 0.0

    @property
    def recording(self):
        return self._stream is not None

    def start(self):
        """Begin a fresh recording. Returns False if the microphone could not be opened."""
        self.stop()
        self.buffer.wipe()
        self._level = 0.0
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                blocksize=BLOCK, callback=self._callback,
            )
            self._stream.start()
        except Exception as e:  # no device, or microphone permission denied
            print(f"whispr: could not open microphone: {e}", file=sys.stderr)
            self._stream = None
            return False
        return True

    def stop(self):
        """Stop capturing. The audio stays in the buffer until wipe()."""
        stream, self._stream = self._stream, None
        if stream is not None:
            stream.stop()
            stream.close()
        self._level = 0.0

    def audio(self):
        return self.buffer.view()

    def wipe(self):
        with self._lock:
            self.buffer.wipe()

    def level(self, t=None):
        return self._level

    def _callback(self, indata, frames, time_info, status):
        mono = indata[:, 0]
        with self._lock:
            self.buffer.append(mono)
        rms = float(np.sqrt(np.mean(mono * mono))) if frames else 0.0
        db = 20 * math.log10(rms) if rms > 1e-9 else FLOOR_DB
        target = min(1.0, max(0.0, (db - FLOOR_DB) / (CEIL_DB - FLOOR_DB)))
        # Fast attack, slower release, so the waveform feels responsive but not jittery.
        k = 0.6 if target > self._level else 0.2
        self._level += (target - self._level) * k
