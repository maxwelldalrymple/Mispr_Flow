"""The floating dictation widget that sits just above the Dock.

States (see README / PLAN for the full behaviour):

    IDLE        tiny outlined pill
    HOVER       mic button + note (◉) button, with tooltips
    HOLD        push-to-talk recording: compact pill with live waveform
    HANDSFREE   toggle recording: ✕ · waveform · ✓
    PROCESSING  transcribing: dim waveform + spinner
    CANCELLED   "Transcript cancelled" toast with a draining progress bar
    MEETING     notetaker running: outlined pill with waveform + ■ stop
    MISTAKE     "Started by mistake?" card (Discard / Keep)

This build is UI-only: clicks drive every state, the waveform comes from a fake
level source, and PROCESSING / meeting stop are stubs. `fn` handling, audio, STT
and paste plug into begin_hold / begin_handsfree / finish / cancel later.
"""

import math
import random
import time
from dataclasses import dataclass, field

import objc
from AppKit import (
    NSBackingStoreBuffered,
    NSColor,
    NSCompositingOperationCopy,
    NSEvent,
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

from . import draw, sounds
from .draw import Rect, white
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

RECORDING_STATES = (HOLD, HANDSFREE, MEETING)

# Canvas: a transparent panel centred above the Dock; everything is drawn inside it.
VIEW_W, VIEW_H = 480, 220
CX = VIEW_W / 2
BASE = 18  # centre line of the pill, in points above the bottom of the visible frame

FPS = 60
MORPH = 0.3  # per-frame easing factor toward the target shape
HOLD_DELAY = 0.3  # long-press on the mic longer than this = push-to-talk
PROCESSING_STUB_SECONDS = 1.2
TOAST_SECONDS = 3.0
MIN_MEETING_SECONDS = 10  # stand-in for "only a few words were captured"
SCREEN_POLL_SECONDS = 0.5

WARNING_YELLOW = (0.96, 0.77, 0.26)


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
        return Layout(Shape(Rect.centered(CX, BASE, 40, 8), 4, 0.35, 0.5))
    if state == HOVER:
        mic = Rect.centered(CX - 16, BASE, 48, 28)
        note = Rect.centered(CX + 26, BASE, 28, 28)
        return Layout(Shape(mic, 14, 0.9, 0.15), {"mic": mic, "note": note}, ("mic", "note"))
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
        return Layout(Shape(Rect.centered(CX, BASE + 6, 200, 40), 20, 0.92, 0.1))
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
    raise ValueError(state)


TOOLTIPS = {
    (HOVER, "mic"): [("Dictate ", False), ("fn", True)],
    (HOVER, "note"): [("New note ", False), ("⌥M", True)],
    (HANDSFREE, "cancel"): [("Cancel", False)],
    (HANDSFREE, "finish"): [("Finish and paste", False)],
    (HANDSFREE, "wave"): [("Press ", False), ("fn", True), (" to finish and paste", False)],
}


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


class _Ticker(NSObject):
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

        self.levels = FakeLevelSource()
        self.sounds = sounds.Sounds()

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

        self.ticker = _Ticker.alloc().init()
        self.ticker.callback = self.tick
        self.timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0 / FPS, self.ticker, "tick:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSRunLoopCommonModes)

    # --- State machine ------------------------------------------------------

    def set_state(self, new):
        if new == self.state:
            return
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

    def begin_hold(self):
        self.sounds.play(sounds.START)
        self.set_state(HOLD)

    def begin_handsfree(self):
        self.sounds.play(sounds.START)
        self.set_state(HANDSFREE)

    def finish(self):
        self.sounds.play(sounds.STOP)
        self.set_state(PROCESSING)
        # TODO: transcribe -> clean up -> paste. Stubbed for the UI-only build.
        self.after(PROCESSING_STUB_SECONDS, self.to_idle)

    def cancel(self):
        self.sounds.play(sounds.CANCEL)
        self.set_state(CANCELLED)
        self.after(TOAST_SECONDS, self.to_idle)

    def begin_meeting(self):
        self.sounds.play(sounds.START)
        self.meeting_started = time.monotonic()
        self.set_state(MEETING)

    def stop_meeting(self):
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
            if lay.elems[name].contains(px, py):
                return name
        return None

    def mouse_down(self, px, py):
        self.pressed = self.hit(px, py)
        if self.state == HOVER and self.pressed == "mic":
            seq = self.seq

            def maybe_hold():
                if self.seq == seq and self.pressed == "mic":
                    self.begin_hold()

            self.after(HOLD_DELAY, maybe_hold)

    def mouse_up(self, px, py):
        pressed, self.pressed = self.pressed, None
        released_on = self.hit(px, py)
        if self.state == HOLD and pressed == "mic":
            self.finish()
            return
        if pressed is None or pressed != released_on:
            return
        action = {
            (HOVER, "mic"): self.begin_handsfree,
            (HOVER, "note"): self.begin_meeting,
            (HANDSFREE, "cancel"): self.cancel,
            (HANDSFREE, "finish"): self.finish,
            (MEETING, "stop"): self.stop_meeting,
            (MISTAKE, "close"): self.to_idle,
            (MISTAKE, "discard"): self.to_idle,
            (MISTAKE, "keep"): self.to_idle,  # TODO: keep -> summarise like a normal meeting
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

    def tick(self):
        now = time.monotonic()

        due = [p for p in self.pending if p[0] <= now]
        self.pending = [p for p in self.pending if p[0] > now]
        for _, seq, fn in due:
            if seq == self.seq:
                fn()

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
            self.tip = (tip, layout(self.state).elems[self.hovered])
        self.tip_a += ((1.0 if tip is not None else 0.0) - self.tip_a) * 0.3

        self.view.setNeedsDisplay_(True)

    def _update_levels(self, now):
        live = self.state in RECORDING_STATES
        lvl = self.levels.level(now) if live else 0.0
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
        draw.stroke_round(r, shape.radius, white(1.0, shape.stroke), 1.0)

        if s == HOVER:
            draw.icon_mic(r.cx, r.cy, white(1.0, a))
            note = lay.elems["note"]
            lit = self.hovered == "note"
            draw.fill_circle(note.cx, note.cy, note.w / 2, white(0.15 if lit else 0.1, 0.92 * a))
            draw.stroke_circle(note.cx, note.cy, note.w / 2 - 0.5, white(1.0, 0.15 * a))
            draw.icon_record(note.cx, note.cy, white(1.0, (1.0 if lit else 0.85) * a))

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
                draw.icon_x(c.cx, c.cy, 3, white(1.0, a))
                draw.fill_circle(fin.cx, fin.cy, 9, white(1.0, a))
                draw.icon_check(fin.cx, fin.cy, white(0.0, a))
            else:
                draw.spinner(fin.cx, fin.cy, 7, time.monotonic() * 1.2, a)

        elif s == CANCELLED:
            label = draw.rich([("Transcript cancelled", False)], 14, white(1.0, a))
            draw.draw_text_centered(label, r.cx, r.cy + 1)
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
            draw.icon_stop(st.cx, st.cy, white(1.0, 0.85 * a))

        elif s == MISTAKE:
            self._draw_mistake_card(r, lay, a)

        self._draw_tooltip(r)

    def _draw_mistake_card(self, card, lay, a):
        title_y = card.top - 28
        draw.icon_warning(card.x + 30, title_y, draw.srgb(*WARNING_YELLOW, a))
        title = draw.rich([("Started by mistake?", True)], 15, white(1.0, a))
        draw.draw_text_left(title, card.x + 46, title_y)

        close = lay.elems["close"]
        lit = self.hovered == "close"
        draw.stroke_circle(close.cx, close.cy, 12, white(1.0, (0.9 if lit else 0.6) * a), 1.2)
        draw.icon_x(close.cx, close.cy, 4, white(1.0, a), 1.4)

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

    def _draw_tooltip(self, bg):
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
