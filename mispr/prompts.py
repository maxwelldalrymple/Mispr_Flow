"""Your cleanup prompts (the app's Prompts page): instructions, extra rules, examples, and
whether the no-invented-words guard applies. Saved as prompts.json next to settings.json;
anything left out falls back to the built-in defaults in cleanup.py.
"""

import json
import sys
from dataclasses import asdict, dataclass, field

from . import cleanup
from .settings import SETTINGS_PATH

PROMPTS_PATH = SETTINGS_PATH.parent / "prompts.json"
SAID, WROTE = "Said:", "Wrote:"


@dataclass
class Prompts:
    system: str = cleanup.SYSTEM_PROMPT
    extra: str = ""  # your own rules, added after the instructions
    examples: list = field(default_factory=lambda: [list(pair) for pair in cleanup.EXAMPLES])
    guard: bool = True  # reject output containing words you didn't say

    def full_system(self):
        rules = self.extra.strip()
        return self.system.strip() + (f"\n\nAlso follow these rules from the user:\n{rules}" if rules else "")


def load(path=None):
    path = path or PROMPTS_PATH
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return Prompts()
    except (OSError, ValueError) as e:
        print(f"mispr: ignoring unreadable prompts ({e})", file=sys.stderr)
        return Prompts()
    defaults = Prompts()
    examples = data.get("examples", defaults.examples)
    if not (isinstance(examples, list) and all(isinstance(p, list) and len(p) == 2 for p in examples)):
        examples = defaults.examples
    return Prompts(
        system=data.get("system") or defaults.system,
        extra=data.get("extra", ""),
        examples=examples,
        guard=bool(data.get("guard", True)),
    )


def save(prompts, path=None):
    path = path or PROMPTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(prompts), indent=2))


def format_examples(pairs):
    """Examples as editable text: 'Said: …' / 'Wrote: …' pairs separated by blank lines."""
    return "\n\n".join(f"{SAID} {raw}\n{WROTE} {clean}" for raw, clean in pairs)


def parse_examples(text):
    """The inverse of format_examples. Incomplete pairs are skipped."""
    pairs, said = [], None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(SAID):
            said = line[len(SAID):].strip()
        elif line.startswith(WROTE) and said is not None:
            pairs.append([said, line[len(WROTE):].strip()])
            said = None
    return pairs


def defaults_payload():
    """The built-in prompts, for the app's Reset buttons."""
    d = Prompts()
    return {"system": d.system, "examples": format_examples(d.examples)}
