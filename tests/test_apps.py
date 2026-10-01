"""The voice app switcher: understanding what was said and finding the app."""

import pytest

from mispr import apps

APPS = {"Google Chrome": "/A/Google Chrome.app", "Terminal": "/S/Terminal.app", "Photos": "/S/Photos.app",
        "Photo Booth": "/S/Photo Booth.app", "FaceTime": "/S/FaceTime.app", "Visual Studio Code": "/A/Code.app",
        "Safari": "/A/Safari.app", "Slack": "/A/Slack.app", "Chrome Remote Desktop": "/A/CRD.app"}


class TestParse:
    @pytest.mark.parametrize("said,expected", [
        ("Set nickname Scooby Snacks to Chrome.", ("nickname", "scooby snacks", "chrome")),
        ("nickname C for Chrome", ("nickname", "c", "chrome")),
        ("Set the nickname for Terminal to T.", ("nickname", "t", "terminal")),
        ("Make a nick name L as Slack", ("nickname", "l", "slack")),
        ("Chrome.", ("switch", "chrome")),
        ("Open the terminal, please.", ("switch", "terminal")),
        ("Switch to Slack", ("switch", "slack")),
        ("Go to FaceTime app", ("switch", "facetime")),
        ("C", ("switch", "c")),
    ])
    def test_commands(self, said, expected):
        assert apps.parse(said) == expected

    @pytest.mark.parametrize("said", ["", "  ", "...", "open"])
    def test_nothing_usable(self, said):
        assert apps.parse(said) in (None, ("switch", "open"))

    def test_normalize(self):
        assert apps.normalize("Google  Chrome’s!") == "google chromes"


class TestMatch:
    @pytest.mark.parametrize("said,app", [
        ("chrome", "Google Chrome"),  # a word of the name, shorter name preferred
        ("terminal", "Terminal"),
        ("photo", "Photos"),  # near-exact beats Photo Booth
        ("photo booth", "Photo Booth"),
        ("face time", "FaceTime"),
        ("code", "Visual Studio Code"),
        ("term", "Terminal"),  # prefix
        ("sapari", "Safari"),  # misheard
        ("SLACK", "Slack"),
    ])
    def test_finds_the_app(self, said, app):
        assert apps.match(said, APPS) == app

    def test_nickname_wins(self):
        assert apps.match("Scooby Snacks", APPS, {"scooby snacks": "Google Chrome"}) == "Google Chrome"
        assert apps.match("c", APPS, {"C": "Google Chrome"}) == "Google Chrome"

    def test_unsure_is_none(self):
        assert apps.match("xyzzy", APPS) is None
        assert apps.match("c", APPS) is None  # one letter only works as a nickname
        assert apps.match("", APPS) is None

    def test_running_apps_win_ties(self):
        assert apps.match("chrome", APPS) == "Google Chrome"
        assert apps.match("chrome", APPS, running={"Chrome Remote Desktop": "/A/CRD.app"}) == "Chrome Remote Desktop"


class TestFindApps:
    def test_finds_apps_one_level_deep_first_wins(self, tmp_path):
        (tmp_path / "A" / "Chrome.app").mkdir(parents=True)
        (tmp_path / "A" / "Utilities" / "Console.app").mkdir(parents=True)
        (tmp_path / "A" / ".hidden" / "Nope.app").mkdir(parents=True)
        (tmp_path / "B" / "Chrome.app").mkdir(parents=True)
        found = apps.find_apps([str(tmp_path / "A"), str(tmp_path / "B"), str(tmp_path / "missing")])
        assert found == {"Chrome": str(tmp_path / "A" / "Chrome.app"), "Console": str(tmp_path / "A" / "Utilities" / "Console.app")}

    def test_this_mac_has_apps(self):
        assert "Safari" in apps.find_apps() or "Finder" in apps.find_apps()


class TestSystem:
    def test_running_apps_are_regular_apps(self):
        running = apps.running_apps()
        assert all(path.endswith(".app") for path in running.values())

    def test_bring_to_front_asks_workspace_to_open_and_activate(self):
        opened = []

        class FakeWorkspace:
            def openApplicationAtURL_configuration_completionHandler_(self, url, config, done):
                opened.append((url.path(), config.activates()))

        assert apps.bring_to_front("/Applications/Safari.app", FakeWorkspace()) is True
        assert opened == [("/Applications/Safari.app", True)]


class TestWindowCommands:
    """close / minimize / expand, side by side, and "chrome 80%"."""

    @pytest.mark.parametrize("said,expected", [
        ("Close Chrome.", ("close", "chrome")),
        ("close", ("close", None)),
        ("Minimize the terminal.", ("minimize", "terminal")),
        ("Expand VS Code", ("expand", "vs code")),
        ("maximize", ("expand", None)),
        ("Window layout Chrome beside VS Code.", ("beside", "chrome", "vs code", None)),
        ("Chrome 70% beside VS code", ("beside", "chrome", "vs code", 70)),
        ("put chrome next to terminal", ("beside", "chrome", "terminal", None)),
        ("Chrome 80%.", ("size", "chrome", 80)),
        ("Chrome eighty percent", ("size", "chrome", 80)),
        ("make slack sixty-five percent", ("size", "slack", 65)),
        ("Chrome 5%", ("switch", "chrome 5")),  # too small to mean a size
    ])
    def test_commands(self, said, expected):
        assert apps.parse(said) == expected

    def test_layouts(self):
        screen = (0, 25, 1440, 875)
        assert apps.layout(screen, "expand") == screen
        assert apps.layout(screen, "size", 80) == (144.0, 112.5, 1152.0, 700.0)  # centred
        assert apps.layout(screen, "beside") == ((0, 25, 720.0, 875), (720.0, 25, 720.0, 875))
        assert apps.layout(screen, "beside", 70) == ((0, 25, 1008.0, 875), (1008.0, 25, 432.0, 875))

    def test_this_macs_screen_and_front_app(self):
        x, y, w, h = apps.screen_frame()
        assert w > 0 and h > 0 and y >= 0
        assert apps.frontmost_pid() is not None
        assert apps.pid_for("/no/such.app") is None


