"""Synthesize Mispr Flow's sound cues into mispr/assets/sounds/: python tools/make_sounds.py

Every cue is generated from scratch here (sine partials, pitch glides, envelopes, and a
little seeded noise), so the sounds are original and MIT licensed like the rest of the
app. Their lengths, pitch ranges, and loudness were tuned to feel like the cues in other
dictation apps: short, soft, and pitched in the 300-500 Hz range so they sit under speech.
"""
import wave
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent.parent / "mispr" / "assets" / "sounds"
SR = 48000
rng = np.random.default_rng(7)


def t_of(seconds):
    return np.arange(int(SR * seconds)) / SR


def env(n, attack, decay, hold=0.0):
    """Linear-ish attack, optional hold, then exponential decay (times in seconds)."""
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1) ** 1.5
    d = np.where(t < attack + hold, 1.0, np.exp(-(t - attack - hold) / decay))
    return a * d


def tone(seconds, f0, f1=None, partials=((1, 1.0),), curve=3.0):
    """Sine partials with an exponential pitch glide from f0 to f1."""
    t = t_of(seconds)
    f1 = f0 if f1 is None else f1
    k = (1 - np.exp(-curve * t / seconds)) / (1 - np.exp(-curve))  # fast-then-settling glide
    f = f0 + (f1 - f0) * k
    phase = 2 * np.pi * np.cumsum(f) / SR
    return sum(amp * np.sin(ratio * phase) for ratio, amp in partials)


def bell(seconds, f, decay, attack=0.004, bright=0.35):
    """Soft struck-bell: a fundamental plus quickly-fading upper partials."""
    t = t_of(seconds)
    out = np.sin(2 * np.pi * f * t) * np.exp(-t / decay)
    for ratio, amp, dk in ((2.0, bright, 0.45), (3.01, bright * 0.5, 0.3), (4.2, bright * 0.25, 0.2)):
        out += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t / (decay * dk))
    return out * env(len(t), attack, 10.0)


def click(seconds=0.006, level=0.25, cutoff=3000):
    """A tiny filtered noise transient that gives a cue its 'tap'."""
    n = int(SR * seconds)
    x = rng.standard_normal(n)
    a = np.exp(-2 * np.pi * cutoff / SR)  # one-pole low-pass
    y = np.zeros(n)
    for i in range(1, n):
        y[i] = (1 - a) * x[i] + a * y[i - 1]
    return level * y / (np.abs(y).max() or 1) * np.linspace(1, 0, n)


def place(total, *parts):
    """Mix (start_seconds, signal) parts into one buffer `total` seconds long."""
    out = np.zeros(int(SR * total))
    for start, sig in parts:
        i = int(SR * start)
        out[i:i + len(sig)] += sig[:len(out) - i]
    return out


def finish(x, peak_db, tail=0.03):
    """Normalize to peak_db dBFS, fade the tail, and add a few ms of lead-in silence."""
    x = x / np.abs(x).max() * 10 ** (peak_db / 20)
    fade = int(SR * tail)
    x[-fade:] *= np.linspace(1, 0, fade)
    return np.concatenate([np.zeros(int(SR * 0.004)), x])


def start():  # a quick, soft wooden "tock"
    body = tone(0.07, 452, 438, partials=((1, 1.0), (0.72, 0.4), (1.12, 0.3), (2.05, 0.2), (2.9, 0.18)))
    x = body * env(len(body), 0.005, 0.016)
    return finish(place(0.09, (0, x), (0, click(0.01, level=0.3, cutoff=5000))), -16.5)


def stop():  # a rounded "bloop" that swells in and falls in pitch
    body = tone(0.16, 460, 292, partials=((1, 1.0), (1.18, 0.35), (0.82, 0.3), (2.0, 0.05)), curve=5)
    return finish(body * env(len(body), 0.04, 0.035), -17)


def lock():  # two bubbly pops: hands-free is locked on
    pop1 = tone(0.05, 430, 170, partials=((1, 1.0), (1.6, 0.2)), curve=4)
    pop2 = tone(0.07, 290, 190, partials=((1, 1.0), (1.5, 0.2)), curve=3)
    return finish(place(0.12, (0, pop1 * env(len(pop1), 0.003, 0.012)),
                        (0.045, 0.8 * pop2 * env(len(pop2), 0.003, 0.018))), -21)


def cancel():  # the stop "bloop" lower and shorter: dismissed
    body = tone(0.12, 330, 210, partials=((1, 1.0), (1.2, 0.3), (2.0, 0.05)), curve=5)
    return finish(body * env(len(body), 0.012, 0.03), -19)


def paste():  # a light rising three-note chime
    notes = (277, 370, 466)
    parts = [(i * 0.085, 0.8 ** i * bell(0.4, f, 0.12, bright=0.2)) for i, f in enumerate(notes)]
    return finish(place(0.5, *parts), -20.5, tail=0.08)


def notification():  # a bright high tick settling downward
    parts = [(0, 1.4 * bell(0.2, 1400, 0.035, bright=0.1)), (0.035, 0.7 * bell(0.2, 680, 0.04)),
             (0.07, 0.55 * bell(0.25, 440, 0.045))]
    return finish(place(0.3, *parts), -17.5, tail=0.08)


def alert():  # a gentle two-step rise that swells in
    a = tone(0.35, 262) * env(int(SR * 0.35), 0.06, 0.05)
    b = tone(0.4, 392, partials=((1, 1.0), (2, 0.1))) * env(int(SR * 0.4), 0.05, 0.07)
    return finish(place(0.5, (0, a), (0.1, b)), -6, tail=0.08)


def error():  # low-high-low: something went wrong
    parts = [(0, bell(0.2, 440, 0.05, bright=0.1)), (0.06, 0.7 * bell(0.2, 660, 0.04, bright=0.1)),
             (0.12, 0.6 * bell(0.2, 440, 0.05, bright=0.1))]
    return finish(place(0.3, *parts), -14, tail=0.06)


def success():  # a sparkly high note resolving down a sixth
    parts = [(0, bell(0.4, 1320, 0.12, bright=0.25)), (0.14, 0.9 * bell(0.5, 784, 0.16, bright=0.25))]
    return finish(place(0.62, *parts), -17.5, tail=0.1)


def achievement():  # a big ringing bell with an octave shimmer
    x = bell(0.95, 415, 0.3, bright=0.6) + 0.5 * bell(0.95, 830, 0.22, bright=0.3)
    x += 0.25 * place(0.95, (0.08, bell(0.8, 1245, 0.18, bright=0.2)))
    return finish(x, -1, tail=0.15)


CUES = {f.__name__: f for f in (start, stop, lock, cancel, paste, notification, alert, error, success, achievement)}


def write(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, make in CUES.items():
        write(OUT / f"{name}.wav", make())
        print(f"wrote {name}.wav")


if __name__ == "__main__":
    main()
