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
