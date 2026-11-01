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


def test_tab_route_types_into_the_start_tab_in_the_background(monkeypatch):
    sent = []
    monkeypatch.setattr(target, "_osascript", lambda script, timeout=3: sent.append(script) or (0, "ok"))
    spot = Spot(1, "Google Chrome", bundle_id="com.google.Chrome", tab=("101", "202"))
    assert target.insert_in_tab(spot, 'Say "hi"', enter=True) == "ok"
    assert 'tab id 202 of window id 101' in sent[0] and "javascript" in sent[0]
    assert "activate" not in sent[0]  # never brings the window forward
    assert 'Say \\\\\\"hi' in sent[0]  # the words' quotes, escaped for JSON, then again for AppleScript


def test_tab_route_reports_the_setting_being_off(monkeypatch):
    monkeypatch.setattr(target, "_osascript", lambda s, timeout=3: (1, "Executing JavaScript through AppleScript is turned off."))
    assert target.insert_in_tab(Spot(1, "Chrome", bundle_id="com.google.Chrome", tab=("1", "2")), "x") == "off"


def test_not_a_browser_tab():
    assert target.insert_in_tab(Spot(1, "Slack", bundle_id="com.tinyspeck.slackmacgap"), "x") == "not a browser tab"


def test_browser_tab_is_noted_only_for_scriptable_browsers(monkeypatch):
    monkeypatch.setattr(target, "_osascript", lambda s, timeout=3: (0, "101, 202"))
    assert target.browser_tab("com.google.Chrome") == ("101", "202")
    assert target.browser_tab("com.apple.Safari") is None


def test_goes_to_start_unless_you_picked_a_new_box():
    start = Spot(10, "Notes", window="w1", element="my box")
    assert target.goes_to_start(start, now=Spot(11, "Chrome", window="w9", element=None))  # other window, no box
    assert not target.goes_to_start(start, now=Spot(11, "Chrome", window="w9", element="chrome box"))  # a new box wins
    assert not target.goes_to_start(start, now=Spot(10, "Notes", window="w1", element="my box"))  # still there
    assert not target.goes_to_start(start, now=Spot(10, "Notes", window="w1", element=None))  # same window: refocus path
    assert not target.goes_to_start(start, now=Spot(10, "Notes", window="w1", element="another box"))  # new box, same window
    assert not target.goes_to_start(None, now=Spot(1, "x"))
