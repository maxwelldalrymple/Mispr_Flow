"""User settings, persisted as JSON in Application Support. The settings UI will edit these."""

import json
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

SETTINGS_PATH = Path.home() / "Library" / "Application Support" / "Mispr_Flow" / "settings.json"


@dataclass
class Settings:
    # Incognito: recordings are wiped from memory right after use and never written to disk.
    # Off by default so history and usage stats can be tracked.
    incognito: bool = False
    # LLM cleanup of transcripts (fillers, self-corrections, punctuation); off = raw Whisper text.
    cleanup: bool = True


def load():
    try:
        data = json.loads(SETTINGS_PATH.read_text())
    except FileNotFoundError:
        return Settings()
    except (OSError, ValueError) as e:
        print(f"mispr: ignoring unreadable settings ({e})", file=sys.stderr)
        return Settings()
    known = {f.name for f in fields(Settings)}
    return Settings(**{k: v for k, v in data.items() if k in known})


def save(settings):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(asdict(settings), indent=2))
