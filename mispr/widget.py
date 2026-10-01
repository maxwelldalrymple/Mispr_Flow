"""The floating dictation widget that sits just above the Dock.

States (see README / PLAN for the full behaviour):

    IDLE        tiny outlined pill
    HOVER       mic button + note (◉) button, with tooltips
    HOLD        push-to-talk recording: compact pill with live waveform
    HANDSFREE   toggle recording: ✕ · waveform · ✓
    PROCESSING  transcribing: dim waveform + spinner
    CANCELLED   "Transcript cancelled · Undo" toast with a draining progress bar
    MEETING     notetaker running: outlined pill with waveform + ■ stop
    MISTAKE     "Started by mistake?" card (Discard / Keep)
    SETUP       first-run model download with progress (mandatory; dictation is off until done)

Dictation is driven by the `fn` key (hold = push-to-talk, double-tap within 1 s =
hands-free; then space/return pastes and fn/delete cancels) or by clicking the widget. The waveform shows the
live microphone level. PROCESSING transcribes locally with whisper.cpp and pastes into
the focused app. The meeting notetaker is still a stub with a simulated waveform.
"""

import math
import os
from datetime import datetime
import random
import sys
import time
from dataclasses import dataclass, field

import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSColor,
    NSCompositingOperationCopy,
    NSEvent,
    NSFontWeightBold,
    NSFontWeightSemibold,
    NSMakeRect,
    NSPanel,
    NSRectFillUsingOperation,
    NSRunLoop,
    NSRunLoopCommonModes,
    NSStatusWindowLevel,
    NSTimer,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorIgnoresCycle,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from Foundation import NSObject
from PyObjCTools import AppHelper

from . import apps, audio, context, draw, prompts, settings, setup, sounds, storage
from .draw import Rect, white
from .audio import Recorder
from .cleanup import Cleaner
from .models import DEFAULT_MODEL
from .paste import ENTER_DELAY, copy_text, paste_text, press_enter, type_text
from .transcribe import Transcriber
from .levels import FakeLevelSource
from .screens import active_screen

IDLE = "idle"
HOVER = "hover"
HOLD = "hold"
HANDSFREE = "handsfree"
PROCESSING = "processing"
CANCELLED = "cancelled"
MEETING = "meeting"
MISTAKE = "mistake"
SETUP = "setup"

RECORDING_STATES = (HOLD, HANDSFREE, MEETING)

# Canvas: a transparent panel centred above the Dock; everything is drawn inside it.
VIEW_W, VIEW_H = 480, 220
CX = VIEW_W / 2
BASE = 18  # centre line of the pill, in points above the bottom of the visible frame

FPS = 60
MORPH = 0.3  # per-frame easing factor toward the target shape
HOLD_DELAY = 0.3  # long-press on the mic longer than this = push-to-talk
FN_TAP_MAX = 0.3  # an fn press shorter than this is a tap, not push-to-talk
DOUBLE_TAP_WINDOW = 1.0  # two fn taps starting within this many seconds = hands-free

# Hands-free keyboard shortcuts (macOS virtual keycodes).
KEY_SPACE = 49  # finish and paste
KEY_RETURN = 36  # finish and paste
KEY_KEYPAD_ENTER = 76  # finish and paste
KEY_DELETE = 51  # cancel
TOAST_SECONDS = 5.0  # how long Undo stays available (the audio is held until then)
MIN_MEETING_SECONDS = 10  # stand-in for "only a few words were captured"
SCREEN_POLL_SECONDS = 0.5

MIC_NOTICE_SECONDS = 3.0  # "Using Built-in mic" shows on the first dictation after launch
COPIED_NOTICE_SECONDS = 4.0  # "No text box · Copied to clipboard"
COPIED_NOTICE = "No text box · Copied to clipboard"
INCOGNITO_NOTICE = "No text box · Incognito, nothing copied"
SWITCH_NOTICE = "Say an app to switch to"
SWITCH_RESULT_SECONDS = 2.5
INCOGNITO_COLOR = NSColor.colorWithSRGBRed_green_blue_alpha_(0.66, 0.52, 1.0, 1.0)  # matches the app's Incognito purple
AUTO_ENTER_COLOR = (0.25, 0.55, 1.0)  # the ⏎ badge while Auto-Enter is on
AUTO_ENTER_NOTICE_SECONDS = 2.0
TEXT_BOX_RECHECK = 0.15  # seconds: a browser box may still be taking focus (YouTube's comment box opens on click)

WARNING_YELLOW = (0.96, 0.77, 0.26)
NOTE_ICON = "record.circle"  # SF Symbol for the meeting-note button

DEBUG = os.environ.get("MISPR_DEBUG") == "1"


def log(msg):
    """Debug trace (MISPR_DEBUG=1). Never logs audio content, only timings and stats."""
    if DEBUG:
        now = time.time()
        print(f"[{time.strftime('%H:%M:%S', time.localtime(now))}.{int(now % 1 * 1000):03d}] {msg}", file=sys.stderr, flush=True)


@dataclass
class Shape:
    """The morphing background shape: black fill + light outline."""
    rect: Rect
    radius: float
    fill: float  # alpha of the black fill
    stroke: float  # alpha of the white outline

    def values(self):
        r = self.rect
        return [r.x, r.y, r.w, r.h, self.radius, self.fill, self.stroke]

    @classmethod
    def from_values(cls, v):
        return cls(Rect(*v[:4]), v[4], v[5], v[6])


