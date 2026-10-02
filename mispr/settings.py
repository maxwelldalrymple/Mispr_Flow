"""User settings, persisted as JSON in Application Support. The settings UI will edit these."""

import json
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

SETTINGS_PATH = Path.home() / "Library" / "Application Support" / "Mispr_Flow" / "settings.json"


@dataclass
class Settings:
    # Incognito: recordings are wiped from memory right after use and never written to disk.
    # Off by default so history and usage stats can be tracked.
    incognito: bool = False
    # Auto-Enter: press Return after the text lands in a text box (send chat messages hands-free).
    # Off by default; only the button in the app's top bar turns it on.
    auto_enter: bool = False
    # LLM cleanup of transcripts (fillers, self-corrections, punctuation); off = raw Whisper text.
    cleanup: bool = True
    # Sound cues (start, stop, paste...).
    sounds: bool = True
    auto_update: bool = True  # the app checks GitHub for a new version about 5 times a day
    # Long dictations typed in piece by piece while they're processed (off: all at once at the end).
    live_long_dictations: bool = False
    # Your own voice commands: [{"say": "sign off", "type": "Best, Alex"}, {"say": "next song", "keys": "cmd right"}].
    custom_commands: list = field(default_factory=list)
    # The dictation key; see hotkey.normalize_trigger. Default: fn.
    hotkey: dict = field(default_factory=lambda: {"kind": "fn", "keycode": 63, "label": "fn"})
    # The app switcher key (hold it, say an app, let go): same format as `hotkey`; None = off.
    switch_hotkey: dict = None
    # The Auto-Enter key (press to turn Auto-Enter on/off): a combo like `switch_hotkey`; None = off.
    auto_enter_hotkey: dict = field(default_factory=lambda: {"kind": "combo", "mods": ["control", "option"],
                                                             "keycode": 36, "label": "⌃⌥↩"})
    # Spoken nicknames for apps: {"c": "Google Chrome", "scooby snacks": "Google Chrome"}.
    app_nicknames: dict = field(default_factory=dict)
    # Set once the user finishes the first-run setup window.
    onboarded: bool = False
    # The setup step reached, so setup resumes there if macOS quits and reopens the app
    # (it does after some permissions, like Screen & System Audio).
    setup_step: int = 0


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


def save_nickname(nick, app):
    """Add one nickname to settings.json, keeping everything else the app may have changed."""
    current = load()
    current.app_nicknames = {**current.app_nicknames, nick: app}
    save(current)
    return current
