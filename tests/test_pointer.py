"""Clicking by voice (mispr/pointer.py) and the numbers overlay geometry (mispr/overlay.py)."""

import pytest

from mispr import overlay, pointer

T = pointer.Target
FOUND = [T("Opus 4.6", "AXButton", (10, 10, 50, 20)), T("Fable 5.1", "AXButton", (10, 40, 50, 20)),
         T("Preferences", "AXMenuItem", (10, 70, 50, 20)), T("Sign in", "AXLink", (10, 130, 50, 20)),
         T("Sign in", "AXStaticText", (15, 133, 30, 14)), T("Walk through setup", "AXButton", (10, 190, 50, 20)),
         T("New Tab", "AXButton", (300, 5, 20, 20)), T("New install: check", "AXStaticText", (10, 260, 90, 16)),
         T("", "AXTextField", (100, 300, 200, 24)), T("Search", "AXSearchField", (100, 330, 200, 24))]


def names(found):
    return [t.name for t in found]


@pytest.mark.parametrize("said, expected", [
    ("sign in", ["Sign in"]),  # the link; its text inside is the same click
    ("the Sign in link", ["Sign in"]),
    ("new tab", ["New Tab"]),  # the full phrase first: not "new" (which would also match "New install")
    ("opus", ["Opus 4.6"]), ("pref", ["Preferences"]), ("fable five", ["Fable 5.1"]),
    ("thru setup", ["Walk through setup"]), ("sign inn", ["Sign in"]), ("zebra", []),
])
def test_match(said, expected):
    assert names(pointer.match(said, FOUND)) == expected


def test_search_box_finds_fields():
    assert {t.role for t in pointer.match("the search box", FOUND)} <= {"AXSearchField", "AXTextField"}


def test_closeness():
    assert pointer.closeness("pref", "preferences") == pytest.approx(0.85)
    assert pointer.closeness("five", "5 1") > pointer.closeness("six", "5 1")
    assert pointer.closeness("zebra", "sign in") < pointer.CLOSE_MIN


def test_numberable_skips_plain_text_and_dupes():
    shown = pointer.numberable(FOUND)
    assert all(t.role != "AXStaticText" or not t.name for t in shown)
    assert len([t for t in shown if t.name == "Sign in"]) == 1


def test_click_posts_move_down_up():
    import Quartz
    events = []
    pointer.click_at((50, 60), post=events.append, pause=lambda s: None)
    kinds = [Quartz.CGEventGetType(e) for e in events]
    assert kinds == [Quartz.kCGEventMouseMoved, Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp]
    events.clear()
    pointer.click_at((5, 5), "right", post=events.append, pause=lambda s: None)
    assert Quartz.CGEventGetType(events[1]) == Quartz.kCGEventRightMouseDown
    events.clear()
    pointer.click_at((5, 5), count=2, post=events.append, pause=lambda s: None)
    assert Quartz.CGEventGetIntegerValueField(events[-1], Quartz.kCGMouseEventClickState) == 2
    events.clear()
    pointer.click_at((5, 5), move_only=True, post=events.append, pause=lambda s: None)
    assert len(events) == 1


def test_drag_moves_in_steps():
    import Quartz
    events = []
    pointer.drag((0, 0), (100, 0), steps=4, post=events.append, pause=lambda s: None)
    kinds = [Quartz.CGEventGetType(e) for e in events]
    assert kinds[1] == Quartz.kCGEventLeftMouseDown and kinds[-1] == Quartz.kCGEventLeftMouseUp
    assert kinds.count(Quartz.kCGEventLeftMouseDragged) == 4


def test_badges_sit_on_the_targets_top_left_corner():
    (x, y, w, h), = overlay.badge_rects([(100, 50, 80, 30)], screen_height=1000)
    assert x == 101 and y == 1000 - 50 - h - 1
    (cx, cy, cw, ch), = overlay.centered_badges([(0, 0, 300, 300)], screen_height=1000)
    assert cx + cw / 2 == pytest.approx(150) and cy + ch / 2 == pytest.approx(850)