@dataclass
class Layout:
    bg: Shape
    elems: dict = field(default_factory=dict)  # name -> Rect
    interactive: tuple = ()


def layout(state):
    if state == IDLE:
        return Layout(Shape(Rect.centered(CX, BASE, 40, 8), 4, 0.6, 0.35))  # darker, softer outline
    if state == HOVER:
        # Taller than the recording pills and lifted off the Dock, so they're easy to hit.
        h, bottom, gap = 36, 12, 5
        mic = Rect(CX - 48, bottom, 56, h)
        note = Rect(mic.right + gap, bottom, h, h)
        return Layout(Shape(mic, h / 2, 0.9, 0.15), {"mic": mic, "note": note}, ("mic", "note"))
    if state == HOLD:
        return Layout(Shape(Rect.centered(CX, BASE, 64, 28), 14, 0.92, 0.12))
    if state in (HANDSFREE, PROCESSING):
        elems = {
            "cancel": Rect.centered(CX - 38, BASE, 20, 20),
            "finish": Rect.centered(CX + 38, BASE, 20, 20),
            "wave": Rect.centered(CX, BASE, 48, 24),
        }
        if state == HANDSFREE:
            return Layout(Shape(Rect.centered(CX, BASE, 104, 28), 14, 0.92, 0.12), elems, ("cancel", "finish", "wave"))
        # ✕ disappears while processing, so the pill's left edge tucks in.
        return Layout(Shape(Rect(CX - 38, BASE - 14, 90, 28), 14, 0.92, 0.12), elems)
    if state == CANCELLED:
        toast = Rect.centered(CX, BASE + 6, 240, 44)
        undo = Rect(toast.right - 8 - 58, toast.cy - 14, 58, 28)
        return Layout(Shape(toast, 22, 0.92, 0.1), {"undo": undo}, ("undo",))
    if state == MEETING:
        elems = {
            "stop": Rect.centered(CX + 19, BASE, 18, 18),
            "wave": Rect.centered(CX - 9, BASE, 22, 16),
        }
        return Layout(Shape(Rect.centered(CX, BASE, 64, 26), 13, 0.55, 0.4), elems, ("stop",))
    if state == MISTAKE:
        card = Rect(CX - 190, 6, 380, 150)
        keep = Rect(card.right - 20 - 60, card.y + 18, 60, 32)
        elems = {
            "close": Rect.centered(card.right - 28, card.top - 28, 26, 26),
            "keep": keep,
            "discard": Rect(keep.x - 10 - 84, card.y + 18, 84, 32),
        }
        return Layout(Shape(card, 20, 0.94, 0.1), elems, ("close", "discard", "keep"))
    if state == SETUP:
        pill = Rect.centered(CX, BASE + 6, 260, 44)
        retry = Rect(pill.right - 8 - 62, pill.cy - 14, 62, 28)
        return Layout(Shape(pill, 22, 0.92, 0.1), {"retry": retry}, ("retry",))
    raise ValueError(state)


TOOLTIPS = {
    (HOVER, "mic"): [("Dictate ", False), ("fn", True)],
    (HOVER, "note"): [("New note ", False), ("⌥M", True)],
    (HANDSFREE, "cancel"): [("Cancel", False)],
    (HANDSFREE, "finish"): [("Finish and paste", False)],
    (HANDSFREE, "wave"): [("space", True), (" to paste · ", False), ("fn", True), (" to cancel", False)],
}


def mic_notice_text(name, built_in):
    """Built-in mics are recommended: Bluetooth headsets drop to low-quality audio while
    their mic is in use."""
    if built_in:
        return "Using Built-in mic (recommended)"
    return f"Using {name}" if name else None


class WidgetView(NSView):
    def isFlipped(self):
        return False

    def acceptsFirstMouse_(self, event):
        return True

    def drawRect_(self, dirty):
        NSColor.clearColor().set()
        NSRectFillUsingOperation(dirty, NSCompositingOperationCopy)
        self.ctrl.draw()

    @objc.python_method
    def _point(self, event):
        p = self.convertPoint_fromView_(event.locationInWindow(), None)
        return p.x, p.y

    def mouseDown_(self, event):
        self.ctrl.mouse_down(*self._point(event))

    def mouseUp_(self, event):
        self.ctrl.mouse_up(*self._point(event))


class Ticker(NSObject):
    """NSTimer needs an Objective-C target; this forwards each tick to a Python callback."""

    def tick_(self, timer):
        self.callback()


