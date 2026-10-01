import json

import pytest

from mispr import cleanup, prompts


@pytest.fixture
def path(tmp_path):
    return tmp_path / "prompts.json"


class TestLoadSave:
    def test_defaults_when_missing(self, path):
        p = prompts.load(path)
        assert p.system == cleanup.SYSTEM_PROMPT and p.extra == "" and p.guard is True
        assert p.examples == [list(e) for e in cleanup.EXAMPLES]

    def test_round_trip(self, path):
        p = prompts.Prompts(system="S", extra="E", examples=[["a", "b"]], guard=False)
        prompts.save(p, path)
        assert prompts.load(path) == p

    def test_blank_system_falls_back(self, path):
        path.write_text(json.dumps({"system": "", "extra": "x"}))
        p = prompts.load(path)
        assert p.system == cleanup.SYSTEM_PROMPT and p.extra == "x"

    @pytest.mark.parametrize("bad", ["{not json", '{"examples": "nope"}', '{"examples": [["only one"]]}'])
    def test_bad_files_or_examples_fall_back(self, path, bad, capsys):
        path.write_text(bad)
        assert prompts.load(path).examples == [list(e) for e in cleanup.EXAMPLES]


class TestFullSystem:
    def test_extra_rules_are_appended(self):
        p = prompts.Prompts(system="Clean it.", extra="  Use British spelling.  ")
        assert p.full_system() == "Clean it.\n\nAlso follow these rules from the user:\nUse British spelling."

    def test_no_extra_no_suffix(self):
        assert prompts.Prompts(system="Clean it.\n").full_system() == "Clean it."


class TestExamplesText:
    def test_round_trip(self):
        pairs = [["um hi", "Hi."], ["a, a b", "A b."]]
        assert prompts.parse_examples(prompts.format_examples(pairs)) == pairs

    def test_format(self):
        assert prompts.format_examples([["a", "b"], ["c", "d"]]) == "Said: a\nWrote: b\n\nSaid: c\nWrote: d"

    def test_incomplete_pairs_and_noise_are_skipped(self):
        text = "Said: one\nnoise\nWrote: 1\n\nWrote: orphan\nSaid: dangling"
        assert prompts.parse_examples(text) == [["one", "1"]]

    def test_defaults_payload(self):
        d = prompts.defaults_payload()
        assert d["system"] == cleanup.SYSTEM_PROMPT
        assert prompts.parse_examples(d["examples"]) == [list(e) for e in cleanup.EXAMPLES]


class TestWidgetUsesPrompts:
    def test_applied_at_start_and_on_reload(self, controller, monkeypatch):
        import mispr.widget as W
        monkeypatch.setattr(W.prompts, "load", lambda: prompts.Prompts(system="S", extra="", examples=[["a", "b"]], guard=False))
        controller.reload_settings()
        assert controller.cleaner.configured[-1] == ("S", [["a", "b"]], False)
