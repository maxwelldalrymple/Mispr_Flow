"""Quiet while you talk (mispr/duck.py). osascript is replaced by a recorder: nothing on this Mac
is muted by these tests."""

from mispr.duck import Ducker


def make(tmp_path, muted="false"):
    ran = []
    def run(script):
        ran.append(script)
        return muted if script.startswith("output muted") else ""
    return Ducker(run=run, marker=tmp_path / "marker", start=lambda fn: fn(), sleep=lambda s: None), ran


def test_mutes_then_restores(tmp_path):
    d, ran = make(tmp_path)
    d.duck()
    assert "set volume output muted true" in ran and (tmp_path / "marker").exists()
    d.restore()
    assert ran[-1] == "set volume output muted false" and not (tmp_path / "marker").exists()


def test_already_muted_by_you_stays_muted(tmp_path):
    d, ran = make(tmp_path, muted="true")
    d.duck()
    d.restore()
    assert "set volume output muted true" not in ran and "set volume output muted false" not in ran


def test_a_quick_tap_never_mutes(tmp_path):
    later = []
    d, ran = make(tmp_path)
    d.start = later.append  # the delayed mute hasn't run yet
    d.duck()
    d.restore()  # let go before it ran
    later[0]()
    assert "set volume output muted true" not in ran


def test_recovers_after_a_crash(tmp_path):
    d, ran = make(tmp_path)
    (tmp_path / "marker").write_text("1")
    assert d.recover() and ran == ["set volume output muted false"] and not (tmp_path / "marker").exists()
    assert not d.recover()
