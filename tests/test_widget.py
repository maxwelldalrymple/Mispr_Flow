import json

import numpy as np
import pytest
from PyObjCTools import AppHelper

import mispr.widget as W
from mispr import storage
from mispr.draw import Rect

ALL_STATES = [W.IDLE, W.HOVER, W.HOLD, W.HANDSFREE, W.PROCESSING, W.CANCELLED, W.MEETING, W.MISTAKE, W.SETUP]


def center(c, name):
    r = W.layout(c.state).elems[name]
    return r.cx, r.cy


def click(c, name):
    x, y = center(c, name)
    c.mouse_down(x, y)
    c.mouse_up(x, y)


def finish_transcription(c, text="Hello world.", raw=None, info=None, secs=0.9):
    """Deliver the (fake) transcriber's result as if the worker thread finished."""
    audio, on_done, post = c.transcriber.calls[-1]
    on_done(text, raw if raw is not None else text, info, secs)


def saved_json(tmp_path):
    return [json.loads(p.read_text()) for p in sorted((tmp_path / "voice-recordings").rglob("*.json"))]


# --- Shape / layout / tooltips ------------------------------------------------------------

class TestShape:
    def test_values_roundtrip(self):
        s = W.Shape(Rect(1, 2, 3, 4), 5, 0.6, 0.7)
        assert W.Shape.from_values(s.values()) == s

    def test_values_order(self):
        assert W.Shape(Rect(1, 2, 3, 4), 5, 0.6, 0.7).values() == [1, 2, 3, 4, 5, 0.6, 0.7]


class TestLayout:
    @pytest.mark.parametrize("state", ALL_STATES)
    def test_every_state_has_a_layout(self, state):
        lay = W.layout(state)
        assert isinstance(lay, W.Layout) and lay.bg.rect.w > 0 and lay.bg.rect.h > 0

    @pytest.mark.parametrize("state", ALL_STATES)
    def test_interactive_elements_exist(self, state):
        lay = W.layout(state)
        assert set(lay.interactive) <= set(lay.elems)

    @pytest.mark.parametrize("state", ALL_STATES)
    def test_everything_fits_in_the_panel(self, state):
        lay = W.layout(state)
        for r in [lay.bg.rect, *lay.elems.values()]:
            assert r.x >= 0 and r.y >= 0 and r.right <= W.VIEW_W and r.top <= W.VIEW_H

    @pytest.mark.parametrize("state", ALL_STATES)
    def test_opacities_valid(self, state):
        bg = W.layout(state).bg
        assert 0 <= bg.fill <= 1 and 0 <= bg.stroke <= 1 and bg.radius <= bg.rect.h / 2 + 1e-9

    def test_unknown_state_raises(self):
        with pytest.raises(ValueError):
            W.layout("nonsense")

    @pytest.mark.parametrize("state", ALL_STATES)
    def test_clickable_elements_do_not_overlap(self, state):
        lay = W.layout(state)
        names = [n for n in lay.interactive if n != "wave"]  # wave is a tooltip zone between buttons
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                ra, rb = lay.elems[a], lay.elems[b]
                assert ra.right <= rb.x or rb.right <= ra.x or ra.top <= rb.y or rb.top <= ra.y, (a, b)

    def test_hover_buttons_sized_and_lifted(self):
        lay = W.layout(W.HOVER)
        assert lay.elems["mic"].h == 36 and lay.elems["note"].h == 36 and lay.elems["mic"].y == 12

    def test_idle_pill_is_centered(self):
        assert W.layout(W.IDLE).bg.rect.cx == W.CX

    def test_processing_has_no_clickable_parts(self):
        assert W.layout(W.PROCESSING).interactive == ()

    def test_idle_and_hold_are_click_through(self):
        assert W.layout(W.IDLE).interactive == () and W.layout(W.HOLD).interactive == ()


class TestTooltips:
    def test_every_tooltip_points_at_an_element(self):
        for (state, name), parts in W.TOOLTIPS.items():
            assert name in W.layout(state).elems
            assert parts and all(isinstance(t, str) and isinstance(b, bool) for t, b in parts)

    def test_handsfree_hint_matches_shortcuts(self):
        text = "".join(t for t, _ in W.TOOLTIPS[(W.HANDSFREE, "wave")])
        assert text == "space to paste · fn to cancel"


# --- State machine basics ------------------------------------------------------------

class TestStateBasics:
    def test_initial_state(self, controller):
        assert controller.state == W.IDLE and controller.seq == 0

    def test_set_state_bumps_seq_and_resets_fade(self, controller):
        controller.content_a = 1.0
        controller.set_state(W.HOVER)
        assert controller.state == W.HOVER and controller.seq == 1 and controller.content_a == 0.0

    def test_set_same_state_is_noop(self, controller):
        controller.set_state(W.IDLE)
        assert controller.seq == 0

    def test_state_since_updates(self, controller, clock):
        clock.advance(5)
        controller.set_state(W.HOVER)
        assert controller.state_since == clock.now

    def test_to_idle_suppresses_hover(self, controller):
        controller.set_state(W.HOVER)
        controller.to_idle()
        assert controller.state == W.IDLE and controller.suppress_hover is True

    def test_scheduled_callback_runs_when_due(self, controller, clock):
        ran = []
        controller.after(2.0, lambda: ran.append(1))
        controller._run_due(clock.now + 1.9)
        assert ran == []
        controller._run_due(clock.now + 2.0)
        assert ran == [1] and controller.pending == []

    def test_stale_callbacks_are_dropped_after_state_change(self, controller, clock):
        ran = []
        controller.after(1.0, lambda: ran.append(1))
        controller.set_state(W.HOVER)
        controller._run_due(clock.now + 5)
        assert ran == [] and controller.pending == []

    def test_callbacks_run_in_schedule_order(self, controller, clock):
        ran = []
        controller.after(1.0, lambda: ran.append("a"))
        controller.after(2.0, lambda: ran.append("b"))
        controller._run_due(clock.now + 3)
        assert ran == ["a", "b"]

    @pytest.mark.parametrize("state,fullscreen,hidden", [
        (W.IDLE, True, True), (W.HOVER, True, True), (W.HOLD, True, False),
        (W.HANDSFREE, True, False), (W.IDLE, False, False), (W.SETUP, True, False),
    ])
    def test_hidden(self, controller, state, fullscreen, hidden):
        controller.state, controller.fullscreen = state, fullscreen
        assert controller.hidden is hidden


# --- fn key gestures --------------------------------------------------------------------

