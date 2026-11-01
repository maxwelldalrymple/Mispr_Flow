"""Where a dictation goes (mispr/target.py): the box you started in, even after switching away."""

from mispr import target
from mispr.target import Spot


def test_still_there_when_nothing_changed():
    start = Spot(10, "Slack", window="w1", element="box")
    assert target.still_there(start, now=Spot(10, "Slack", window="w1", element="box"))
    assert target.still_there(start, now=Spot(10, "Slack", window="w1", element=None))  # focus left the box: same window


def test_switched_app_window_or_box():
    start = Spot(10, "Slack", window="w1", element="box")
    assert not target.still_there(start, now=Spot(11, "Chrome", window="w9"))
    assert not target.still_there(start, now=Spot(10, "Slack", window="w2", element="box"))
    assert not target.still_there(start, now=Spot(10, "Slack", window="w1", element="other box"))


def test_unknown_means_behave_as_before():
    assert target.still_there(None, now=Spot(1, "x"))
    assert target.still_there(Spot(1, "x"), now=None)


def test_box_for_prefers_the_box_with_the_cursor(monkeypatch):
    assert target.box_for(Spot(1, "x", element="box")) == "box"
    found = target.pointer.Input("main", "AXTextArea", (0, 0, 300, 30), True, "")
    monkeypatch.setattr(target.pointer, "text_inputs", lambda pid: [found])
    assert target.box_for(Spot(1, "x")) == "main"
    monkeypatch.setattr(target.pointer, "text_inputs", lambda pid: [])
    assert target.box_for(Spot(1, "x")) is None


def test_landed_needs_the_words_really_there(monkeypatch):
    monkeypatch.setattr(target.pointer, "_ax", lambda el, attr: el)
    assert target._landed("Hi there. Hello.", "Hi there.", "Hello.")
    assert not target._landed("Hi there.", "Hi there.", "Hello.")  # accepted the call, changed nothing
    assert not target._landed(None, "", "Hello.")