class TestShortcuts:
    """Tab and browser commands are the apps' own keyboard shortcuts."""

    @pytest.mark.parametrize("said,expected", [
        ("New tab.", ("shortcut", "new tab", None)),
        ("Close tab in Chrome", ("shortcut", "close tab", "chrome")),
        ("Chrome new tab", ("shortcut", "new tab", "chrome")),
        ("Go to tab 3", ("shortcut", "tab 3", None)),
        ("Open incognito window in Chrome", ("shortcut", "new private window", "chrome")),
        ("go forward in safari", ("shortcut", "forward", "safari")),
        ("Refresh", ("shortcut", "reload", None)),
        ("reopen closed tab", ("shortcut", "reopen tab", None)),
        ("quit slack", ("quit", "slack")),
        ("tab 12", None),
    ])
    def test_commands(self, said, expected):
        assert apps.parse(said) == expected

    def test_every_alias_is_a_real_shortcut(self):
        assert set(apps.SHORTCUT_ALIASES.values()) <= set(apps.SHORTCUTS)

    @pytest.mark.parametrize("name,code,mods", [("new tab", 17, {"cmd"}), ("reopen tab", 17, {"cmd", "shift"}),
                                                ("next tab", 48, {"ctrl"}), ("tab 3", 20, {"cmd"})])
    def test_keys_pressed(self, name, code, mods):
        import Quartz
        events = []
        apps.press_shortcut(name, post=events.append)
        assert [Quartz.CGEventGetType(e) for e in events] == [Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp]
        assert Quartz.CGEventGetIntegerValueField(events[0], Quartz.kCGKeyboardEventKeycode) == code
        flags = Quartz.CGEventGetFlags(events[0])
        masks = {"cmd": Quartz.kCGEventFlagMaskCommand, "shift": Quartz.kCGEventFlagMaskShift, "ctrl": Quartz.kCGEventFlagMaskControl}
        assert {m for m, bit in masks.items() if flags & bit} == mods


class TestSound:
    """Play/pause, volume, mic and tab muting."""

    @pytest.mark.parametrize("said,expected", [
        ("Pause.", ("media", "play")), ("play the music", ("media", "play")), ("next song", ("media", "next")),
        ("previous track", ("media", "previous")), ("Volume up", ("volume", "up")), ("turn it down", ("volume", "down")),
        ("volume 40%", ("volume", 40)), ("set volume to thirty percent", ("volume", 30)),
        ("mute", ("volume", "mute")), ("unmute the sound", ("volume", "unmute")),
        ("Mute mic.", ("mic", True)), ("unmute my microphone", ("mic", False)),
        ("mute tab", ("mute_tab", None, True)), ("mute this tab in chrome", ("mute_tab", "chrome", True)),
        ("unmute tab", ("mute_tab", None, False)), ("unmute the site in chrome", ("mute_tab", "chrome", False)),
        ("mute Spotify", ("mute_app", "spotify", True)), ("unmute spotify", ("mute_app", "spotify", False)),
    ])
    def test_commands(self, said, expected):
        assert apps.parse(said) == expected

    def test_volume_scripts(self):
        ran = []
        run = lambda cmd: ran.append(cmd[2]) or "60"
        assert apps.set_volume("up", run) == 60
        assert "+ 10) without output muted" in ran[0]
        apps.set_volume(35, run)
        assert ran[2] == "set volume output volume 35 without output muted"
        assert apps.set_volume("mute", run) is None and ran[-1] == "set volume output muted true"

    def test_mic_level(self):
        assert apps.mic_level(lambda cmd: "72") == 72 and apps.mic_level(lambda cmd: "missing value") is None
        ran = []
        apps.set_mic_level(0, lambda cmd: ran.append(cmd[2]))
        assert ran == ["set volume input volume 0"]

    def test_media_key_events(self):
        import Quartz
        events = []
        apps.press_media("play", post=events.append)
        assert len(events) == 2 and all(Quartz.CGEventGetType(e) == 14 for e in events)  # system-defined


class TestSeek:
    @pytest.mark.parametrize("said,expected", [
        ("Skip forward 30 seconds.", ("seek", 30, None)), ("skip back 15 seconds", ("seek", -15, None)),
        ("skip forward", ("seek", 10, None)), ("rewind 20 seconds", ("seek", -20, None)),
        ("jump ahead 2 minutes", ("seek", 120, None)), ("go back 10 seconds in chrome", ("seek", -10, "chrome")),
        ("skip backward thirty seconds", ("seek", -30, None)), ("rewind", ("seek", -10, None)),
        ("next song", ("media", "next")),
    ])
    def test_commands(self, said, expected):
        assert apps.parse(said) == expected

    def test_one_arrow_per_five_seconds(self):
        import Quartz
        events = []
        apps.seek(30, post=events.append)
        downs = [e for e in events if Quartz.CGEventGetType(e) == Quartz.kCGEventKeyDown]
        assert len(downs) == 6 and Quartz.CGEventGetIntegerValueField(downs[0], Quartz.kCGKeyboardEventKeycode) == 124
        events.clear()
        apps.seek(-7, post=events.append)  # rounds to one press back
        assert len(events) == 2 and Quartz.CGEventGetIntegerValueField(events[0], Quartz.kCGKeyboardEventKeycode) == 123