class TestFnGestures:
    def test_hold_records_then_finishes(self, controller, clock):
        controller.fn_down()
        assert controller.state == W.HOLD and controller.hold_source == "fn"
        assert controller.recorder.started == 1
        clock.advance(1.5)
        controller.fn_up()
        assert controller.state == W.PROCESSING and controller.recorder.stopped >= 1
        assert len(controller.transcriber.calls) == 1

    def test_quick_tap_is_discarded_silently(self, controller, clock):
        controller.fn_down()
        clock.advance(0.1)
        controller.fn_up()
        assert controller.state == W.IDLE and controller.transcriber.calls == []
        assert controller.recorder.wiped == 1 and controller.last_tap_at is not None

    @pytest.mark.parametrize("held,expected", [(W.FN_TAP_MAX - 0.01, W.IDLE), (W.FN_TAP_MAX + 0.01, W.PROCESSING)])
    def test_tap_vs_hold_threshold(self, controller, clock, held, expected):
        controller.fn_down()
        clock.advance(held)
        controller.fn_up()
        assert controller.state == expected

    def test_double_tap_starts_handsfree(self, controller, clock):
        controller.fn_down(); clock.advance(0.1); controller.fn_up()
        clock.advance(0.3)
        controller.fn_down()
        assert controller.state == W.HANDSFREE and controller.last_tap_at is None
        clock.advance(0.1)
        controller.fn_up()
        assert controller.state == W.HANDSFREE  # releasing the 2nd tap doesn't stop it

    def test_double_tap_window_is_measured_from_first_press(self, controller, clock):
        controller.fn_down(); clock.advance(0.2); controller.fn_up()
        clock.advance(W.DOUBLE_TAP_WINDOW - 0.2)  # second press exactly 1 s after the first
        controller.fn_down()
        assert controller.state == W.HANDSFREE

    def test_slow_second_tap_is_a_new_hold(self, controller, clock):
        controller.fn_down(); clock.advance(0.1); controller.fn_up()
        clock.advance(1.5)
        controller.fn_down()
        assert controller.state == W.HOLD

    def test_fn_in_handsfree_cancels(self, controller, clock):
        controller.begin_handsfree()
        clock.advance(2)
        controller.fn_down()
        assert controller.state == W.CANCELLED
        controller.fn_up()
        assert controller.state == W.CANCELLED  # consumed press; release does nothing

    @pytest.mark.parametrize("busy", [W.PROCESSING, W.MEETING, W.MISTAKE, W.SETUP])
    def test_fn_ignored_while_busy(self, controller, busy):
        controller.state = busy
        controller.fn_down()
        controller.fn_up()
        assert controller.state == busy and controller.recorder.started == 0

    def test_fn_works_from_hover(self, controller):
        controller.set_state(W.HOVER)
        controller.fn_down()
        assert controller.state == W.HOLD

    def test_mic_failure_keeps_state(self, controller):
        controller.recorder.start_ok = False
        controller.fn_down()
        assert controller.state == W.IDLE
        controller.fn_up()
        assert controller.state == W.IDLE

    def test_fn_combo_discards_hold(self, controller, clock):
        controller.fn_down()
        clock.advance(0.5)
        controller.fn_combo()
        assert controller.state == W.IDLE and controller.recorder.wiped == 1
        controller.fn_up()
        assert controller.state == W.IDLE and controller.transcriber.calls == []

    def test_fn_combo_clears_pending_double_tap(self, controller, clock):
        controller.fn_down(); clock.advance(0.1); controller.fn_up()
        controller.fn_combo()
        clock.advance(0.2)
        controller.fn_down()
        assert controller.state == W.HOLD  # not hands-free

    def test_fn_combo_ignored_outside_fn_hold(self, controller):
        controller.begin_handsfree()
        controller.fn_combo()
        assert controller.state == W.HANDSFREE

    def test_fn_up_without_press_is_harmless(self, controller):
        controller.fn_up()
        assert controller.state == W.IDLE

    def test_fn_up_ignored_for_mouse_hold(self, controller, clock):
        controller.begin_hold("mouse")
        clock.advance(2)
        controller.fn_consumed = False
        controller.fn_up()
        assert controller.state == W.HOLD


# --- Keyboard shortcuts ----------------------------------------------------------------------

class TestKeys:
    @pytest.mark.parametrize("key", [W.KEY_SPACE, W.KEY_RETURN, W.KEY_KEYPAD_ENTER])
    def test_accept_keys_finish(self, controller, key):
        controller.begin_handsfree()
        assert controller.handle_key(key) is True
        assert controller.state == W.PROCESSING

    def test_delete_cancels(self, controller):
        controller.begin_handsfree()
        assert controller.handle_key(W.KEY_DELETE) is True
        assert controller.state == W.CANCELLED

    def test_delete_on_toast_discards_immediately(self, controller):
        controller.begin_handsfree()
        controller.cancel()
        assert controller.handle_key(W.KEY_DELETE) is True
        assert controller.state == W.IDLE and controller.recorder.wiped == 1

    @pytest.mark.parametrize("state", [W.IDLE, W.HOVER, W.HOLD, W.PROCESSING, W.MEETING, W.MISTAKE, W.SETUP])
    @pytest.mark.parametrize("key", [W.KEY_SPACE, W.KEY_RETURN, W.KEY_DELETE])
    def test_keys_pass_through_in_other_states(self, controller, state, key):
        controller.state = state
        assert controller.handle_key(key) is False
        assert controller.state == state

    def test_space_on_toast_passes_through(self, controller):
        controller.begin_handsfree()
        controller.cancel()
        assert controller.handle_key(W.KEY_SPACE) is False

    def test_other_keys_pass_through(self, controller):
        controller.begin_handsfree()
        assert controller.handle_key(0) is False and controller.state == W.HANDSFREE

    def test_deferred_action_skipped_if_state_changed(self, controller, monkeypatch):
        queued = []
        monkeypatch.setattr(AppHelper, "callAfter", lambda fn, *a: queued.append(fn))
        controller.begin_handsfree()
        assert controller.handle_key(W.KEY_SPACE) is True
        controller.cancel()  # state changes before the queued action runs
        queued[0]()
        assert controller.state == W.CANCELLED  # finish() did not fire


# --- Cancel / Undo ----------------------------------------------------------------------------

class TestCancelUndo:
    def test_cancel_keeps_audio_until_toast_expires(self, controller, clock):
        controller.begin_handsfree()
        controller.cancel()
        assert controller.state == W.CANCELLED and controller.recorder.wiped == 0
        controller._run_due(clock.now + W.TOAST_SECONDS - 0.1)
        assert controller.state == W.CANCELLED
        controller._run_due(clock.now + W.TOAST_SECONDS)
        assert controller.state == W.IDLE and controller.recorder.wiped == 1

    def test_undo_processes_the_recording(self, controller):
        controller.begin_handsfree()
        controller.cancel()
        click(controller, "undo")
        assert controller.state == W.PROCESSING and len(controller.transcriber.calls) == 1

    def test_undo_cancels_the_expiry(self, controller, clock):
        controller.begin_handsfree()
        controller.cancel()
        controller.undo_cancel()
        controller._run_due(clock.now + 60)
        assert controller.state == W.PROCESSING and controller.recorder.wiped == 0

    def test_new_recording_supersedes_toast(self, controller, speech):
        controller.recorder.audio_data = speech
        controller.begin_handsfree()
        controller.cancel()
        controller.fn_down()
        assert controller.state == W.HOLD and controller.recorder.wiped == 1

    def test_cancel_sets_end_time(self, controller):
        controller.begin_handsfree()
        controller.cancel()
        assert controller.rec_ended_at is not None


