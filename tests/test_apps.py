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
