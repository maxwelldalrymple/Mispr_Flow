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
        ("Open the terminal, please.", ("open", "terminal")),
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
        ("quit slack", ("quit", "slack")), ("Quit.", ("quit", None)), ("quit this app", ("quit", None)),
        ("exit", ("quit", None)),
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


class TestScroll:
    @pytest.mark.parametrize("said,expected", [
        ("Scroll down.", ("scroll", -450)), ("scroll up", ("scroll", 450)), ("scroll down a little", ("scroll", -157)),
        ("scroll down a lot", ("scroll", -1350)), ("scroll up more", ("scroll", 900)), ("scroll down 3 times", ("scroll", -1350)),
        ("page down", ("scroll", -900)), ("scroll to the top", ("scroll_end", "top")),
        ("scroll all the way to the bottom", ("scroll_end", "bottom")),
        ("volume up", ("volume", "up")), ("up", ("switch", "up")),  # not a scroll without the word
    ])
    def test_commands(self, said, expected):
        assert apps.parse(said) == expected

    def test_scroll_events(self):
        import Quartz
        events = []
        apps.scroll(-450, post=events.append)
        assert len(events) == 3 and all(Quartz.CGEventGetType(e) == Quartz.kCGEventScrollWheel for e in events)
        assert Quartz.CGEventGetIntegerValueField(events[0], Quartz.kCGScrollWheelEventPointDeltaAxis1) < 0

    def test_top_and_bottom_are_cmd_arrows(self):
        assert apps.SHORTCUTS["top"] == ("up", "cmd") and apps.SHORTCUTS["bottom"] == ("down", "cmd")


class TestConfidentMatching:
    """Never open the wrong app: "Pro." (a clipped "Chrome") once opened Logic Pro."""

    APPS = {"Google Chrome": 1, "Logic Pro": 1, "Final Cut Pro": 1, "Terminal": 1, "Photos": 1, "Photo Booth": 1,
            "FaceTime": 1, "Visual Studio Code": 1, "Safari": 1}

    @pytest.mark.parametrize("said,running,expected", [
        ("pro", (), (None, False)),  # generic word: no match at all
        ("Pro", ("Logic Pro",), (None, False)),  # not even when Logic Pro is open
        ("chrome", (), ("Google Chrome", True)),  # one distinctive word: sure enough to open it
        ("logic", (), ("Logic Pro", True)),
        ("face time", (), ("FaceTime", True)),
        ("code", (), ("Visual Studio Code", False)),  # short word: only if it's already open
        ("term", (), ("Terminal", False)),
        ("sapari", (), ("Safari", False)),  # sounds close: only if open
        ("crome", (), (None, False)),
    ])
    def test_scores(self, said, running, expected):
        assert apps.match_scored(said, self.APPS, None, running) == expected


class TestFolders:
    @pytest.mark.parametrize("said,expected", [
        ("Open folder Projects.", ("open_folder", "projects")), ("open the downloads folder", ("open_folder", "downloads")),
        ("go to my voice recordings folder", ("open_folder", "voice recordings")), ("Open Budget.", ("open", "budget")),
        ("open the terminal please", ("open", "terminal")),
    ])
    def test_commands(self, said, expected):
        assert apps.parse(said) == expected

    def tree(self, tmp_path):
        for d in ("Work/Projects/Mispr_Flow/voice-recordings", "Projects", ".hidden/Taxes", "Library/Taxes", "Docs/Old/Taxes"):
            (tmp_path / d).mkdir(parents=True)
        (tmp_path / "Docs" / "Budget 2026.xlsx").write_text("x")
        (tmp_path / "Docs" / "budget").mkdir()
        return tmp_path

    def test_highest_level_wins_and_names_are_loose(self, tmp_path):
        root = self.tree(tmp_path)
        assert apps.find_in(root, "projects", files=False) == str(root / "Projects")  # not Work/Projects
        assert apps.find_in(root, "mispr flow", files=False) == str(root / "Work/Projects/Mispr_Flow")
        assert apps.find_in(root, "voice recordings", files=False).endswith("voice-recordings")

    def test_skips_hidden_and_library(self, tmp_path):
        root = self.tree(tmp_path)
        assert apps.find_in(root, "taxes", files=False) == str(root / "Docs/Old/Taxes")

    def test_files_by_name_without_extension_and_folders_first(self, tmp_path):
        root = self.tree(tmp_path)
        assert apps.find_in(root / "Docs", "budget") == str(root / "Docs/budget")  # a folder named exactly that
        assert apps.find_in(root / "Docs", "budget 2026") == str(root / "Docs/Budget 2026.xlsx")
        assert apps.find_in(root, "nope") is None and apps.find_in(root, "...") is None

    def test_gives_up_after_its_time_budget(self, tmp_path):
        root = self.tree(tmp_path)
        ticks = iter(range(100))
        assert apps.find_in(root, "voice recordings", budget=1, clock=lambda: next(ticks)) is None

    def test_finder_scripts(self):
        ran = []
        assert apps.finder_folder(lambda cmd: ran.append(cmd[2]) or "/Users/me/Docs/") == "/Users/me/Docs"
        assert apps.finder_folder(lambda cmd: "") is None  # no window, or not allowed
        apps.finder_go('/Users/me/My "Quoted" Folder', lambda cmd: ran.append(cmd[2]))
        assert 'POSIX file "/Users/me/My \\"Quoted\\" Folder"' in ran[-1]

    def test_finder_permission_check_never_prompts(self):
        assert apps.finder_control() in (True, False, None)