# --- Transcription result → paste → save → wipe ------------------------------------------------

class TestTranscribed:
    def test_text_is_pasted_saved_and_wiped(self, controller, speech, isolated_paths):
        controller.recorder.audio_data = speech
        controller.begin_handsfree()
        controller.finish()
        finish_transcription(controller, "Hello world.", raw="um hello world",
                             info={"model": "g", "applied": True, "ms": 400, "rejected": None})
        assert controller.pasted == ["Hello world."]
        assert controller.state == W.IDLE and controller.recorder.wiped == 1
        (meta,) = saved_json(isolated_paths)
        assert meta["status"] == "pasted" and meta["transcript"] == "Hello world."
        assert meta["raw_transcript"] == "um hello world" and meta["cleanup"]["applied"] is True
        assert meta["recorded_in"] == {"app": "TestApp", "bundle_id": "com.test.app"}
        assert meta["pasted_into"]["url"] == "https://example.com/page"

    def test_empty_transcript_pastes_and_saves_nothing(self, controller, speech, isolated_paths):
        controller.recorder.audio_data = speech
        controller.begin_handsfree()
        controller.finish()
        finish_transcription(controller, "")
        assert controller.pasted == [] and saved_json(isolated_paths) == []
        assert controller.recorder.wiped == 1 and controller.state == W.IDLE

    def test_rejected_cleanup_info_is_handled(self, controller, speech):
        controller.recorder.audio_data = speech
        controller.begin_handsfree()
        controller.finish()
        finish_transcription(controller, "raw text", info={"model": "g", "applied": False, "ms": 300,
                                                           "rejected": "invented words: x"})
        assert controller.pasted == ["raw text"]

    def test_cleanup_used_when_enabled(self, controller):
        controller.begin_handsfree()
        controller.finish()
        assert controller.transcriber.calls[-1][2] == controller.cleaner.clean

    def test_cleanup_skipped_when_disabled(self, controller):
        controller.settings.cleanup = False
        controller.begin_handsfree()
        controller.finish()
        assert controller.transcriber.calls[-1][2] is None

    def test_transcriber_gets_the_recorded_audio(self, controller, speech):
        controller.recorder.audio_data = speech
        controller.begin_handsfree()
        controller.finish()
        assert controller.transcriber.calls[-1][0] is speech


class TestSaving:
    def test_incognito_saves_nothing(self, controller, speech, isolated_paths):
        controller.settings.incognito = True
        controller.recorder.audio_data = speech
        controller.begin_handsfree()
        controller.finish()
        finish_transcription(controller)
        assert saved_json(isolated_paths) == [] and controller.pasted == ["Hello world."]

    def test_cancelled_recording_saved_on_expiry(self, controller, speech, clock, isolated_paths):
        controller.recorder.audio_data = speech
        controller.begin_handsfree()
        controller.cancel()
        controller._run_due(clock.now + W.TOAST_SECONDS)
        (meta,) = saved_json(isolated_paths)
        assert meta["status"] == "cancelled" and meta["pasted_into"] is None

    def test_short_audio_not_saved(self, controller, isolated_paths):
        controller.recorder.audio_data = np.full(1000, 0.5, np.float32)  # 62 ms
        controller.begin_handsfree()
        controller._save(storage.PASTED, "hi")
        assert saved_json(isolated_paths) == []

    def test_nothing_saved_before_any_recording(self, controller, speech, isolated_paths):
        controller.recorder.audio_data = speech
        controller._save(storage.PASTED, "hi")  # rec_started_at is None
        assert saved_json(isolated_paths) == []

    def test_disk_errors_never_break_dictation(self, controller, speech, monkeypatch, capsys):
        def boom(*a, **kw):
            raise OSError("disk full")

        monkeypatch.setattr(W.storage, "save_recording", boom)
        controller.recorder.audio_data = speech
        controller.begin_handsfree()
        controller.finish()
        finish_transcription(controller)
        assert controller.pasted == ["Hello world."] and controller.state == W.IDLE
        assert "could not save recording" in capsys.readouterr().err

    def test_note_context_records_app_only(self, controller):
        controller._note_context()
        assert controller.rec_recorded_in["url"] is None and controller.rec_started_at is not None


# --- Meeting --------------------------------------------------------------------------------

class TestMeeting:
    def test_note_button_starts_meeting(self, controller):
        controller.set_state(W.HOVER)
        click(controller, "note")
        assert controller.state == W.MEETING

    def test_short_meeting_asks_started_by_mistake(self, controller, clock):
        controller.begin_meeting()
        clock.advance(W.MIN_MEETING_SECONDS - 1)
        controller.stop_meeting()
        assert controller.state == W.MISTAKE

    def test_long_meeting_ends_normally(self, controller, clock):
        controller.begin_meeting()
        clock.advance(W.MIN_MEETING_SECONDS)
        controller.stop_meeting()
        assert controller.state == W.IDLE

    @pytest.mark.parametrize("button", ["close", "discard", "keep"])
    def test_mistake_card_buttons_dismiss(self, controller, clock, button):
        controller.begin_meeting()
        controller.stop_meeting()
        click(controller, button)
        assert controller.state == W.IDLE

    def test_stop_button(self, controller, clock):
        controller.begin_meeting()
        clock.advance(30)
        click(controller, "stop")
        assert controller.state == W.IDLE


# --- Mouse ----------------------------------------------------------------------------------

class TestMouse:
    @pytest.mark.parametrize("state", ALL_STATES)
    def test_hit_finds_each_interactive_element(self, controller, state):
        controller.state = state
        controller.setup_error = "offline"  # make retry clickable too
        for name in W.layout(state).interactive:
            assert controller.hit(*center(controller, name)) == name

    def test_hit_outside_everything(self, controller):
        controller.state = W.HANDSFREE
        assert controller.hit(1, 1) is None

    def test_retry_only_clickable_after_failure(self, controller):
        controller.state = W.SETUP
        xy = center(controller, "retry")
        assert controller.hit(*xy) is None
        controller.setup_error = "offline"
        assert controller.hit(*xy) == "retry"

    def test_mic_click_starts_handsfree(self, controller):
        controller.set_state(W.HOVER)
        click(controller, "mic")
        assert controller.state == W.HANDSFREE

    def test_mic_long_press_is_push_to_talk(self, controller, clock):
        controller.set_state(W.HOVER)
        x, y = center(controller, "mic")
        controller.mouse_down(x, y)
        controller._run_due(clock.now + W.HOLD_DELAY)
        assert controller.state == W.HOLD and controller.hold_source == "mouse"
        controller.mouse_up(x, y)
        assert controller.state == W.PROCESSING

    def test_long_press_cancelled_if_released_early(self, controller, clock):
        controller.set_state(W.HOVER)
        x, y = center(controller, "mic")
        controller.mouse_down(x, y)
        controller.mouse_up(x, y)  # quick click -> hands-free
        controller._run_due(clock.now + 5)
        assert controller.state == W.HANDSFREE

    def test_release_on_different_element_does_nothing(self, controller):
        controller.set_state(W.HOVER)
        controller.mouse_down(*center(controller, "mic"))
        controller.mouse_up(*center(controller, "note"))
        assert controller.state == W.HOVER

    def test_press_on_nothing_does_nothing(self, controller):
        controller.set_state(W.HOVER)
        controller.mouse_down(1, 1)
        controller.mouse_up(1, 1)
        assert controller.state == W.HOVER

    def test_cancel_and_finish_buttons(self, controller):
        controller.begin_handsfree()
        click(controller, "finish")
        assert controller.state == W.PROCESSING
        controller.state = W.IDLE
        controller.begin_handsfree()
        click(controller, "cancel")
        assert controller.state == W.CANCELLED

    def test_wave_zone_is_not_a_button(self, controller):
        controller.begin_handsfree()
        click(controller, "wave")
        assert controller.state == W.HANDSFREE


