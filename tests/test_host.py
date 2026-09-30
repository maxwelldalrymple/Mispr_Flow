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

    def test_defaults_to_stdout(self, capsys):
        host.send("hello")
        assert capsys.readouterr().out == '@mispr {"event": "hello"}\n'


class TestParse:
    @pytest.mark.parametrize("line,cmd", [
        ('{"cmd": "open_setup"}\n', "open_setup"),
        ('{"cmd": "quit", "extra": 1}', "quit"),
        ("", None), ("not json", None), ("[1, 2]", None), ('{"cmd": 5}', None), ('{"other": "x"}', None),
    ])
    def test_lines(self, line, cmd):
        assert host.parse(line) == cmd


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
            reload_settings = object()
            on_saved = None

        opened = object()
        widget = Widget()
        app._connect_host(App(), widget, opened)
        assert sent[0][0] == "hello" and set(sent[0][1]) == {"recordings_dir", "settings_path"}
        assert listened["handlers"]["open_setup"] is opened
        assert listened["handlers"]["reload_settings"] is Widget.reload_settings
        widget.on_saved("/r/a.json")
        assert sent[-1] == ("saved", {"path": "/r/a.json"})
        listened["handlers"]["quit"]()
        listened["eof"]()
        assert App.terminated == 2
