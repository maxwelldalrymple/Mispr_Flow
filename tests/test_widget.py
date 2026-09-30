import json

import numpy as np
import pytest
from PyObjCTools import AppHelper

import whispr.widget as W
from whispr import storage
from whispr.draw import Rect

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
