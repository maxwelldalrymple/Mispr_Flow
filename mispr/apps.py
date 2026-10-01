"""Voice app switcher: hold the switch key, say an app (or a nickname for one), let go, and
that app comes to the front. "Set nickname C to Chrome" teaches a nickname.

Everything here is local: apps are found on disk and in the running-apps list, never online.
"""

import difflib
import os
import re
from pathlib import Path

APP_DIRS = (
    "/Applications", "/Applications/Utilities", "/System/Applications", "/System/Applications/Utilities",
    str(Path.home() / "Applications"), "/System/Library/CoreServices/Applications",
)
FUZZY_CUTOFF = 0.75  # how close a misheard name must be (difflib ratio)

# "set nickname scooby snacks to chrome", "nickname C for Chrome", "set the nickname for Chrome to C".
_NICKNAME_PATTERNS = (
    re.compile(r"^(?:please\s+)?(?:set|make|add|create)?\s*(?:a|the)?\s*nick\s*name\s+for\s+(?P<app>.+?)\s+(?:to|as|is)\s+(?P<nick>.+)$"),
    re.compile(r"^(?:please\s+)?(?:set|make|add|create)?\s*(?:a|the)?\s*nick\s*name\s+(?P<nick>.+?)\s+(?:to|for|as|is|means)\s+(?P<app>.+)$"),
)
# Spoken filler around an app name: "open chrome", "switch to the terminal", "go to Slack please".
_FILLER = re.compile(r"^(?:(?:please|ok|okay|hey|um|uh)\s+)*(?:(?:open|switch|go|bring|show|launch|focus)(?:\s+(?:to|up|me))?\s+)?(?:the\s+)?|\s+(?:app|please)$")


def normalize(text):
    """Lowercase words only: "Google Chrome." -> "google chrome"."""
    text = re.sub(r"[^\w\s]", " ", text.lower().replace("’", "").replace("'", ""))
    return " ".join(text.split())


def parse(text):
    """What was said: ("nickname", nick, app), ("switch", name), or None for nothing usable."""
    said = normalize(text)
    if not said:
        return None
    for pattern in _NICKNAME_PATTERNS:
        m = pattern.match(said)
        if m:
            return ("nickname", m["nick"].strip(), m["app"].strip())
    name = _FILLER.sub("", said).strip()
    return ("switch", name) if name else None


def find_apps(dirs=APP_DIRS):
    """{display name: path} for every .app in the usual folders (one level of subfolders)."""
    found = {}
    for top in dirs:
        try:
            entries = list(os.scandir(top))
        except OSError:
            continue
        for entry in entries:
            if entry.name.endswith(".app"):
                found.setdefault(entry.name[:-4], entry.path)
            elif entry.is_dir() and not entry.name.startswith("."):
                try:
                    for sub in os.scandir(entry.path):
                        if sub.name.endswith(".app"):
                            found.setdefault(sub.name[:-4], sub.path)
                except OSError:
                    pass
    return found


def running_apps():
    """{name: path} of apps with a window in the Dock (not background helpers)."""
    from AppKit import NSApplicationActivationPolicyRegular, NSWorkspace

    out = {}
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        if app.activationPolicy() == NSApplicationActivationPolicyRegular and app.bundleURL() is not None:
            out[str(app.localizedName())] = str(app.bundleURL().path())
    return out


def match(name, apps, nicknames=None, running=()):
    """The app `name` refers to: a nickname, an exact name, a word of a name ("chrome" ->
    "Google Chrome"), a prefix, or a close-sounding name. Running apps win ties. None if unsure."""
    said = normalize(name)
    if not said:
        return None
    for nick, app in (nicknames or {}).items():
        if normalize(nick) == said:
            return app
    by_norm = {}
    for app in sorted(apps, key=lambda a: (a not in running, len(a))):
        by_norm.setdefault(normalize(app), app)
    if said in by_norm:
        return by_norm[said]
    squashed = said.replace(" ", "")
    for norm, app in by_norm.items():  # "face time" -> FaceTime, "vs code" -> "VS Code"
        if norm.replace(" ", "") == squashed:
            return app
    if len(said) >= 3:
        for norm, app in by_norm.items():  # "photo" -> Photos (not Photo Booth)
            if norm.startswith(said) and len(norm) - len(said) <= 2:
                return app
        for norm, app in by_norm.items():  # "chrome" -> Google Chrome, "code" -> Visual Studio Code
            if said in norm.split() or (" " in said and said in norm):
                return app
        for norm, app in by_norm.items():  # "photo" -> Photos, "term" -> Terminal
            if norm.startswith(said):
                return app
    close = difflib.get_close_matches(said, list(by_norm), n=1, cutoff=FUZZY_CUTOFF)
    return by_norm[close[0]] if close else None


def bring_to_front(path, workspace=None):
    """Activate the app at `path`, launching it if it isn't running. True on success."""
    from AppKit import NSWorkspace, NSWorkspaceOpenConfiguration
    from Foundation import NSURL

    config = NSWorkspaceOpenConfiguration.configuration()
    config.setActivates_(True)
    (workspace or NSWorkspace.sharedWorkspace()).openApplicationAtURL_configuration_completionHandler_(
        NSURL.fileURLWithPath_(path), config, None)
    return True
