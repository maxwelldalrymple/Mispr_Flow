import io
import json

import pytest

from mispr import host


class TestHosted:
    @pytest.mark.parametrize("value,expected", [("1", True), ("0", False), ("", False), (None, False)])
    def test_env_flag(self, monkeypatch, value, expected):
        if value is None:
            monkeypatch.delenv("MISPR_HOSTED", raising=False)
        else:
            monkeypatch.setenv("MISPR_HOSTED", value)
        assert host.hosted() is expected


class TestSend:
    def test_one_prefixed_json_line(self):
        out = io.StringIO()
        host.send("saved", out=out, path="/x/a.json")
        line = out.getvalue()
        assert line.startswith("@mispr ") and line.endswith("\n") and line.count("\n") == 1
        assert json.loads(line[len("@mispr "):]) == {"event": "saved", "path": "/x/a.json"}

    def test_defaults_to_stdout(self, capsys, monkeypatch):
        monkeypatch.setattr(host, "_channel", None)
        host.send("hello")
        assert capsys.readouterr().out == '@mispr {"event": "hello"}\n'


class TestChannel:
    def test_survives_stdout_being_pointed_at_dev_null(self, monkeypatch, tmp_path):
        """llama.cpp dup2()s /dev/null over fd 1 while loading; our channel must not care."""
        import os
        import sys
        target = open(tmp_path / "pipe", "w")
        saved = os.dup(1)
        monkeypatch.setattr(host, "_channel", None)
        monkeypatch.setattr(sys, "stdout", target)
        try:
            os.dup2(target.fileno(), 1)
            channel = host.open_channel()
            assert host.open_channel() is channel  # opened once
            with open(os.devnull, "w") as null:
                os.dup2(null.fileno(), 1)  # what llama.cpp does during a model load
                host.send("hello")
        finally:
            os.dup2(saved, 1)
            os.close(saved)
            channel.close()
            target.close()
        assert (tmp_path / "pipe").read_text() == '@mispr {"event": "hello"}\n'


class TestParse:
    @pytest.mark.parametrize("line,parsed", [
        ('{"cmd": "open_setup"}\n', ("open_setup", {})),
        ('{"cmd": "try_prompt", "text": "hi", "guard": false}', ("try_prompt", {"text": "hi", "guard": False})),
        ("", (None, {})), ("not json", (None, {})), ("[1, 2]", (None, {})), ('{"cmd": 5}', (None, {})),
        ('{"other": "x"}', (None, {})),
    ])
    def test_lines(self, line, parsed):
        assert host.parse(line) == parsed


class TestListen:
    def run(self, text, handlers):
        called, eof = [], []
        host.listen(
            {k: (lambda k=k: called.append(k)) for k in handlers},
            on_eof=lambda: eof.append(True),
            stream=io.StringIO(text),
            call=lambda fn: fn(),
            start=lambda target, name: target(),
        )
        return called, eof

    def test_runs_handlers_in_order_then_eof(self):
        called, eof = self.run('{"cmd": "reload_settings"}\n{"cmd": "open_setup"}\n', ["reload_settings", "open_setup"])
        assert called == ["reload_settings", "open_setup"] and eof == [True]

    def test_unknown_and_malformed_commands_are_skipped(self, capsys):
        called, eof = self.run('{"cmd": "dance"}\ngarbage\n{"cmd": "quit"}\n', ["quit"])
        assert called == ["quit"] and eof == [True]
        assert "unknown host command 'dance'" in capsys.readouterr().err

    def test_arguments_reach_the_handler(self):
        got = []
        host.listen({"try_prompt": lambda **kw: got.append(kw)}, on_eof=lambda: None,
                    stream=io.StringIO('{"cmd": "try_prompt", "text": "um hi"}\n'),
                    call=lambda fn: fn(), start=lambda target, name: target())
        assert got == [{"text": "um hi"}]

    def test_closed_stdin_means_the_app_is_gone(self):
        called, eof = self.run("", ["quit"])
        assert called == [] and eof == [True]

    def test_reads_on_a_named_daemon_thread(self):
        started = []
        host.listen({}, on_eof=lambda: None, stream=io.StringIO(""), start=lambda target, name: started.append(name))
        assert started == ["host-stdin"]