class WidgetController:
    def __init__(self):
        self.state = IDLE
        self.seq = 0  # bumps on every state change; invalidates stale scheduled callbacks
        self.state_since = time.monotonic()
        self.meeting_started = 0.0
        self.pending = []  # [(due, seq, fn)]
        self.pressed = None
        self.hovered = None
        self.suppress_hover = False
        self.accepting_mouse = False
        self.fullscreen = False
        self.screen_frame = None
        self.next_screen_poll = 0.0

        self.shape = layout(IDLE).bg.values()
        self.content_a = 1.0
        self.tip_a = 0.0
        self.tip = None  # (parts, anchor Rect) — kept while fading out
        self.bar_levels = {11: [0.0] * 11, 5: [0.0] * 5}

        self.settings = settings.load()
        self.recorder = Recorder()
        self.transcriber = Transcriber()
        self.cleaner = Cleaner()
        self.apply_prompts()
        self.setup_progress = 0.0
        self.setup_error = None
        self.rec_started_at = self.rec_ended_at = None
        self.rec_recorded_in = None  # context.frontmost() when the recording started
        self.meeting_levels = FakeLevelSource()  # replaced by real levels when the app records
        self.sounds = sounds.Sounds()
        self.sounds.enabled = self.settings.sounds
        self.on_saved = lambda path: None  # the Swift app refreshes its history from this
        # Set by the Swift app: the ◉ button opens its note window instead of starting at once.
        self.on_note_requested = None
        self.on_meeting_changed = lambda active: None
        self.on_settings_changed = lambda: None  # the Swift app re-reads settings.json

        self.hold_source = None  # "fn" or "mouse"
        self.fn_press_at = 0.0
        self.fn_consumed = False  # this fn press already did something; ignore its release
        self.last_tap_at = None  # start time of a recent short fn tap (double-tap detection)

        self.notice = None  # (text, shown_at, seconds, states): a pill above the widget
        self.mic_notice_done = False  # which mic is in use: once per launch

    # --- Setup --------------------------------------------------------------

    def start(self):
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, VIEW_W, VIEW_H),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        p = self.panel
        p.setFloatingPanel_(True)
        p.setLevel_(NSStatusWindowLevel)  # after setFloatingPanel_, which resets the level
        p.setOpaque_(False)
        p.setBackgroundColor_(NSColor.clearColor())
        p.setHasShadow_(False)
        p.setHidesOnDeactivate_(False)
        p.setIgnoresMouseEvents_(True)
        p.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorIgnoresCycle
        )
        self.view = WidgetView.alloc().initWithFrame_(NSMakeRect(0, 0, VIEW_W, VIEW_H))
        self.view.ctrl = self
        p.setContentView_(self.view)
        self._poll_screen(force=True)
        p.orderFrontRegardless()
        self.recorder.prepare()
        if setup.missing():
            self.set_state(SETUP)
            self._run_setup()
        else:
            self._load_engines()

        self.ticker = Ticker.alloc().init()
        self.ticker.callback = self.tick
        self.timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0 / FPS, self.ticker, "tick:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSRunLoopCommonModes)

    # --- State machine ------------------------------------------------------

    def set_state(self, new):
        if new == self.state:
            return
        log(f"state {self.state} -> {new}")
        self.state = new
        self.seq += 1
        self.state_since = time.monotonic()
        self.content_a = 0.0

    def after(self, delay, fn):
        self.pending.append((time.monotonic() + delay, self.seq, fn))

    def to_idle(self):
        self.set_state(IDLE)
        # Don't pop straight back into HOVER while the pointer is still resting on the pill.
        self.suppress_hover = True

    def _drop_cancelled(self):
        # A new recording replaces one still waiting in the Undo toast.
        if self.state == CANCELLED:
            self._save(storage.CANCELLED, "")
            self._wipe("cancelled (superseded)")

    def _note_context(self):
        self.rec_started_at, self.rec_ended_at = datetime.now(), None
        if not self.mic_notice_done:
            self.mic_notice_done = True
            text = mic_notice_text(*audio.input_device())
            if text:
                self.show_notice(text, MIC_NOTICE_SECONDS, (HOLD, HANDSFREE))
        # App only (cheap); the browser page is looked up at paste time.
        self.rec_recorded_in = context.frontmost(include_page=False)

    def _stop_recording(self):
        self.recorder.stop()
        self.rec_ended_at = datetime.now()

    def _save(self, status, text, pasted_into=None, raw=None, cleanup=None):
        """Keep the recording on disk unless Incognito is on. Never breaks dictation."""
        if self.settings.incognito or self.rec_started_at is None:
            return
        audio = self.recorder.audio()
        if len(audio) < 0.3 * storage.SAMPLE_RATE:
            return
        try:
            path = storage.save_recording(
                audio, status=status, transcript=text,
                started_at=self.rec_started_at, ended_at=self.rec_ended_at or datetime.now(),
                recorded_in=self.rec_recorded_in or {}, pasted_into=pasted_into,
                model=DEFAULT_MODEL.filename, raw_transcript=raw, cleanup=cleanup,
            )
            log(f"saved {status} recording -> {path.parent.name}/{path.name}")
        except OSError as e:
            print(f"mispr: could not save recording: {e}", file=sys.stderr)
            return
        self.on_saved(path)

    def reload_settings(self):
        """Pick up settings.json after the main window changed it."""
        was_auto_enter = self.settings.auto_enter
        self.settings = settings.load()
        if self.settings.auto_enter != was_auto_enter:  # say so, by sound and on the widget
            self.sounds.enabled = self.settings.sounds
            self.sounds.play(sounds.LOCK)
            self.show_notice("Auto-Enter on ⏎" if self.settings.auto_enter else "Auto-Enter off",
                             AUTO_ENTER_NOTICE_SECONDS, (IDLE, HOVER))
        self.sounds.enabled = self.settings.sounds
        self.apply_prompts()
        log(f"settings reloaded: {self.settings}")

    def apply_prompts(self):
        """Use the prompts from the app's Prompts page (prompts.json), or the defaults."""
        p = prompts.load()
        self.cleaner.configure(p.full_system(), p.examples, p.guard)

    def begin_hold(self, source):
        self._drop_cancelled()
        if not self.recorder.start():
            self.sounds.play(sounds.ERROR)  # the mic didn't open: don't fail silently
            return
        self._note_context()
        self.sounds.play(sounds.START)
        self.hold_source = source
        self.set_state(HOLD)

    def begin_handsfree(self, sound=True):
        self._drop_cancelled()
        if not self.recorder.start():
            self.sounds.play(sounds.ERROR)
            return
        self._note_context()
        if sound:
            self.sounds.play(sounds.START)
        self.set_state(HANDSFREE)

    def _wipe(self, reason):
        secs, peak, ok = self.recorder.wipe()
        log(f"{reason}: {secs:.2f}s captured, peak {peak:.3f}, wiped={'ok' if ok else 'FAILED'}")

    def finish(self):
        self._stop_recording()
        self.sounds.play(sounds.STOP)
        self._process("finished")

    def _process(self, reason):
        self.set_state(PROCESSING)
        self.transcriber.transcribe_async(
            self.recorder.audio(),
            lambda text, raw, info, secs: self._on_transcribed(text, raw, info, secs, reason),
            post=self.cleaner.clean if self.settings.cleanup else None,
        )

    def _on_transcribed(self, text, raw, info, secs, reason):
        cleanup_note = ""
        if info:
            cleanup_note = f", cleanup {info['ms']} ms " + ("applied" if info["applied"] else f"rejected ({info['rejected']})")
        log(f"transcribed + cleaned in {secs:.2f}s -> {len(text)} chars{cleanup_note}")
        if text:
            target = context.frontmost()  # where the text is about to land
            where, why = context.focused_text_target()
            if where == context.NO and context.is_browser(target):
                time.sleep(TEXT_BOX_RECHECK)  # focus may still be moving into the box
                where, why = context.focused_text_target()
                why += f" [after a recheck; focused: {context.focus_chain()}]"
            log(f"text box: {where} ({why})")
            incognito = self.settings.incognito
            if where == context.NO:
                # ⌘V would do nothing (or paste something odd, like files in Finder), so
                # leave the text on the clipboard instead. In Incognito the clipboard is
                # off-limits too: the words are simply dropped.
                if not incognito:
                    copy_text(text)
                self.sounds.play(sounds.ERROR)
                self.show_notice(INCOGNITO_NOTICE if incognito else COPIED_NOTICE, COPIED_NOTICE_SECONDS, (IDLE, HOVER))
                status = storage.COPIED
            else:
                # Incognito types the words in directly so they never pass through the clipboard.
                (type_text if incognito else paste_text)(text)
                if self.settings.auto_enter:
                    AppHelper.callLater(ENTER_DELAY, press_enter)  # send it, so you can just talk
                self.sounds.play(sounds.PASTE)
                status = storage.PASTED
            # The worker is done with the audio view: save it (unless Incognito), then wipe.
            self._save(status, text, pasted_into=target, raw=raw, cleanup=info)
        else:
            self.sounds.play(sounds.ALERT)  # recorded, but no words came out: nothing to paste
        self._wipe(reason)
        self.to_idle()

    def cancel(self):
        """Stop and offer Undo. The audio stays in locked memory until the toast expires."""
        self._stop_recording()
        self.sounds.play(sounds.CANCEL)
        self.set_state(CANCELLED)
        self.after(TOAST_SECONDS, self._expire_cancel)

    def _expire_cancel(self):
        self._save(storage.CANCELLED, "")
        self._wipe("cancelled")
        self.to_idle()

    def undo_cancel(self):
        self._process("undo")

    def discard_quietly(self):
        """Drop a recording that was never meant to be one (an fn tap or fn+key combo)."""
        self.recorder.stop()
        self._wipe("discarded")
        self.set_state(IDLE)

    # --- First-run setup ----------------------------------------------------

    def _load_engines(self):
        self.transcriber.load_async()
        self.cleaner.load_async()

    def _run_setup(self):
        self.setup_error = None
        self.setup_progress = 0.0
        log(f"setup: downloading {[m.filename for m in setup.missing()]}")
        setup.install_async(self._setup_progress, self._setup_done, self._setup_failed)

    def _setup_progress(self, fraction):
        self.setup_progress = fraction  # called from the download thread; just store it

    def _setup_done(self):
        log("setup: models installed")
        self.sounds.play(sounds.SUCCESS)
        self._load_engines()
        self.to_idle()

    def _setup_failed(self, message):
        log(f"setup: failed ({message})")
        print(f"mispr: model download failed: {message}", file=sys.stderr)
        self.sounds.play(sounds.ERROR)
        self.setup_error = message

    def _retry_setup(self):
        if self.setup_error:
            self._run_setup()

    # --- fn key -------------------------------------------------------------

    def fn_down(self):
        now = time.monotonic()
        log(f"fn down (state {self.state})")
        self.fn_consumed = True
        if self.state == HANDSFREE:
            self.cancel()
        elif self.state not in (IDLE, HOVER, CANCELLED):
            pass  # busy (processing, meeting, card): ignore fn
        elif self.last_tap_at is not None and now - self.last_tap_at <= DOUBLE_TAP_WINDOW:
            # The first tap already played the start sound; now confirm the lock.
            self.last_tap_at = None
            self.begin_handsfree(sound=False)
            if self.state == HANDSFREE:
                self.sounds.play(sounds.LOCK)
        else:
            # Start recording immediately so the first word isn't clipped; a short
            # release turns this into a tap instead.
            self.fn_consumed = False
            self.fn_press_at = now
            self.begin_hold("fn")

    def fn_up(self):
        log(f"fn up (held {time.monotonic() - self.fn_press_at:.2f}s)" if not self.fn_consumed else "fn up")
        if self.fn_consumed or self.state != HOLD or self.hold_source != "fn":
            return
        if time.monotonic() - self.fn_press_at < FN_TAP_MAX:
            self.last_tap_at = self.fn_press_at
            self.discard_quietly()
        else:
            self.finish()

    # --- App switcher key -----------------------------------------------------

    def switch_key(self, edge):
        """The app switcher key: "down" starts listening, "up" switches to the app you said,
        "combo" (a shortcut with it held) or a quick tap drops it."""
        log(f"switch key {edge} (state {self.state})")
        if edge == "down":
            if self.state not in (IDLE, HOVER, CANCELLED):
                return  # busy dictating, processing or in a meeting
            self.begin_hold("switch")
            if self.state == HOLD:
                self.fn_press_at = time.monotonic()
                self.show_notice(SWITCH_NOTICE, 60, (HOLD,))
            return
        if self.state != HOLD or self.hold_source != "switch":
            return
        if edge == "combo" or time.monotonic() - self.fn_press_at < FN_TAP_MAX:
            self.discard_quietly()
            return
        self._stop_recording()
        self.sounds.play(sounds.STOP)
        self.set_state(PROCESSING)
        # Raw Whisper text: an app name needs no cleanup, and skipping it is faster.
        self.transcriber.transcribe_async(self.recorder.audio(), lambda text, raw, info, secs: self._on_switch_heard(text))

    def _on_switch_heard(self, text):
        """Act on what was said: teach a nickname, or bring an app to the front. The audio is
        wiped and never saved (switching apps isn't dictation history)."""
        log(f"switch heard {text!r}")
        self._wipe("app switch")
        self.to_idle()
        command = apps.parse(text or "")
        if command is None:
            self.sounds.play(sounds.ALERT)
            return
        installed = apps.find_apps()
        if command[0] == "nickname":
            _, nick, spoken = command
            target = apps.match(spoken, installed, self.settings.app_nicknames)
            if target is None:
                return self._switch_failed(f"No app called “{spoken}”")
            self.settings = settings.save_nickname(nick, target)
            self.on_settings_changed()
            self.sounds.play(sounds.PASTE)
            self.show_notice(f"“{nick}” now opens {target}", SWITCH_RESULT_SECONDS, (IDLE, HOVER))
            return
        running = apps.running_apps()

        def find(name):  # (app name, path) or None
            target = apps.match(name, {**installed, **running}, self.settings.app_nicknames, running)
            path = running.get(target) or installed.get(target)
            return (target, path) if path else None

        kind = command[0]
        names = [n for n in command[1:3] if isinstance(n, str)] if kind == "beside" else [command[1]]
        found = []
        for name in names:
            if name is None:  # no app named: the one you're in
                found.append((None, None))
                continue
            hit = find(name)
            if hit is None:
                return self._switch_failed(f"No app called “{name}”")
            found.append(hit)
        if kind == "switch":
            apps.bring_to_front(found[0][1])
            return self._switch_done(f"→ {found[0][0]}")
        if kind in ("close", "minimize", "expand"):
            target, path = found[0]
            pid = apps.frontmost_pid() if path is None else apps.pid_for(path)
            if pid is None:
                return self._switch_failed(f"{target} isn't open")
            ok = apps.window_action(pid, "frame", apps.layout(apps.screen_frame(), "expand")) if kind == "expand" \
                else apps.window_action(pid, kind)
            if kind == "expand" and path:
                apps.bring_to_front(path)
            word = {"close": "Closed", "minimize": "Minimized", "expand": "Expanded"}[kind]
            return self._switch_done(f"{word} {target or 'the window'}") if ok else self._switch_failed("No window to " + kind)
        screen = apps.screen_frame()
        frames = [apps.layout(screen, "size", command[2])] if kind == "size" else list(apps.layout(screen, "beside", command[3]))
        for (target, path), frame in reversed(list(zip(found, frames))):  # the first named ends up in front
            self._place(path, frame)
        label = f"{found[0][0]} {command[2]}%" if kind == "size" else f"{found[0][0]} | {found[1][0]}"
        self._switch_done(label)

    def _place(self, path, frame, tries=4):
        """Bring the app forward and give its window `frame`; an app still opening gets a few more tries."""
        apps.bring_to_front(path)
        pid = apps.pid_for(path)
        if (pid is None or not apps.window_action(pid, "frame", frame)) and tries > 1:
            AppHelper.callLater(0.75, self._place, path, frame, tries - 1)

    def _switch_done(self, message):
        self.sounds.play(sounds.PASTE)
        self.show_notice(message, SWITCH_RESULT_SECONDS, (IDLE, HOVER))

    def _switch_failed(self, message):
        self.sounds.play(sounds.ERROR)
        self.show_notice(message, SWITCH_RESULT_SECONDS, (IDLE, HOVER))

    def handle_key(self, keycode):
        """Called from inside the event tap: decide fast, act on the next run-loop pass.

        Hands-free: space / return / enter = finish and paste, delete = cancel.
        Cancelled toast: delete = discard now (skip the Undo countdown).
        """
        state = self.state
        action = {
            (HANDSFREE, KEY_SPACE): self.finish,
            (HANDSFREE, KEY_RETURN): self.finish,
            (HANDSFREE, KEY_KEYPAD_ENTER): self.finish,
            (HANDSFREE, KEY_DELETE): self.cancel,
            (CANCELLED, KEY_DELETE): self._expire_cancel,
        }.get((state, keycode))
        if action is None:
            return False
        log(f"key {keycode} -> {action.__name__}")
        AppHelper.callAfter(lambda: self.state == state and action())
        return True

    def fn_combo(self):
        """Another key was pressed with fn held (fn+arrow, fn+F-key...): not dictation."""
        log("fn + other key")
        self.last_tap_at = None
        if not self.fn_consumed and self.state == HOLD and self.hold_source == "fn":
            self.fn_consumed = True
            self.discard_quietly()

    def request_note(self):
        """The ◉ button and ⌥M: the app opens its note window and starts (or stops) the
        recording; standalone, the widget's meeting pill toggles."""
        if self.on_note_requested is not None:
            if self.state == HOVER:
                self.to_idle()
            self.on_note_requested()
        elif self.state == MEETING:
            self.stop_meeting()
        else:
            self.begin_meeting()

    def begin_meeting(self):
        if self.state not in (IDLE, HOVER):
            return  # busy dictating, processing, or already in a meeting
        self.sounds.play(sounds.START)
        self.meeting_started = time.monotonic()
        self.set_state(MEETING)
        self.on_meeting_changed(True)

    def stop_meeting(self):
        if self.state != MEETING:
            return
        self.on_meeting_changed(False)
        self.sounds.play(sounds.STOP)
        if time.monotonic() - self.meeting_started < MIN_MEETING_SECONDS:
            self.set_state(MISTAKE)
        else:
            # TODO: diarised transcript + LLM summary -> meeting-recordings/.
            self.to_idle()

    # --- Mouse --------------------------------------------------------------

    def hit(self, px, py):
        lay = layout(self.state)
        for name in lay.interactive:
            if name == "retry" and not self.setup_error:
                continue  # only clickable once a download has failed
            if lay.elems[name].contains(px, py):
                return name
        return None

    def mouse_down(self, px, py):
        self.pressed = self.hit(px, py)
        if self.state == HOVER and self.pressed == "mic":
            seq = self.seq

            def maybe_hold():
                if self.seq == seq and self.pressed == "mic":
                    self.begin_hold("mouse")

            self.after(HOLD_DELAY, maybe_hold)

    def mouse_up(self, px, py):
        pressed, self.pressed = self.pressed, None
        released_on = self.hit(px, py)
        if self.state == HOLD and self.hold_source == "mouse" and pressed == "mic":
            self.finish()
            return
        if pressed is None or pressed != released_on:
            return
        action = {
            (HOVER, "mic"): self.begin_handsfree,
            (HOVER, "note"): self.request_note,
            (HANDSFREE, "cancel"): self.cancel,
            (HANDSFREE, "finish"): self.finish,
            (MEETING, "stop"): self.stop_meeting,
            (MISTAKE, "close"): self.to_idle,
            (MISTAKE, "discard"): self.to_idle,
            (MISTAKE, "keep"): self.to_idle,  # TODO: keep -> summarise like a normal meeting
            (CANCELLED, "undo"): self.undo_cancel,
            (SETUP, "retry"): self._retry_setup,
        }.get((self.state, pressed))
        if action:
            action()

    def _update_mouse(self):
        loc = NSEvent.mouseLocation()
        origin = self.panel.frame().origin
        px, py = loc.x - origin.x, loc.y - origin.y

        if self.state == IDLE and not self.hidden:
            inside = Rect.centered(CX, BASE, 72, 34).contains(px, py)
            if self.suppress_hover:
                self.suppress_hover = inside
            elif inside:
                self.set_state(HOVER)
        elif self.state == HOVER and self.pressed is None:
            lay = layout(HOVER)
            if not lay.elems["mic"].union(lay.elems["note"]).inset(-10).contains(px, py):
                self.set_state(IDLE)

        self.hovered = None if self.hidden else self.hit(px, py)
        accept = self.hovered is not None or self.pressed is not None
        if accept != self.accepting_mouse:
            self.accepting_mouse = accept
            self.panel.setIgnoresMouseEvents_(not accept)

    # --- Screen following ---------------------------------------------------

    @property
    def hidden(self):
        return self.fullscreen and self.state in (IDLE, HOVER)

    def _poll_screen(self, force=False):
        screen, self.fullscreen = active_screen()
        vf = screen.visibleFrame()
        frame = (vf.origin.x + vf.size.width / 2 - VIEW_W / 2, vf.origin.y)
        if force or frame != self.screen_frame:
            self.screen_frame = frame
            self.panel.setFrame_display_(NSMakeRect(frame[0], frame[1], VIEW_W, VIEW_H), True)

    # --- Frame loop ---------------------------------------------------------

    def _run_due(self, now):
        """Run scheduled callbacks that are due, skipping any from an earlier state."""
        due = [p for p in self.pending if p[0] <= now]
        self.pending = [p for p in self.pending if p[0] > now]
        for _, seq, fn in due:
            if seq == self.seq:
                fn()

    def tick(self):
        now = time.monotonic()
        self._run_due(now)

        if now >= self.next_screen_poll:
            self.next_screen_poll = now + SCREEN_POLL_SECONDS
            self._poll_screen()

        self._update_mouse()
        self._update_levels(now)

        target = layout(self.state).bg.values()
        self.shape = [c + (t - c) * MORPH for c, t in zip(self.shape, target)]
        self.content_a += (1.0 - self.content_a) * 0.25

        tip = TOOLTIPS.get((self.state, self.hovered))
        if tip is not None:
            label = (self.settings.hotkey or {}).get("label") or "fn"
            tip = [(label, bold) if (text, bold) == ("fn", True) else (text, bold) for text, bold in tip]
        if tip is not None:
            self.tip = (tip, layout(self.state).elems[self.hovered])
        self.tip_a += ((1.0 if tip is not None else 0.0) - self.tip_a) * 0.3

        self.view.setNeedsDisplay_(True)

    def _update_levels(self, now):
        if self.state in (HOLD, HANDSFREE):
            lvl = self.recorder.level()
        elif self.state == MEETING:
            lvl = self.meeting_levels.level(now)
        else:
            lvl = 0.0
        for n, arr in self.bar_levels.items():
            mid = (n - 1) / 2
            for i in range(n):
                envelope = math.exp(-(((i - mid) / (n * 0.3)) ** 2))
                target = lvl * envelope * random.uniform(0.55, 1.0)
                arr[i] += (target - arr[i]) * 0.35

    # --- Rendering ----------------------------------------------------------

    def draw(self):
        if self.hidden:
            return
        shape = Shape.from_values(self.shape)
        r = shape.rect
        a = self.content_a
        lay = layout(self.state)
        s = self.state

        draw.fill_round(r, shape.radius, white(0.0, shape.fill))
        if self.settings.incognito:
            # A purple outline whenever Incognito is on, so you can tell at a glance.
            draw.stroke_round(r, shape.radius, INCOGNITO_COLOR.colorWithAlphaComponent_(max(0.85, shape.stroke)), 1.5)
        else:
            draw.stroke_round(r, shape.radius, white(1.0, shape.stroke), 1.0)
        if self.settings.auto_enter:
            # A small ⏎ badge on the corner whenever Auto-Enter is on.
            bx, by = r.right - 3, r.top - 3
            draw.fill_circle(bx, by, 6.5, NSColor.colorWithSRGBRed_green_blue_alpha_(*AUTO_ENTER_COLOR, 1.0))
            draw.symbol("return", bx, by, 7, weight=NSFontWeightBold)

        if s == HOVER:
            draw.symbol("mic.fill", r.cx, r.cy, 15, alpha=a)
            note = lay.elems["note"]
            lit = self.hovered == "note"
            draw.fill_circle(note.cx, note.cy, note.w / 2, white(0.15 if lit else 0.1, 0.92 * a))
            draw.stroke_circle(note.cx, note.cy, note.w / 2 - 0.5, white(1.0, 0.15 * a))
            draw.symbol(NOTE_ICON, note.cx, note.cy, 17, alpha=(1.0 if lit else 0.85) * a)

        elif s == HOLD:
            draw.bars(r.cx, r.cy, self.bar_levels[11], 3.5, 2, 16, white(1.0, a))

        elif s in (HANDSFREE, PROCESSING):
            wave = lay.elems["wave"]
            wave_alpha = a if s == HANDSFREE else 0.4 * a
            draw.bars(wave.cx, r.cy, self.bar_levels[11], 3.5, 2, 16, white(1.0, wave_alpha))
            fin = lay.elems["finish"]
            if s == HANDSFREE:
                c = lay.elems["cancel"]
                lit = self.hovered == "cancel"
                draw.fill_circle(c.cx, c.cy, 9, white(1.0, (0.28 if lit else 0.18) * a))
                draw.symbol("xmark", c.cx, c.cy, 8, alpha=a, weight=NSFontWeightBold)
                draw.fill_circle(fin.cx, fin.cy, 9, white(1.0, a))
                draw.symbol("checkmark", fin.cx, fin.cy, 9, rgb=(0.0, 0.0, 0.0), alpha=a, weight=NSFontWeightBold)
            else:
                draw.spinner(fin.cx, fin.cy, 7, time.monotonic() * 1.2, a)

        elif s == CANCELLED:
            label = draw.rich([("Transcript cancelled", False)], 14, white(1.0, a))
            draw.draw_text_left(label, r.x + 18, r.cy + 1)
            undo = lay.elems["undo"]
            lit = self.hovered == "undo"
            draw.fill_round(undo, 9, white(1.0, (0.24 if lit else 0.14) * a))
            draw.draw_text_centered(draw.rich([("Undo", False)], 13, white(1.0, a)), undo.cx, undo.cy)
            remaining = max(0.0, 1.0 - (time.monotonic() - self.state_since) / TOAST_SECONDS)
            track = Rect(r.x + 16, r.y + 3, r.w - 32, 2)
            draw.fill_round(track, 1, white(1.0, 0.18 * a))
            draw.fill_round(Rect(track.x, track.y, track.w * remaining, 2), 1, white(1.0, 0.85 * a))

        elif s == MEETING:
            w = lay.elems["wave"]
            draw.bars(w.cx, w.cy, self.bar_levels[5], 3, 1.5, 10, white(1.0, 0.75 * a))
            st = lay.elems["stop"]
            lit = self.hovered == "stop"
            draw.fill_circle(st.cx, st.cy, 9, white(1.0, (0.35 if lit else 0.22) * a))
            draw.symbol("stop.fill", st.cx, st.cy, 7, alpha=0.85 * a)

        elif s == SETUP:
            if self.setup_error:
                label = draw.rich([("Model download failed", False)], 14, white(1.0, a))
                retry = lay.elems["retry"]
                lit = self.hovered == "retry"
                draw.fill_round(retry, 9, white(1.0, (0.24 if lit else 0.14) * a))
                draw.draw_text_centered(draw.rich([("Retry", False)], 13, white(1.0, a)), retry.cx, retry.cy)
            else:
                pct = int(self.setup_progress * 100)
                label = draw.rich([("Downloading models ", False), (f"{pct}%", True)], 14, white(1.0, a))
                track = Rect(r.x + 16, r.y + 3, r.w - 32, 2)
                draw.fill_round(track, 1, white(1.0, 0.18 * a))
                draw.fill_round(Rect(track.x, track.y, track.w * self.setup_progress, 2), 1, white(1.0, 0.85 * a))
            draw.draw_text_left(label, r.x + 18, r.cy + 1)

        elif s == MISTAKE:
            self._draw_mistake_card(r, lay, a)

        self._draw_tooltip(r)

    def _draw_mistake_card(self, card, lay, a):
        title_y = card.top - 28
        draw.symbol("exclamationmark.triangle.fill", card.x + 30, title_y, 14, rgb=WARNING_YELLOW, alpha=a)
        title = draw.rich([("Started by mistake?", True)], 15, white(1.0, a))
        draw.draw_text_left(title, card.x + 46, title_y)

        close = lay.elems["close"]
        lit = self.hovered == "close"
        draw.stroke_circle(close.cx, close.cy, 12, white(1.0, (0.9 if lit else 0.6) * a), 1.2)
        draw.symbol("xmark", close.cx, close.cy, 10, alpha=a, weight=NSFontWeightSemibold)

        body = draw.rich(
            [("Only a few words were captured. Keep this meeting or discard it.", False)],
            14,
            white(1.0, 0.7 * a),
        )
        body.drawInRect_(NSMakeRect(card.x + 20, card.y + 56, card.w - 40, 44))

        for name, fill, fg, bold in (
            ("discard", white(1.0, 0.14), white(1.0, a), False),
            ("keep", white(1.0, 0.94), white(0.0, a), True),
        ):
            b = lay.elems[name]
            lit = self.hovered == name
            draw.fill_round(b, 9, white(fill.whiteComponent(), min(1.0, fill.alphaComponent() + (0.08 if lit else 0)) * a))
            draw.draw_text_centered(draw.rich([(name.capitalize(), bold)], 14, fg), b.cx, b.cy)

    def show_notice(self, text, seconds, states):
        """Show `text` in a pill above the widget for `seconds`, only while in `states`."""
        self.notice = (text, time.monotonic(), seconds, states)

    def _notice_alpha(self):
        """Opacity of the notice: full while shown, fading out over its last 0.4 s."""
        if self.notice is None or self.state not in self.notice[3]:
            return 0.0
        _, shown_at, seconds, _ = self.notice
        remaining = seconds - (time.monotonic() - shown_at)
        return max(0.0, min(1.0, remaining / 0.4))

    def _draw_notice(self, bg, a):
        label = draw.rich([(self.notice[0], False)], 13, white(1.0, a))
        sz = label.size()
        box = Rect.centered(bg.cx, bg.top + 8 + 14, sz.width + 32, 28)
        draw.fill_round(box, 14, white(0.0, 0.92 * a))
        draw.stroke_round(box, 14, white(1.0, 0.1 * a))
        draw.draw_text_centered(label, box.cx, box.cy)

    def _draw_tooltip(self, bg):
        notice_a = self._notice_alpha()
        if notice_a > 0.01:
            self._draw_notice(bg, notice_a)  # takes the tooltip's spot while visible
            return
        if self.tip is None or self.tip_a < 0.01:
            return
        parts, anchor = self.tip
        a = self.tip_a
        label = draw.rich(parts, 13, white(1.0, a))
        sz = label.size()
        box = Rect.centered(anchor.cx, bg.top + 8 + 14, sz.width + 24, 28)
        draw.fill_round(box, 14, white(0.0, 0.92 * a))
        draw.stroke_round(box, 14, white(1.0, 0.1 * a))
        draw.draw_text_centered(label, box.cx, box.cy)
