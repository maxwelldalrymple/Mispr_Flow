"""Audio level sources that drive the waveform.

The widget only needs `level(t) -> float in 0..1`. For the UI-only build we fake
speech-like amplitude; the real microphone RMS source will implement the same method.
"""

import math
import random


class FakeLevelSource:
    def __init__(self):
        self._offset = random.uniform(0, 100)

    def level(self, t):
        t += self._offset
        syllables = max(0.0, math.sin(t * 2 * math.pi * 3.3))
        phrase = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 0.35)
        pause = 1.0 if math.sin(t * 2 * math.pi * 0.13) > -0.6 else 0.1
        return min(1.0, (0.25 + 0.75 * syllables) * phrase * pause + random.uniform(0, 0.08))


class PushedLevelSource:
    """Levels pushed in from elsewhere (the app's meeting capture), decaying if they stop."""

    DECAY_AFTER = 0.3  # seconds without an update before the level fades out

    def __init__(self, clock=None):
        import time
        self.clock = clock or time.monotonic
        self._value, self._at = 0.0, 0.0

    def push(self, value):
        self._value, self._at = max(0.0, min(1.0, float(value))), self.clock()

    def level(self, t):
        age = self.clock() - self._at
        return self._value if age < self.DECAY_AFTER else self._value * max(0.0, 1 - (age - self.DECAY_AFTER) * 4)
