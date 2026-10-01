"""Dictating into a terminal: spoken syntax becomes shell syntax, and nothing is ever added."""

import pytest

from mispr import terminal


@pytest.mark.parametrize("said,typed", [
    ("ls flag a", "ls -a"), ("LS dash L A.", "ls -la"), ("cd tilde slash documents slash projects", "cd ~/documents/projects"),
    ("cd tilde", "cd ~"), ("git commit dash m quote fix the login bug quote", 'git commit -m "fix the login bug"'),
    ("grep dash r todo dot pipe head", "grep -r todo . | head"), ("cat readme dot md", "cat readme.md"),
    ("python three dash m pytest dash dash verbose", "python3 -m pytest --verbose"),
    ("npm run dev and and open localhost colon three thousand", "npm run dev && open localhost:3000"),
    ("git status", "git status"),
])
def test_plain_converter(said, typed):
    assert terminal.spoken_to_shell(said) == typed


def test_the_model_can_never_add_a_command_or_flag():
    assert terminal.faithful("ls flag a", "ls -a") and terminal.faithful("LS dash L A", "ls -la")
    assert not terminal.faithful("ls flag a", "rm -rf /")
    assert not terminal.faithful("git status", "git status && rm x")


class Cleaner:
    def __init__(self, reply, applied=True):
        self.reply, self.applied, self.calls = reply, applied, []

    def clean(self, raw, system, examples, guard):
        self.calls.append((system, guard))
        return self.reply, {"applied": self.applied, "rejected": None, "ms": 5}


def test_uses_the_model_with_terminal_instructions():
    c = Cleaner("`ls -la`.")
    text, info = terminal.clean("ls dash l a", c)
    assert text == "ls -la" and info["terminal"] and c.calls == [(terminal.PROMPT, False)]


def test_unfaithful_or_failed_model_falls_back_to_the_converter():
    assert terminal.clean("ls flag a", Cleaner("rm -rf /"))[0] == "ls -a"
    assert terminal.clean("ls flag a", Cleaner("", applied=False))[0] == "ls -a"
    text, info = terminal.clean("ls flag a", None)  # cleanup off
    assert text == "ls -a" and info["terminal"] and not info["applied"]


def test_which_apps_are_terminals():
    assert terminal.is_terminal({"bundle_id": "com.apple.Terminal"}) and terminal.is_terminal({"bundle_id": "com.googlecode.iterm2"})
    assert not terminal.is_terminal({"bundle_id": "com.google.Chrome"}) and not terminal.is_terminal(None)