# --- First-run setup ----------------------------------------------------------------------------

class TestSetupFlow:
    @pytest.fixture
    def installs(self, monkeypatch):
        calls = []
        monkeypatch.setattr(W.setup, "install_async", lambda p, d, e: calls.append((p, d, e)))
        return calls

    def test_run_setup_resets_and_starts_download(self, controller, installs):
        controller.setup_error, controller.setup_progress = "old", 0.7
        controller._run_setup()
        assert controller.setup_error is None and controller.setup_progress == 0.0 and len(installs) == 1

    def test_progress_is_stored(self, controller):
        controller._setup_progress(0.42)
        assert controller.setup_progress == 0.42

    def test_done_loads_engines_and_unlocks(self, controller):
        controller.state = W.SETUP
        controller._setup_done()
        assert controller.state == W.IDLE
        assert controller.transcriber.loaded == 1 and controller.cleaner.loaded == 1

    def test_failure_shows_retry_and_stays_locked(self, controller, capsys):
        controller.state = W.SETUP
        controller._setup_failed("network unreachable")
        assert controller.state == W.SETUP and controller.setup_error == "network unreachable"
        assert "model download failed" in capsys.readouterr().err

    def test_retry_only_after_failure(self, controller, installs):
        controller._retry_setup()
        assert installs == []
        controller.setup_error = "offline"
        controller._retry_setup()
        assert len(installs) == 1

    def test_retry_button_click(self, controller, installs):
        controller.state, controller.setup_error = W.SETUP, "offline"
        click(controller, "retry")
        assert len(installs) == 1

    def test_dictation_locked_during_setup(self, controller):
        controller.state = W.SETUP
        controller.fn_down()
        assert controller.state == W.SETUP and controller.recorder.started == 0

    def test_load_engines(self, controller):
        controller._load_engines()
        assert controller.transcriber.loaded == 1 and controller.cleaner.loaded == 1


# --- Waveform levels ------------------------------------------------------------------------------

class TestLevels:
    def test_idle_levels_decay_to_zero(self, controller):
        controller.bar_levels[11] = [1.0] * 11
        for _ in range(60):
            controller._update_levels(0)
        assert max(controller.bar_levels[11]) < 0.01

    def test_recording_uses_mic_level_center_weighted(self, controller):
        controller.state = W.HOLD
        controller.recorder._level = 1.0
        for _ in range(60):
            controller._update_levels(0)
        bars = controller.bar_levels[11]
        assert bars[5] > bars[0] and bars[5] > 0.4 and all(0 <= b <= 1 for b in bars)

    def test_meeting_uses_meeting_source(self, controller):
        controller.state = W.MEETING
        controller.meeting_levels = type("L", (), {"level": lambda self, t: 1.0})()
        for _ in range(60):
            controller._update_levels(0)
        assert controller.bar_levels[5][2] > 0.4

    def test_bar_counts(self, controller):
        assert len(controller.bar_levels[11]) == 11 and len(controller.bar_levels[5]) == 5


# --- Logging --------------------------------------------------------------------------------------

class TestLog:
    def test_silent_by_default(self, monkeypatch, capsys):
        monkeypatch.setattr(W, "DEBUG", False)
        W.log("hello")
        assert capsys.readouterr().err == ""

    def test_debug_prints_timestamped(self, monkeypatch, capsys):
        monkeypatch.setattr(W, "DEBUG", True)
        W.log("hello")
        err = capsys.readouterr().err
        assert err.endswith("hello\n") and err[0] == "[" and err[13] == "]"  # [HH:MM:SS.mmm]


# --- Rendering smoke tests (every state draws into a real bitmap) -------------------------------------

class TestDraw:
    @pytest.mark.parametrize("state", ALL_STATES)
    @pytest.mark.parametrize("hovered", [None, "first"])
    def test_every_state_renders(self, controller, bitmap_context, state, hovered):
        controller.state = state
        controller.shape = W.layout(state).bg.values()
        controller.content_a = 1.0
        interactive = W.layout(state).interactive
        controller.hovered = interactive[0] if (hovered and interactive) else None
        tip = W.TOOLTIPS.get((state, controller.hovered))
        if tip:
            controller.tip, controller.tip_a = (tip, W.layout(state).elems[controller.hovered]), 1.0
        controller.setup_error = "offline" if hovered else None
        controller.draw()  # must not raise

    def test_hidden_draws_nothing(self, controller, bitmap_context):
        controller.fullscreen = True
        controller.draw()
        assert bitmap_context(100, 18)[3] == 0.0


# =========================================================================================
# Added after mutation testing: specification, snapshots, side effects, and the UI glue.
# =========================================================================================

from datetime import datetime  # noqa: E402

from conftest import FakeScreen, render  # noqa: E402


class TestSpecification:
    """Product decisions, asserted as literal values (not compared to themselves)."""

    def test_fn_timing(self):
        assert (W.FN_TAP_MAX, W.DOUBLE_TAP_WINDOW, W.HOLD_DELAY) == (0.3, 1.0, 0.3)

    def test_undo_window_and_meeting_guard(self):
        assert (W.TOAST_SECONDS, W.MIN_MEETING_SECONDS) == (5.0, 10)

    def test_handsfree_keys(self):
        assert (W.KEY_SPACE, W.KEY_RETURN, W.KEY_KEYPAD_ENTER, W.KEY_DELETE) == (49, 36, 76, 51)

    def test_panel_and_animation(self):
        assert (W.VIEW_W, W.VIEW_H, W.BASE, W.FPS) == (480, 220, 18, 60)
        assert (W.MORPH, W.SCREEN_POLL_SECONDS) == (0.3, 0.5)

    def test_tooltip_copy(self):
        assert W.TOOLTIPS == {
            (W.HOVER, "mic"): [("Dictate ", False), ("fn", True)],
            (W.HOVER, "note"): [("New note ", False), ("⌥M", True)],
            (W.HANDSFREE, "cancel"): [("Cancel", False)],
            (W.HANDSFREE, "finish"): [("Finish and paste", False)],
            (W.HANDSFREE, "wave"): [("space", True), (" to paste · ", False), ("fn", True), (" to cancel", False)],
        }

    def test_icons(self):
        assert W.NOTE_ICON == "record.circle"
        assert W.WARNING_YELLOW == (0.96, 0.77, 0.26)

    def test_state_names_are_stable(self):
        # Used in logs and (later) persisted UI state.
        assert ALL_STATES == ["idle", "hover", "hold", "handsfree", "processing", "cancelled",
                              "meeting", "mistake", "setup"]
        assert W.RECORDING_STATES == ("hold", "handsfree", "meeting")


