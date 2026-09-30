"""User settings, persisted as JSON in Application Support. The settings UI will edit these."""

import json
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

SETTINGS_PATH = Path.home() / "Library" / "Application Support" / "WhisprClone" / "settings.json"


@dataclass
class Settings:
    # Incognito: recordings are wiped from memory right after use and never written to disk.
    # Off by default so history and usage stats can be tracked.
    incognito: bool = False


def load():
    try:
        data = json.loads(SETTINGS_PATH.read_text())
    except FileNotFoundError:
        return Settings()
    except (OSError, ValueError) as e:
        print(f"whispr: ignoring unreadable settings ({e})", file=sys.stderr)
        return Settings()
    known = {f.name for f in fields(Settings)}
    return Settings(**{k: v for k, v in data.items() if k in known})


def save(settings):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(asdict(settings), indent=2))
