"""More of the Mac by voice (mispr/control.py): parsing, keys, windows, switches, the web,
Shortcuts and your own commands. System tools are replaced by recorders: nothing on this Mac
is changed by these tests."""

import pytest

from mispr import apps, control


def parse(text):
    return apps.parse(text)


@pytest.mark.parametrize("said, expected", [
    ("Press enter.", ("keys", [("return", "")], 1)),
    ("press command shift t", ("keys", [("t", "cmd shift")], 1)),
    ("hit escape", ("keys", [("escape", "")], 1)),
    ("press tab three times", ("keys", [("tab", "")], 3)),
    ("down three", ("keys", [("down", "")], 3)),
    ("select all", ("keys", [("a", "cmd")], 1)),
    ("Save.", ("keys", [("s", "cmd")], 1)),
    ("new paragraph", ("keys", [("return", "shift")], 2)),
    ("scratch that", ("that", "delete")),
    ("capitalize that", ("that", "capitalize")),
    ("left half", ("snap", "left")),
    ("right side of the screen", ("snap", "right")),
    ("top left corner", ("snap", "top left")),
    ("move to top left", ("snap", "top left")),
    ("move to the other screen", ("other_screen",)),
    ("desktop 2", ("desktop", 2)),
    ("next desktop", ("desktop", "next")),
    ("show desktop", ("mission", "desktop")),
    ("control center", ("mission", "control")),
    ("dark mode on", ("dark_mode", True)),
    ("light mode", ("dark_mode", False)),
    ("turn off wi-fi", ("wifi", False)),
    ("dimmer", ("brightness", "down")),
    ("use AirPods", ("output", "airpods")),
    ("google best pizza near me", ("search", "google", "best pizza near me")),
    ("search youtube for lofi beats", ("search", "youtube", "lofi beats")),
    ("Go to apple.com.", ("go_to", "apple.com")),
    ("go to news dot ycombinator dot com", ("go_to", "news.ycombinator.com")),
    ("find pricing on the page", ("find", "pricing")),
    ("spotlight budget", ("spotlight", "budget")),
    ("run my morning shortcut", ("run_shortcut", "morning")),
    ("do that 3 times", ("again", 3)),
    ("show grid", ("grid",)),
    ("drag budget to the trash", ("drag", "budget", "trash")),
    ("scroll the sidebar down", ("scroll_in", "sidebar", "down")),
    ("Auto enter on.", ("mode", "auto_enter", True)),
    ("incognito mode", ("mode", "incognito", None)),
    ("turn off sounds", ("mode", "sounds", False)),
])
def test_parse(said, expected):
    assert parse(said) == expected


def test_type_keeps_what_was_said():
    assert parse("Type Hello@Example.com.") == ("type", "Hello@Example.com")
    assert parse("Write Dear John, thanks!") == ("type", "Dear John, thanks!")


@pytest.mark.parametrize("said, kind", [("top left", "shortcut"), ("tab left", "shortcut"), ("close tab", "shortcut"),
                                        ("scroll down", "scroll"), ("Chrome", "switch"), ("press sign in", "click"),
                                        ("new private window", "shortcut"), ("mute", "volume")])
def test_older_commands_still_win(said, kind):
    assert parse(said)[0] == kind  # "top left" is how Whisper hears "tab left"


def test_press_posts_the_key_with_its_modifiers():
    import Quartz
    events = []
    control.press("t", "cmd shift", post=events.append)
    assert len(events) == 2
    flags = Quartz.CGEventGetFlags(events[0])
    assert flags & Quartz.kCGEventFlagMaskCommand and flags & Quartz.kCGEventFlagMaskShift
    assert Quartz.CGEventGetIntegerValueField(events[0], Quartz.kCGKeyboardEventKeycode) == control.KEYCODES["t"]
    control.press("down", times=3, post=events.append)
    assert len(events) == 8


def test_snap_frames():
    screen = (0, 25, 1000, 800)
    assert control.snap_frame(screen, "left") == (0, 25, 500, 800)
    assert control.snap_frame(screen, "bottom right") == (500, 425, 500, 400)
    assert control.snap_frame(screen, "right two thirds")[2] == pytest.approx(666.67, abs=0.01)


def test_grid_cells_number_left_to_right():
    cells = control.grid_cells((0, 0, 300, 90))
    assert len(cells) == 9 and cells[0] == (0, 0, 100, 30) and cells[4] == (100, 30, 100, 30)


def test_switches_use_macos_tools():
    ran = []
    control.dark_mode(True, run=ran.append)
    assert "set dark mode to true" in ran[-1][-1]
    control.dark_mode(None, run=ran.append)
    assert "not dark mode" in ran[-1][-1]
    out = {"networksetup -listallhardwareports": "Hardware Port: Wi-Fi\nDevice: en1\n"}
    calls = []
    def run(cmd):
        calls.append(cmd)
        return out.get(" ".join(cmd), "Wi-Fi Power (en1): On")
    assert control.wifi(None, run=run) is False  # it was on: flip to off
    assert calls[-1] == ["networksetup", "-setairportpower", "en1", "off"]


def test_sound_output_by_closest_name():
    set_to = []
    devices = {"MacBook Pro Speakers": 1, "Max's AirPods Pro": 2}
    assert control.use_output("airpods", devices, set_to.append) == "Max's AirPods Pro" and set_to == [2]
    assert control.use_output("speakers", devices, set_to.append) == "MacBook Pro Speakers"
    assert control.use_output("tv", devices, set_to.append) is None


def test_search_urls_are_encoded():
    assert control.search_url("google", "pizza & beer") == "https://www.google.com/search?q=pizza+%26+beer"
    assert control.search_url("youtube", "lofi").startswith("https://www.youtube.com/results?search_query=")


def test_run_shortcut_by_closest_name():
    ran = []
    names = ["Morning Routine", "Turn Off Lights"]
    assert control.run_shortcut("morning", names, run=ran.append) == "Morning Routine"
    assert ran == [["shortcuts", "run", "Morning Routine"]]
    assert control.run_shortcut("turn of lights", names, run=ran.append) == "Turn Off Lights"
    assert control.run_shortcut("vacuum", names, run=ran.append) is None


def test_editing_that():
    pressed = []
    control.select_back(5, press_fn=lambda key, mods, n: pressed.append((key, mods, n)))
    assert pressed == [("left", "shift", 5)]
    assert control.transform("hello there", "capitalize") == "Hello there"
    assert control.transform("Hi", "uppercase") == "HI"


def test_custom_commands():
    cmds = [{"say": "sign off", "type": "Best,\nAlex"}, {"say": "send it", "keys": "cmd+enter"}, {"say": ""}, "junk"]
    assert control.custom("Sign off.", cmds) == ("custom", "sign off", [], "Best,\nAlex")
    assert control.custom("Send it!", cmds) == ("custom", "send it", [("return", "cmd")], "")
    assert control.custom("something else", cmds) is None
    assert control.custom("anything", None) is None