class TestLayoutSnapshot:
    def test_every_state_matches_golden_geometry(self, golden_json):
        def rect(r):
            return [r.x, r.y, r.w, r.h]

        snapshot = {}
        for state in ALL_STATES:
            lay = W.layout(state)
            snapshot[state] = {
                "bg": {"rect": rect(lay.bg.rect), "radius": lay.bg.radius, "fill": lay.bg.fill, "stroke": lay.bg.stroke},
                "elems": {name: rect(r) for name, r in lay.elems.items()},
                "interactive": list(lay.interactive),
            }
        golden_json("widget_layouts", snapshot)


class TestInitialState:
    def test_defaults(self, controller, clock):
        c = controller
        assert (c.state, c.seq, c.state_since, c.meeting_started) == (W.IDLE, 0, clock.now, 0.0)
        assert c.pending == [] and c.pressed is None and c.hovered is None
        assert (c.suppress_hover, c.accepting_mouse, c.fullscreen) == (False, False, False)
        assert (c.screen_frame, c.next_screen_poll) == (None, 0.0)
        assert c.shape == W.layout(W.IDLE).bg.values()
        assert (c.content_a, c.tip_a, c.tip) == (1.0, 0.0, None)
        assert c.bar_levels == {11: [0.0] * 11, 5: [0.0] * 5}
        assert (c.setup_progress, c.setup_error) == (0.0, None)
        assert (c.rec_started_at, c.rec_ended_at, c.rec_recorded_in) == (None, None, None)
        assert (c.hold_source, c.fn_press_at, c.fn_consumed, c.last_tap_at) == (None, 0.0, False, None)


class TestSoundCues:
    """SpySounds records every cue, so each gesture's audible feedback is pinned."""

    def test_fn_hold(self, controller, clock):
        controller.fn_down()
        clock.advance(1)
        controller.fn_up()
        assert controller.sounds.played == ["start", "stop"]

    def test_double_tap_plays_start_then_lock(self, controller, clock):
        controller.fn_down(); clock.advance(0.1); controller.fn_up()
        clock.advance(0.2)
        controller.fn_down()
        assert controller.state == W.HANDSFREE and controller.sounds.played == ["start", "lock"]

    def test_no_lock_sound_if_mic_fails_on_second_tap(self, controller, clock):
        controller.fn_down(); clock.advance(0.1); controller.fn_up()
        clock.advance(0.2)
        controller.recorder.start_ok = False
        controller.fn_down()
        assert controller.state != W.HANDSFREE and controller.sounds.played == ["start", "error"]

    def test_model_download_failure_plays_error(self, controller):
        controller._setup_failed("offline")
        assert controller.sounds.played == ["error"]

    def test_quick_tap_discard_is_silent_after_start(self, controller, clock):
        controller.fn_down(); clock.advance(0.1); controller.fn_up()
        assert controller.sounds.played == ["start"]

    def test_mouse_handsfree_then_cancel(self, controller):
        controller.set_state(W.HOVER)
        click(controller, "mic")
        click(controller, "cancel")
        assert controller.sounds.played == ["start", "cancel"]

    def test_undo_and_expiry_are_silent(self, controller, clock):
        controller.begin_handsfree()
        controller.cancel()
        controller.undo_cancel()
        assert controller.sounds.played == ["start", "cancel"]

    def test_meeting(self, controller, clock):
        controller.begin_meeting()
        clock.advance(30)
        controller.stop_meeting()
        assert controller.sounds.played == ["start", "stop"]

    def test_short_meeting_still_confirms_stop(self, controller):
        controller.begin_meeting()
        controller.stop_meeting()
        assert controller.sounds.played == ["start", "stop"] and controller.state == W.MISTAKE

    def test_mic_failure_plays_error(self, controller):
        controller.recorder.start_ok = False
        controller.fn_down()
        controller.begin_handsfree()
        assert controller.sounds.played == ["error", "error"]

    def test_paste_sound_when_text_lands(self, controller):
        controller.begin_handsfree()
        controller.finish()
        controller._on_transcribed("Hello there.", "hello there", None, 1.0, "finished")
        assert controller.pasted == ["Hello there."] and controller.sounds.played == ["start", "stop", "paste"]

    def test_alert_when_nothing_was_heard(self, controller):
        controller.begin_handsfree()
        controller.finish()
        controller._on_transcribed("", "", None, 1.0, "finished")
        assert controller.pasted == [] and controller.sounds.played == ["start", "stop", "alert"]

    def test_quick_tap_does_not_alert(self, controller, clock):
        controller.fn_down(); clock.advance(0.1); controller.fn_up()
        clock.advance(5)
        assert "alert" not in controller.sounds.played

    def test_models_installed_plays_success(self, controller):
        controller._setup_done()
        assert controller.sounds.played == ["success"]


class TestStateMachineDetails:
    def test_tap_threshold_is_exclusive(self, controller, clock):
        clock.now = 0.0  # exact float arithmetic at the boundary
        controller.fn_down()
        clock.now = W.FN_TAP_MAX
        controller.fn_up()
        assert controller.state == W.PROCESSING  # exactly 0.3 s is a hold, not a tap

    @pytest.mark.parametrize("samples,saved", [(4799, False), (4800, True)])
    def test_save_minimum_length_boundary(self, controller, isolated_paths, samples, saved):
        controller.recorder.audio_data = np.full(samples, 0.5, np.float32)
        controller.begin_handsfree()
        controller._save(storage.PASTED, "hi")
        assert bool(saved_json(isolated_paths)) is saved

    def test_saved_times_are_recording_start_and_stop(self, controller, speech, isolated_paths):
        controller.recorder.audio_data = speech
        controller.begin_handsfree()
        controller.rec_started_at = datetime(2026, 9, 30, 12, 0, 0, 0)
        controller._stop_recording()
        controller.rec_ended_at = datetime(2026, 9, 30, 12, 0, 7, 250000)
        controller._save(storage.PASTED, "hi")
        (meta,) = saved_json(isolated_paths)
        assert meta["started_at"].startswith("2026-09-30T12:00:00.000")
        assert meta["ended_at"].startswith("2026-09-30T12:00:07.250")

    def test_missing_end_time_falls_back_to_now(self, controller, speech, isolated_paths):
        controller.recorder.audio_data = speech
        controller.begin_handsfree()
        controller.rec_ended_at = None
        controller._save(storage.PASTED, "hi")
        (meta,) = saved_json(isolated_paths)
        assert meta["ended_at"] >= meta["started_at"]

    def test_superseded_cancel_is_saved_before_new_recording(self, controller, speech, isolated_paths):
        controller.recorder.audio_data = speech
        controller.begin_handsfree()
        controller.cancel()
        controller.set_state(W.CANCELLED)
        controller.begin_handsfree()  # new hands-free recording replaces the toast
        (meta,) = saved_json(isolated_paths)
        assert meta["status"] == "cancelled" and controller.state == W.HANDSFREE

    def test_hold_records_where_dictation_started(self, controller):
        controller.begin_hold("fn")
        assert controller.rec_recorded_in == {"app": "TestApp", "bundle_id": "com.test.app", "url": None,
                                              "page_title": None}
        assert controller.rec_started_at is not None and controller.rec_ended_at is None

    def test_discard_stops_the_mic(self, controller):
        controller.begin_hold("fn")
        stops = controller.recorder.stopped
        controller.discard_quietly()
        assert controller.recorder.stopped == stops + 1

    def test_long_press_ignored_if_released_outside(self, controller, clock):
        controller.set_state(W.HOVER)
        controller.mouse_down(*center(controller, "mic"))
        controller.mouse_up(1, 1)  # dragged off the button
        controller._run_due(clock.now + W.HOLD_DELAY)
        assert controller.state == W.HOVER and controller.recorder.started == 0

    def test_long_press_only_on_mic(self, controller, clock):
        controller.set_state(W.HOVER)
        controller.mouse_down(*center(controller, "note"))
        assert controller.pending == []

    def test_long_press_ignored_after_state_change(self, controller, clock):
        controller.set_state(W.HOVER)
        controller.mouse_down(*center(controller, "mic"))
        maybe_hold = controller.pending[0][2]
        controller.set_state(W.IDLE)
        maybe_hold()  # even if it ran, a state change must cancel the long-press
        assert controller.state == W.IDLE