class TestConnectHost:
    def test_wiring(self, monkeypatch):
        from mispr import app
        sent, listened = [], {}
        monkeypatch.setattr(host, "send", lambda event, **f: sent.append((event, f)))
        monkeypatch.setattr(host, "listen", lambda handlers, on_eof: listened.update(handlers=handlers, eof=on_eof))

        class App:
            terminated = 0

            def terminate_(self, sender):
                App.terminated += 1

        class Widget:
            reloaded = 0
            settings = type("S", (), {"hotkey": {"kind": "fn"}})()

            def reload_settings(self):
                self.reloaded += 1

            begin_meeting = object()
            stop_meeting = object()
            transcriber = cleaner = None
            on_saved = on_note_requested = on_meeting_changed = on_settings_changed = meeting_levels = None

        opened = object()
        widget = Widget()
        app._connect_host(App(), widget, opened)
        assert sent[0][0] == "hello"
        assert set(sent[0][1]) == {"recordings_dir", "settings_path", "prompts_path", "default_prompts"}
        assert listened["handlers"]["open_setup"] is opened
        listened["handlers"]["reload_settings"]()
        assert widget.reloaded == 1
        widget.on_saved("/r/a.json")
        assert sent[-1] == ("saved", {"path": "/r/a.json"})
        assert listened["handlers"]["start_meeting"] is Widget.begin_meeting
        assert listened["handlers"]["stop_meeting"] is Widget.stop_meeting
        widget.on_note_requested()
        assert sent[-1] == ("open_note", {"start": True})
        listened["handlers"]["meeting_level"](level=0.7)
        assert widget.meeting_levels.level(0) == 0.7
        assert {"transcribe_chunk", "summarize", "ask"} <= set(listened["handlers"])
        worker = listened["handlers"]["transcribe_chunk"].__self__
        from mispr import models
        assert worker.preview.spec is models.PREVIEW_MODEL and not worker.preview._loading  # loads on first meeting
        assert worker.embedder.spec is models.SPEAKER_MODEL and worker.embedder._extractor is None
        widget.on_meeting_changed(True)
        assert sent[-1] == ("meeting", {"active": True})
        widget.on_settings_changed()  # a nickname set by voice: the app re-reads settings
        assert sent[-1] == ("settings_changed", {})
        listened["handlers"]["quit"]()
        listened["eof"]()
        assert App.terminated == 2


class TestTryPrompt:
    def test_runs_the_draft_and_reports(self, monkeypatch):
        from mispr import app
        sent = []
        monkeypatch.setattr(host, "send", lambda event, **f: sent.append((event, f)))

        class Cleaner:
            def clean(self, text, system, examples, guard):
                self.args = (text, system, examples, guard)
                return "Hi.", {"applied": True, "rejected": None, "ms": 12}

        c = Cleaner()
        app.try_prompt(c, text="um hi", system="Be terse.", extra="No emoji.",
                       examples="Said: a um b\nWrote: a b", guard=False, start=lambda target, name: target())
        assert c.args == ("um hi", "Be terse.\n\nAlso follow these rules from the user:\nNo emoji.", [["a um b", "a b"]], False)
        assert sent == [("tried", {"output": "Hi.", "applied": True, "rejected": None, "ms": 12})]

    def test_blank_instructions_mean_the_default(self, monkeypatch):
        from mispr import app, cleanup
        monkeypatch.setattr(host, "send", lambda event, **f: None)

        class Cleaner:
            def clean(self, text, system, examples, guard):
                self.system = system
                return text, {"applied": False, "rejected": None, "ms": 0}

        c = Cleaner()
        app.try_prompt(c, text="x", start=lambda target, name: target())
        assert c.system == cleanup.SYSTEM_PROMPT


def test_reload_applies_a_new_dictation_key(monkeypatch):
    from mispr import app
    listened = {}
    monkeypatch.setattr(host, "send", lambda event, **f: None)
    monkeypatch.setattr(host, "listen", lambda handlers, on_eof: listened.update(handlers))

    class Widget:
        settings = type("S", (), {"hotkey": {"kind": "key", "keycode": 96, "label": "F5"},
                                  "switch_hotkey": {"kind": "combo", "mods": ["control", "option"]}})()
        reload_settings = lambda self: None
        begin_meeting = stop_meeting = cleaner = transcriber = meeting_levels = None

    class Fn:
        def set_trigger(self, trigger):
            self.trigger = trigger

        def set_switch_trigger(self, trigger):
            self.switch = trigger

    fn = Fn()
    app._connect_host(object(), Widget(), lambda: None, fn)
    listened["reload_settings"]()
    assert fn.trigger == {"kind": "key", "keycode": 96, "label": "F5"}
    assert fn.switch == {"kind": "combo", "mods": ["control", "option"]}  # and the app switcher key
