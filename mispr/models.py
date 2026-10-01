"""Model storage and first-run download.

Models are fetched once from their official sources (Hugging Face repositories, or the
project's own GitHub release), verified against a pinned SHA-256, and kept in Application
Support. Nothing else is ever downloaded or uploaded.
"""

import hashlib
import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

MODELS_DIR = Path.home() / "Library" / "Application Support" / "Mispr_Flow" / "models"


@dataclass(frozen=True)
class ModelSpec:
    filename: str
    size: int
    sha256: str
    repo: str = "ggerganov/whisper.cpp"
    source: str = ""  # a full download URL, for models not on Hugging Face

    @property
    def path(self):
        return MODELS_DIR / self.filename

    @property
    def url(self):
        return self.source or f"https://huggingface.co/{self.repo}/resolve/main/{self.filename}"


# Best balance of accuracy, speed, and memory on Apple Silicon.
WHISPER_TURBO_Q5 = ModelSpec(
    "ggml-large-v3-turbo-q5_0.bin",
    574_041_195,
    "394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2",
)

DEFAULT_MODEL = WHISPER_TURBO_Q5

# Live meeting previews: ~0.15 s per phrase instead of ~1 s, so the words appear while
# they're being said. The final text still comes from the turbo model.
WHISPER_BASE_EN = ModelSpec(
    "ggml-base.en.bin",
    147_964_211,
    "a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002",
)

PREVIEW_MODEL = WHISPER_BASE_EN

# Voice fingerprints for telling meeting speakers apart (WeSpeaker ResNet34, trained on
# VoxCeleb; 256 numbers per voice, compared by cosine similarity). From sherpa-onnx's release.
WESPEAKER_RESNET34 = ModelSpec(
    "wespeaker_en_voxceleb_resnet34_LM.onnx",
    26_530_550,
    "e9848563da86f263117134dfd7ad63c92355b37de492b55e325400c9d9c39012",
    source="https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/"
           "wespeaker_en_voxceleb_resnet34_LM.onnx",
)

# Better at telling voices apart than ResNet34, and as fast (21 ms per second of audio):
# separation d' 4.09 vs 3.10 on AMI meetings, 0.66 vs 0.57 on a Zoom recording. NVIDIA TitaNet-large
# (CC BY 4.0), converted by sherpa-onnx.
TITANET_LARGE = ModelSpec(
    "nemo_en_titanet_large.onnx",
    101_405_493,
    "d51abcf31717ef28162f26acb9d44dd4127c3d44c9b8624f699f3425daca8e77",
    source="https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/"
           "nemo_en_titanet_large.onnx",
)

SPEAKER_MODEL = TITANET_LARGE

# Speech detection (Silero VAD): tells real speech from clicks, typing and noise, so a mouse
# click during a meeting never becomes "okay." or "Thank you." From sherpa-onnx's release.
SILERO_VAD = ModelSpec(
    "silero_vad.onnx",
    643_854,
    "9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6",
    source="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx",
)

VAD_MODEL = SILERO_VAD

# Text cleanup LLM. Chosen over Qwen2.5-1.5B/3B and Qwen3-4B-Instruct-2507 in a 27-case
# eval: zero invented words, zero lost key words, and the most conservative on ambiguous
# self-corrections (~550 ms on an M1 Pro). Gemma Terms of Use apply.
GEMMA3_4B_Q4 = ModelSpec(
    "gemma-3-4b-it-Q4_K_M.gguf",
    2_489_757_856,
    "882e8d2db44dc554fb0ea5077cb7e4bc49e7342a1f0da57901c0802ea21a0863",
    repo="ggml-org/gemma-3-4b-it-GGUF",
)

CLEANUP_MODEL = GEMMA3_4B_Q4


def is_installed(spec=DEFAULT_MODEL):
    p = spec.path
    return p.exists() and p.stat().st_size == spec.size


def ensure_model(spec=DEFAULT_MODEL, progress=None):
    """Download the model if missing. `progress(done_bytes, total_bytes)` is optional.

    Downloads to a .part file, verifies size and SHA-256, then renames into place, so a
    half-finished or corrupted download is never used.
    """
    if is_installed(spec):
        return spec.path
    if not spec.url.startswith("https://"):  # integrity also needs the SHA-256 below, but never plain HTTP
        raise ValueError(f"refusing a non-HTTPS model download: {spec.url}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    part = spec.path.with_suffix(spec.path.suffix + ".part")
    digest = hashlib.sha256()
    done = 0
    with urllib.request.urlopen(spec.url, timeout=30) as resp, open(part, "wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if progress:
                progress(done, spec.size)
    if done != spec.size or digest.hexdigest() != spec.sha256:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"model download failed verification ({spec.filename})")
    os.replace(part, spec.path)
    return spec.path


def progress_printer(out=None):
    """A download progress callback that prints every 5%: "40% (229 / 574 MB)"."""
    last = [-1]

    def report(done, total):
        pct = done * 100 // total
        if pct != last[0] and pct % 5 == 0:
            last[0] = pct
            print(f"{pct}% ({done / 1e6:.0f} / {total / 1e6:.0f} MB)", file=out or sys.stderr, flush=True)

    return report


def cli(args, ensure=None):
    """python -m mispr.models [whisper] [cleanup]: download and verify models."""
    ensure = ensure or ensure_model
    names = {"whisper": DEFAULT_MODEL, "cleanup": CLEANUP_MODEL, "preview": PREVIEW_MODEL, "speakers": SPEAKER_MODEL,
             "vad": VAD_MODEL}
    report = progress_printer()
    return [ensure(names[name], progress=report) for name in args or ["whisper", "cleanup"]]


if __name__ == "__main__":
    for path in cli(sys.argv[1:]):
        print(path)