class TestLevelsCharacterization:
    def test_envelope_snapshot(self, controller, golden_json):
        import random
        random.seed(7)
        controller.state = W.HOLD
        controller.recorder._level = 0.8
        for _ in range(5):
            controller._update_levels(0)
        golden_json("widget_bar_levels_seed7", {n: [round(v, 9) for v in arr]
                                                 for n, arr in controller.bar_levels.items()})

    def test_center_bar_tallest_edges_symmetric(self, controller, monkeypatch):
        monkeypatch.setattr(W.random, "uniform", lambda a, b: 1.0)  # remove jitter
        controller.state = W.HOLD
        controller.recorder._level = 1.0
        for _ in range(100):
            controller._update_levels(0)
        bars = controller.bar_levels[11]
        assert bars[5] == pytest.approx(1.0, abs=1e-6)
        for i in range(5):
            assert bars[i] == pytest.approx(bars[10 - i]) and bars[i] < bars[i + 1]


# --- UI glue (humble objects replaced by fakes) -----------------------------------------------

class TestPointer:
    def test_entering_idle_zone_opens_hover(self, controller, ui):
        ui.point_at(W.CX, W.BASE)
        controller._update_mouse()
        assert controller.state == W.HOVER

    def test_pointer_elsewhere_stays_idle(self, controller, ui):
        ui.point_at(W.CX + 100, W.BASE)
        controller._update_mouse()
        assert controller.state == W.IDLE

    @pytest.mark.parametrize("dx,dy,inside", [(36, 0, True), (36.4, 0, False), (-36, 0, True), (-36.4, 0, False),
                                              (0, 17, True), (0, 17.4, False), (0, -17, True), (0, -17.4, False)])
    def test_idle_hover_zone_edges(self, controller, ui, dx, dy, inside):
        ui.point_at(W.CX + dx, W.BASE + dy)  # zone is 72 x 34 around the pill
        controller._update_mouse()
        assert (controller.state == W.HOVER) is inside

    def test_suppressed_until_pointer_leaves(self, controller, ui):
        controller.suppress_hover = True
        ui.point_at(W.CX, W.BASE)
        controller._update_mouse()
        assert controller.state == W.IDLE and controller.suppress_hover is True
        ui.point_at(W.CX + 200, W.BASE)
        controller._update_mouse()
        assert controller.suppress_hover is False
        ui.point_at(W.CX, W.BASE)
        controller._update_mouse()
        assert controller.state == W.HOVER

    def test_leaving_buttons_closes_hover(self, controller, ui):
        controller.set_state(W.HOVER)
        ui.point_at(W.CX + 150, W.BASE)
        controller._update_mouse()
        assert controller.state == W.IDLE

    def test_hover_has_a_ten_point_grace_margin(self, controller, ui):
        controller.set_state(W.HOVER)
        lay = W.layout(W.HOVER)
        zone = lay.elems["mic"].union(lay.elems["note"])
        ui.point_at(zone.right + 9, zone.cy)
        controller._update_mouse()
        assert controller.state == W.HOVER
        ui.point_at(zone.right + 11, zone.cy)
        controller._update_mouse()
        assert controller.state == W.IDLE

    def test_hover_kept_while_button_pressed(self, controller, ui):
        controller.set_state(W.HOVER)
        controller.pressed = "mic"
        ui.point_at(W.CX + 150, W.BASE)
        controller._update_mouse()
        assert controller.state == W.HOVER

    def test_hidden_widget_ignores_pointer(self, controller, ui):
        controller.fullscreen = True
        ui.point_at(W.CX, W.BASE)
        controller._update_mouse()
        assert controller.state == W.IDLE and controller.hovered is None

    def test_accepts_clicks_only_over_buttons(self, controller, ui):
        controller.set_state(W.HOVER)
        ui.point_at(*center(controller, "mic"))
        controller._update_mouse()
        assert controller.hovered == "mic" and ui.panel.ignores_mouse == [False]
        ui.point_at(*center(controller, "note"))
        controller._update_mouse()
        assert ui.panel.ignores_mouse == [False]  # unchanged: no redundant calls
        ui.point_at(W.CX + 150, W.BASE + 80)
        controller._update_mouse()
        assert ui.panel.ignores_mouse == [False, True]

    def test_pressed_button_keeps_accepting_clicks(self, controller, ui):
        controller.state, controller.pressed = W.HOLD, "mic"
        ui.point_at(1, 1)
        controller._update_mouse()
        assert ui.panel.ignores_mouse == [False]

    def test_pointer_coordinates_are_panel_relative(self, controller, ui):
        ui.panel.origin = (500.0, 300.0)
        controller.set_state(W.HOVER)
        ui.point_at(*center(controller, "note"))
        controller._update_mouse()
        assert controller.hovered == "note"


class TestScreenFollowing:
    def test_panel_centered_on_visible_frame_bottom(self, controller, ui):
        ui.set_screen(FakeScreen(x=100, y=80, w=1000, h=700))
        controller._poll_screen()
        assert ui.panel.frames == [(100 + 500 - 240, 80, 480, 220)]
        assert controller.screen_frame == (360, 80)

    def test_not_moved_when_unchanged(self, controller, ui):
        controller._poll_screen()
        assert ui.panel.frames == []

    def test_force_always_repositions(self, controller, ui):
        controller._poll_screen(force=True)
        assert len(ui.panel.frames) == 1

    def test_moves_to_new_screen(self, controller, ui):
        ui.set_screen(FakeScreen(x=1512, y=0, w=1920, h=1050))
        controller._poll_screen()
        assert ui.panel.frames[-1] == (1512 + 960 - 240, 0, 480, 220)

    def test_records_fullscreen(self, controller, ui):
        ui.set_screen(FakeScreen(), fullscreen=True)
        controller._poll_screen()
        assert controller.fullscreen is True


