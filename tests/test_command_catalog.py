"""The Voice Commands page (macos/.../CommandsView.swift) is accurate: every phrase on it is
parsed by the real engine into the kind of command the page says."""

import re
from pathlib import Path

import pytest

from mispr import apps

CATALOG = Path(__file__).resolve().parent.parent / "macos" / "Sources" / "MisprFlow" / "Views" / "CommandsView.swift"
PHRASES = re.findall(r'Say\(words: "([^"]+)", does: "[^"]*", kind: "(\w+)"\)', CATALOG.read_text())


def test_the_page_lists_plenty():
    assert len(PHRASES) >= 50


@pytest.mark.parametrize("words, kind", PHRASES)
def test_every_phrase_does_what_the_page_says(words, kind):
    command = apps.parse(words)
    assert command is not None and command[0] == kind, f"“{words}” parses as {command}"
