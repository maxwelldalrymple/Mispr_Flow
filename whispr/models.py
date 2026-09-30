"""Model storage and first-run download.

Models are fetched once from their official Hugging Face repositories, verified
against the published SHA-256, and kept in Application Support.
"""

import hashlib
import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

MODELS_DIR = Path.home() / "Library" / "Application Support" / "WhisprClone" / "models"


@dataclass(frozen=True)
class ModelSpec:
    filename: str
    size: int
    sha256: str
    repo: str = "ggerganov/whisper.cpp"

    @property
    def path(self):
        return MODELS_DIR / self.filename

    @property
    def url(self):
        return f"https://huggingface.co/{self.repo}/resolve/main/{self.filename}"


# Best balance of accuracy, speed, and memory on Apple Silicon.
WHISPER_TURBO_Q5 = ModelSpec(
    "ggml-large-v3-turbo-q5_0.bin",
    574_041_195,
    "394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2",
)

DEFAULT_MODEL = WHISPER_TURBO_Q5

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


if __name__ == "__main__":
    last = [-1]

    def report(done, total):
        pct = done * 100 // total
        if pct != last[0] and pct % 5 == 0:
            last[0] = pct
            print(f"{pct}% ({done / 1e6:.0f} / {total / 1e6:.0f} MB)", file=sys.stderr, flush=True)

    names = {"whisper": DEFAULT_MODEL, "cleanup": CLEANUP_MODEL}
    for name in sys.argv[1:] or ["whisper", "cleanup"]:
        print(ensure_model(names[name], progress=report))