class TestFrameLoop:
    def test_tick_runs_due_callbacks(self, controller, ui, clock):
        ran = []
        controller.after(0, lambda: ran.append(1))
        controller.tick()
        assert ran == [1]

    def test_screen_polled_on_cadence(self, controller, ui, clock):
        controller.tick()
        assert controller.next_screen_poll == clock.now + 0.5
        ui.set_screen(FakeScreen(x=1512, y=0, w=1920, h=1050))
        clock.advance(0.49)
        controller.tick()
        assert ui.panel.frames == []  # not polled yet
        clock.advance(0.01)
        controller.tick()
        assert len(ui.panel.frames) == 1  # polled at 0.5 s and moved

    def test_shape_eases_thirty_percent_toward_target(self, controller, ui):
        start = controller.shape[:]
        controller.set_state(W.HANDSFREE)
        controller.tick()
        target = W.layout(W.HANDSFREE).bg.values()
        assert controller.shape == pytest.approx([s + (t - s) * 0.3 for s, t in zip(start, target)])

    def test_content_fades_in(self, controller, ui):
        controller.set_state(W.HANDSFREE)  # a state the pointer position can't change
        controller.tick()
        assert controller.content_a == pytest.approx(0.25)
        controller.tick()
        assert controller.content_a == pytest.approx(0.4375)

    def test_tooltip_follows_hovered_element(self, controller, ui):
        controller.set_state(W.HOVER)
        ui.point_at(*center(controller, "mic"))
        controller.tick()
        parts, anchor = controller.tip
        assert parts == W.TOOLTIPS[(W.HOVER, "mic")] and anchor == W.layout(W.HOVER).elems["mic"]
        assert controller.tip_a == pytest.approx(0.3)

    def test_tooltip_fades_out_but_keeps_content(self, controller, ui):
        controller.set_state(W.HOVER)
        ui.point_at(*center(controller, "mic"))
        controller.tick()
        ui.point_at(W.CX + 36, W.BASE + 60)  # inside hover grace margin, over no button
        controller.tick()
        assert controller.tip is not None and controller.tip_a == pytest.approx(0.3 * 0.7)

    def test_every_tick_redraws(self, controller, ui):
        controller.tick()
        controller.tick()
        assert ui.view.redraws == [True, True]

    def test_tick_animates_waveform(self, controller, ui):
        controller.state = W.HOLD
        controller.recorder._level = 1.0
        controller.tick()
        assert controller.bar_levels[11][5] > 0.1


class TestStart:
    @pytest.fixture
    def appkit(self, monkeypatch):
        """Fake NSPanel / NSTimer / NSRunLoop so start() builds nothing on screen."""
        made = {}

        class Panel:
            @classmethod
            def alloc(cls):
                return cls()

            def initWithContentRect_styleMask_backing_defer_(self, rect, mask, backing, defer):
                made["panel"] = self
                self.cfg = {"rect": (rect.size.width, rect.size.height), "mask": mask}
                self.calls = []
                return self

            def __getattr__(self, name):  # record every configuration call in order
                return lambda *args: self.calls.append((name, args))

            def frame(self):
                from AppKit import NSMakeRect
                return NSMakeRect(0, 0, 480, 220)

        class Timer:
            @staticmethod
            def timerWithTimeInterval_target_selector_userInfo_repeats_(interval, target, sel, info, repeats):
                made["timer"] = (interval, target, sel, repeats)
                return "TIMER"

        class RunLoop:
            @staticmethod
            def currentRunLoop():
                return RunLoop()

            def addTimer_forMode_(self, timer, mode):
                made["runloop"] = (timer, mode)

        monkeypatch.setattr(W, "NSPanel", Panel)
        monkeypatch.setattr(W, "NSTimer", Timer)
        monkeypatch.setattr(W, "NSRunLoop", RunLoop)
        monkeypatch.setattr(W, "active_screen", lambda: (FakeScreen(), False))
        return made

    def test_panel_configuration(self, controller, appkit, monkeypatch):
        monkeypatch.setattr(W.setup, "missing", lambda: [])
        controller.start()
        p = appkit["panel"]
        assert p.cfg == {"rect": (480, 220), "mask": W.NSWindowStyleMaskBorderless | W.NSWindowStyleMaskNonactivatingPanel}
        names = [n for n, _ in p.calls]
        # Level must be set after setFloatingPanel_ (which resets it).
        assert names.index("setFloatingPanel_") < names.index("setLevel_")
        calls = dict(p.calls)
        assert calls["setFloatingPanel_"] == (True,)
        assert calls["setLevel_"] == (W.NSStatusWindowLevel,)
        assert calls["setBackgroundColor_"] == (W.NSColor.clearColor(),)
        assert calls["setContentView_"] == (controller.view,)
        f = controller.view.frame()
        assert (f.origin.x, f.origin.y, f.size.width, f.size.height) == (0, 0, W.VIEW_W, W.VIEW_H)
        assert calls["setOpaque_"] == (False,) and calls["setHasShadow_"] == (False,)
        assert calls["setHidesOnDeactivate_"] == (False,) and calls["setIgnoresMouseEvents_"] == (True,)
        assert calls["setCollectionBehavior_"] == (
            W.NSWindowCollectionBehaviorCanJoinAllSpaces | W.NSWindowCollectionBehaviorStationary
            | W.NSWindowCollectionBehaviorFullScreenAuxiliary | W.NSWindowCollectionBehaviorIgnoresCycle,)
        assert "orderFrontRegardless" in names and "setFrame_display_" in names
        assert controller.view.ctrl is controller

    def test_frame_timer_at_60fps_in_common_modes(self, controller, appkit, monkeypatch):
        monkeypatch.setattr(W.setup, "missing", lambda: [])
        controller.start()
        interval, target, sel, repeats = appkit["timer"]
        assert interval == pytest.approx(1 / 60) and sel == "tick:" and repeats is True
        assert target.callback == controller.tick
        assert appkit["runloop"] == ("TIMER", W.NSRunLoopCommonModes)

    def test_models_present_loads_engines(self, controller, appkit, monkeypatch):
        monkeypatch.setattr(W.setup, "missing", lambda: [])
        controller.start()
        assert controller.state == W.IDLE and controller.recorder.prepared == 1
        assert controller.transcriber.loaded == 1 and controller.cleaner.loaded == 1

    def test_missing_models_enter_mandatory_setup(self, controller, appkit, monkeypatch):
        monkeypatch.setattr(W.setup, "missing", lambda: [W.DEFAULT_MODEL])
        installs = []
        monkeypatch.setattr(W.setup, "install_async", lambda *a: installs.append(a))
        controller.start()
        assert controller.state == W.SETUP and len(installs) == 1
        assert controller.transcriber.loaded == 0  # engines wait for the download