class TestSoundAlikeNames:
    """Whisper wrote "clawed" for "Claude": the folder should still open."""

    def test_sound_codes(self):
        assert apps.sounds_like("clawed") == apps.sounds_like("Claude") == apps.sounds_like("claw to") == "C430"
        assert apps.sounds_like("Robert") == apps.sounds_like("Rupert")
        assert apps.sounds_like("abc") is None  # too short to trust

    def test_exact_name_wins_then_highest_sound_alike(self, tmp_path):
        (tmp_path / "work" / "claude").mkdir(parents=True)
        (tmp_path / "Clawed Notes").mkdir()
        assert apps.find_in(tmp_path, "clawed", files=False) == str(tmp_path / "work" / "claude")
        (tmp_path / "Clawed").mkdir()
        assert apps.find_in(tmp_path, "clawed", files=False) == str(tmp_path / "Clawed")  # exact beats sound-alike


class TestSpotlightAndAccess:
    def test_spotlight_exact_then_sound_alike_shallowest(self, tmp_path):
        out = {"*clawed*": "", "cl*": f"{tmp_path}/a/b/claude\n{tmp_path}/claude\n{tmp_path}/.hidden/claude\n{tmp_path}/clips\n"}
        run = lambda cmd: next(v for k, v in out.items() if f"'{k}'" in cmd[-1])
        for d in ("a/b/claude", "claude", "clips"):
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        assert apps.spotlight(tmp_path, "clawed", files=False, run=run) == str(tmp_path / "claude")

    def test_spotlight_off_or_failing_is_none(self, tmp_path):
        assert apps.spotlight(tmp_path, "claude", run=lambda cmd: "") is None
        assert apps.spotlight(tmp_path, "claude", run=lambda cmd: (_ for _ in ()).throw(OSError())) is None

    def test_full_disk_access_check(self, tmp_path):
        locked = tmp_path / "locked"
        locked.write_text("x")
        assert apps.full_disk_access(locked) is True
        locked.chmod(0)
        try:
            assert apps.full_disk_access(locked) is False
        finally:
            locked.chmod(0o600)
        assert apps.full_disk_access(tmp_path / "missing") is True


class TestSystemHelpersSafely:
    """Window, tab, quit and open helpers, run where they can't change anything."""

    NO_WINDOWS = 999_999  # no such process: nothing to find or change

    def test_window_helpers_answer_no_window(self):
        assert apps._window(self.NO_WINDOWS) is None
        assert apps.window_action(self.NO_WINDOWS, "close") is False
        assert apps.window_action(self.NO_WINDOWS, "frame", (0, 0, 100, 100)) is False
        assert apps.mute_tab(self.NO_WINDOWS) is False

    def test_quit_needs_a_real_app(self):
        assert apps.quit_app(self.NO_WINDOWS) is False

    def test_open_path_uses_open(self):
        ran = []
        apps.open_path("/Users/me/Docs", run=ran.append)
        assert ran == [["open", "/Users/me/Docs"]]
