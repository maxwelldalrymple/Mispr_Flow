"""The ~1,000 most visited websites (assets/sites.txt), so a misheard site name is assumed to be
the real one: "you two" -> youtube.com, "chat gbt" -> chatgpt.com, "linkdin" -> linkedin.com.

A name is matched exactly first, then by sound (the more popular site wins), then by spelling,
with a strict cutoff so ordinary words aren't turned into websites.
"""

import difflib
import re
from functools import lru_cache
from pathlib import Path

SITES_FILE = Path(__file__).resolve().parent / "assets" / "sites.txt"
GUESS_MIN = 0.8  # spelling closeness needed to assume a popular site (open tabs use apps.SITE_GUESS_MIN)
SOUND_MIN = 0.7  # ...or this close, when it also sounds the same ("redit", "net flicks")
_TLDS = r"com|org|net|io|ai|co|app|so|tv|gg|dev|me|us|uk|ca|edu"


def _key(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


@lru_cache(maxsize=1)
def known():
    """[(domain, keys)] in popularity order. Keys are how the site is said: "youtube" for
    youtube.com; "googledocs" and "docsgoogle" for docs.google.com."""
    out = []
    for line in SITES_FILE.read_text().splitlines():
        domain = line.strip().lower()
        if not domain or domain.startswith("#") or re.match(r"^[a-z]{2}\.[^.]+\.[a-z]+$", domain) and not domain.startswith(("x.", "t.")):
            continue  # country copies (de.linkedin.com) say nothing new
        labels = [p for p in domain.split(".") if p not in ("www", "m")]
        labels = labels[:-1] if len(labels) > 1 else labels  # drop the TLD
        if len(labels) > 1 and labels[-1] in ("co", "com"):  # bbc.co.uk
            labels = labels[:-1]
        keys = {_key("".join(labels)), _key("".join(reversed(labels))), _key(labels[-1] if len(labels) == 1 else "".join(labels))}
        out.append((domain, {k for k in keys if k}))
    return out


def scored_guess(spoken):
    """(domain, confidence 0-1) for the popular site `spoken` most likely means, or (None, 0).
    Exact name 1.0; otherwise spelling closeness, counted only if it's at least GUESS_MIN, or
    at least SOUND_MIN when the two also sound alike (Soundex)."""
    from .apps import sounds_like
    want = _key(spoken)
    if len(want) < 2:
        return None, 0.0
    sites = known()
    for domain, keys in sites:
        if want in keys:
            return domain, 1.0
    sound = sounds_like(want)
    best, best_score = None, 0.0
    for domain, keys in sites:  # popularity order: a tie keeps the more popular site
        for k in keys:
            score = difflib.SequenceMatcher(None, want, k).ratio()
            alike = sound is not None and sounds_like(k) == sound
            if (score >= GUESS_MIN or (alike and score >= SOUND_MIN)) and score > best_score:
                best, best_score = domain, score
    return best, best_score


def guess(spoken):
    """The popular site `spoken` most likely means (its domain), or None."""
    return scored_guess(spoken)[0]


_SPOKEN_ADDRESS = re.compile(rf"\b((?:[a-z0-9]+[ -]){{0,2}}[a-z0-9]+)\s*(?:\bdot\b\s*|\.)({_TLDS})\b", re.I)


def fix_addresses(text):
    """Web addresses said aloud, made right: "chat gbt dot com" -> "chatgpt.com",
    "you tube.com" -> "youtube.com". Only when the name is close to a popular site; anything
    else is left as it was."""
    def repl(m):
        words = m[1].split()
        best, best_score, best_n = None, 0.0, 0
        for n in range(1, len(words) + 1):  # the tail of words that best names a site with this ending
            domain, score = scored_guess(" ".join(words[-n:]))
            if domain and domain.endswith("." + m[2].lower()) and score > best_score:
                best, best_score, best_n = domain, score, n
        return " ".join(words[:-best_n] + [best]) if best else m[0]
    return _SPOKEN_ADDRESS.sub(repl, text)