class TestObjCBridges:
    def test_view_contract(self, controller):
        from AppKit import NSMakeRect
        view = W.WidgetView.alloc().initWithFrame_(NSMakeRect(0, 0, W.VIEW_W, W.VIEW_H))
        assert view.isFlipped() is False  # y grows upward, matching the layout maths
        assert view.acceptsFirstMouse_(None) is True  # first click works without activating

    def test_view_forwards_mouse_in_view_coordinates(self, controller):
        from AppKit import NSMakePoint, NSMakeRect
        view = W.WidgetView.alloc().initWithFrame_(NSMakeRect(0, 0, W.VIEW_W, W.VIEW_H))
        seen = []
        view.ctrl = type("Ctrl", (), {"mouse_down": lambda s, x, y: seen.append(("down", x, y)),
                                      "mouse_up": lambda s, x, y: seen.append(("up", x, y))})()
        event = type("Ev", (), {"locationInWindow": lambda s: NSMakePoint(12.5, 34.0)})()
        view.mouseDown_(event)
        view.mouseUp_(event)
        assert seen == [("down", 12.5, 34.0), ("up", 12.5, 34.0)]

    def test_ticker_forwards_to_callback(self):
        ticks = []
        t = W.Ticker.alloc().init()
        t.callback = lambda: ticks.append(1)
        t.tick_(None)
        assert ticks == [1]


# --- Golden images of every widget state -------------------------------------------------------

def _prepare_render(controller, state, hovered=None, error=None):
    controller.state = state
    controller.shape = W.layout(state).bg.values()
    controller.content_a = 1.0
    controller.hovered = hovered
    controller.setup_error = error
    controller.setup_progress = 0.42
    controller.state_since = controller.state_since  # fake clock: toast bar is deterministic
    for n, arr in controller.bar_levels.items():
        mid = (n - 1) / 2
        arr[:] = [0.9 * (1 - abs(i - mid) / (mid + 1)) for i in range(n)]
    tip = W.TOOLTIPS.get((state, hovered))
    controller.tip, controller.tip_a = ((tip, W.layout(state).elems[hovered]), 1.0) if tip else (None, 0.0)


RENDER_CASES = [(s, None, None) for s in ALL_STATES] + [
    (W.HOVER, "mic", None), (W.HOVER, "note", None), (W.HANDSFREE, "cancel", None),
    (W.HANDSFREE, "finish", None), (W.HANDSFREE, "wave", None), (W.CANCELLED, "undo", None),
    (W.MEETING, "stop", None), (W.MISTAKE, "keep", None), (W.SETUP, "retry", "offline"),
]


@pytest.mark.parametrize("state,hovered,error", RENDER_CASES)
def test_state_matches_golden_image(controller, clock, golden_image, state, hovered, error):
    _prepare_render(controller, state, hovered, error)
    clock.advance(2.0)  # 2 s into the Undo countdown; spinner phase fixed by the fake clock
    pixels, rep = render(controller.draw, W.VIEW_W, W.VIEW_H)
    golden_image(f"widget_{state}_{hovered or 'plain'}", pixels, rep)


class TestDebugLog:
    def test_env_var_switches_debug_on_only_for_1(self):
        import os
        import subprocess
        import sys
        code = "import mispr.widget as W; print(W.DEBUG)"
        def debug_with(value):
            env = {k: v for k, v in os.environ.items() if k != "MISPR_DEBUG"}
            if value is not None:
                env["MISPR_DEBUG"] = value
            out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
            return out.stdout.strip().splitlines()[-1]
        assert debug_with("1") == "True"
        assert debug_with("0") == "False" and debug_with(None) == "False"

    def test_fn_up_logs_how_long_fn_was_held(self, controller, clock, monkeypatch, capsys):
        monkeypatch.setattr(W, "DEBUG", True)
        controller.fn_down()
        clock.advance(1.5)
        controller.fn_up()
        assert "fn up (held 1.50s)" in capsys.readouterr().err

    def test_consumed_fn_up_logs_plainly(self, controller, clock, monkeypatch, capsys):
        monkeypatch.setattr(W, "DEBUG", True)
        controller.begin_handsfree()
        controller.fn_down()  # cancels; this press is consumed
        controller.fn_up()
        assert "fn up\n" in capsys.readouterr().err


# --- Mic notice (first dictation after launch) ------------------------------------------------

class TestMicNotice:
    @pytest.mark.parametrize("name,built_in,text", [
        ("MacBook Pro Microphone", True, "Using Built-in mic (recommended)"),
        ("AirPods Pro", False, "Using AirPods Pro"),
        (None, False, None),
    ])
    def test_wording(self, name, built_in, text):
        assert W.mic_notice_text(name, built_in) == text

    def test_duration_spec(self):
        assert W.MIC_NOTICE_SECONDS == 3.0

    def test_shown_on_first_dictation_only(self, controller, clock):
        controller.fn_down()
        assert controller.mic_notice == ("Using Built-in mic (recommended)", clock.now)
        clock.advance(1)
        controller.fn_up()
        clock.advance(10)
        controller.state = W.IDLE
        first = controller.mic_notice
        controller.fn_down()
        assert controller.mic_notice == first  # not re-armed for the second dictation

    def test_also_on_first_handsfree_or_mouse_recording(self, controller, clock):
        controller.begin_handsfree()
        assert controller.mic_notice is not None

    def test_skipped_when_there_is_no_mic_name(self, controller, monkeypatch):
        monkeypatch.setattr(W.audio, "input_device", lambda: (None, False))
        controller.begin_hold("fn")
        assert controller.mic_notice is None

    @pytest.mark.parametrize("elapsed,alpha", [(0.0, 1.0), (2.6, 1.0), (2.8, 0.5), (3.0, 0.0), (9.0, 0.0)])
    def test_visible_for_three_seconds_then_fades(self, controller, clock, elapsed, alpha):
        controller.begin_hold("fn")
        clock.advance(elapsed)
        assert controller._mic_notice_alpha() == pytest.approx(alpha)

    @pytest.mark.parametrize("state", [W.IDLE, W.HOVER, W.PROCESSING, W.CANCELLED, W.MEETING])
    def test_only_while_recording(self, controller, state):
        controller.begin_hold("fn")
        controller.state = state
        assert controller._mic_notice_alpha() == 0.0

    def test_takes_priority_over_tooltips(self, controller, bitmap_context, monkeypatch):
        drawn = []
        monkeypatch.setattr(controller, "_draw_mic_notice", lambda bg, a: drawn.append(a))
        controller.begin_handsfree()
        controller.tip, controller.tip_a = (W.TOOLTIPS[(W.HANDSFREE, "wave")], W.layout(W.HANDSFREE).elems["wave"]), 1.0
        controller._draw_tooltip(W.layout(W.HANDSFREE).bg.rect)
        assert drawn == [1.0]


def test_mic_notice_matches_golden_image(controller, clock, golden_image):
    controller.begin_hold("fn")
    _prepare_render(controller, W.HOLD)
    pixels, rep = render(controller.draw, W.VIEW_W, W.VIEW_H)
    golden_image("widget_hold_mic_notice", pixels, rep)
