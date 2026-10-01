"""Dictating into a terminal: spoken syntax becomes shell syntax ("ls flag a" -> "ls -a").

The cleanup model gets terminal instructions; its output is accepted only if every word in it
was said, so it can never add a command or flag. Otherwise (or with cleanup off) a plain
word-for-symbol converter is used.
"""

import re

TERMINAL_APPS = {
    "com.apple.Terminal", "com.googlecode.iterm2", "dev.warp.Warp-Stable", "dev.warp.Warp", "com.mitchellh.ghostty",
    "net.kovidgoyal.kitty", "org.alacritty", "io.alacritty", "com.github.wez.wezterm", "co.zeit.hyper",
    "org.tabby", "com.raphaelamorim.rio",
}

PROMPT = """You turn dictated speech into terminal input for a macOS shell (zsh/bash).
Write exactly what was dictated, as it would be typed:
- Spoken symbols become characters: "dash"/"flag"/"minus" -> "-", "dash dash"/"double dash" -> "--", "pipe" -> "|",
  "slash" -> "/", "tilde" -> "~", "dot" -> ".", "star" -> "*", "underscore" -> "_", "equals" -> "=", "colon" -> ":",
  "and and" -> "&&", "greater than" -> ">", "less than" -> "<", "quote" ... "quote" -> "...", "dollar" -> "$".
- A letter after a dash is a flag letter: "flag a" -> "-a", "dash l a" -> "-la".
- Commands, paths and options are lowercase, with no spaces inside them. Numbers as digits.
- Never add a command, flag, argument or word that was not said. Never explain. No code fences.
- No trailing period. Words inside quotes stay as said (like a commit message)."""

EXAMPLES = [
    ("ls flag a", "ls -a"),
    ("LS dash L A.", "ls -la"),
    ("cd tilde slash documents slash projects", "cd ~/documents/projects"),
    ("git commit dash m quote fix the login bug quote", 'git commit -m "fix the login bug"'),
    ("grep dash r to do dot pipe head", "grep -r todo . | head"),
    ("python three dash m pytest dash dash verbose", "python3 -m pytest --verbose"),
    ("npm run dev and and open localhost colon three thousand", "npm run dev && open localhost:3000"),
]

# The plain converter: longest phrases first.
_PHRASES = [
    (r"\bdouble dash\b|\bdash dash\b", "--"), (r"\band and\b", "&&"), (r"\bgreater than\b", ">"),
    (r"\bless than\b", "<"), (r"\b(?:dash|flag|minus)\b", "-"), (r"\bpipe\b", "|"), (r"\bslash\b", "/"),
    (r"\btilde\b", "~"), (r"\bdot\b", "."), (r"\bstar\b", "*"), (r"\bunderscore\b", "_"), (r"\bequals\b", "="),
    (r"\bcolon\b", ":"), (r"\bdollar\b", "$"),
]
_JOIN = re.compile(r"\s*([/:=_])\s*")  # these sit tight against both neighbours
_NUMBERS = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
            "eight": "8", "nine": "9", "ten": "10"}


def is_terminal(info):
    """True when the app the dictation started in (a context.frontmost() result) is a terminal."""
    return bool(info) and info.get("bundle_id") in TERMINAL_APPS


def spoken_to_shell(raw):
    """Spoken syntax to shell syntax, word for word: "ls flag a" -> "ls -a"."""
    text = raw.strip().rstrip(".!?").lower()
    text = re.sub(r"\bquote\b\s*(.*?)\s*\bquote\b", lambda m: f'"{m[1]}"', text)
    for pattern, symbol in _PHRASES:
        text = re.sub(pattern, f" {symbol} ", text)
    text = re.sub(r"\b(" + "|".join(_NUMBERS) + r")\b", lambda m: _NUMBERS[m[1]], text)
    text = re.sub(r"\b(\d+)\s+thousand\b", lambda m: str(int(m[1]) * 1000), text)
    text = re.sub(r"\b(\d+)\s+hundred\b", lambda m: str(int(m[1]) * 100), text)
    text = re.sub(r"(--?)\s+(\w)", r"\1\2", text)  # "- a" -> "-a", "-- verbose" -> "--verbose"
    text = re.sub(r"(-\w)\s+(?=\w\b)(\w)\b", r"\1\2", text)  # "-l a" -> "-la"
    text = re.sub(r"(?<=\w)\s+(\d)\b", r"\1", text)  # "python 3" -> "python3"
    text = _JOIN.sub(r"\1", text)
    text = re.sub(r"~\s+", "~", text)  # "~ /docs" -> "~/docs", but "cd ~" keeps its space
    text = re.sub(r"(?<=\w)\s*\.\s*(?=[a-z0-9])", ".", text)  # "file . txt" -> "file.txt"; "todo ." stays
    text = re.sub(r"\s*\|\s*", " | ", text)
    return re.sub(r"\s+", " ", text).strip()


def faithful(raw, command):
    """Every word in `command` (2+ letters) was said, alone or as said letters run together
    ("l a" -> "-la"): the model can never add a command ("rm") or flag ("rf")."""
    said = set(re.findall(r"[a-z]+", raw.lower()))
    joined = re.sub(r"[^a-z]", "", raw.lower())
    for word in re.findall(r"[a-z]{2,}", command.lower()):
        if word not in said and word not in joined:
            return False
    return True


def clean(raw, cleaner=None):
    """(command, info) for terminal input: the model with terminal instructions when it stays
    faithful, else the plain converter."""
    if cleaner is not None:
        text, info = cleaner.clean(raw, PROMPT, EXAMPLES, guard=False)
        text = re.sub(r"(?<=\w)\.$", "", (text or "").replace("`", "").strip())  # "ls ." keeps its dot
        if info.get("applied") and text and faithful(raw, text):
            info["terminal"] = True
            return text, info
    else:
        info = {"applied": False, "rejected": None, "ms": 0}
    info = dict(info, terminal=True, applied=False,
                rejected=info.get("rejected") or "terminal: used the plain converter")
    return spoken_to_shell(raw), info
