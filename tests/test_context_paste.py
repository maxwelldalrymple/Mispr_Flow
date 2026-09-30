import pytest
import Quartz
from AppKit import NSData, NSPasteboard, NSPasteboardTypeString, NSURL

from mispr import context, paste


# --- context -----------------------------------------------------------------------

class AXNode:
    def __init__(self, role=None, url=None, title=None, parent=None):
        self.attrs = {"AXRole": role, "AXURL": url, "AXTitle": title, "AXParent": parent}


class FakeApp:
    def __init__(self, name="Google Chrome", bundle="com.google.Chrome", pid=42):
        self._n, self._b, self._p = name, bundle, pid

    def localizedName(self):
        return self._n

    def bundleIdentifier(self):
        return self._b

    def processIdentifier(self):
        return self._p


@pytest.fixture
def ax(monkeypatch):
    """A fake accessibility tree: app element -> focused element / focused window."""
    tree = {"app": AXNode(), "timeout": None}

    def copy_attr(element, name, _):
        value = element.attrs.get(name)
        return (0, value) if value is not None else (-25212, None)  # kAXErrorNoValue

    monkeypatch.setattr(context.AS, "AXUIElementCopyAttributeValue", copy_attr)
    monkeypatch.setattr(context.AS, "AXUIElementCreateApplication", lambda pid: tree["app"])
    monkeypatch.setattr(context.AS, "AXUIElementSetMessagingTimeout", lambda el, t: tree.__setitem__("timeout", t))
    return tree


def set_frontmost(monkeypatch, app):
    class Workspace:  # Python stand-in: ObjC class methods can't be monkeypatched
        @staticmethod
        def sharedWorkspace():
            return Workspace()

        def frontmostApplication(self):
            return app

    monkeypatch.setattr(context, "NSWorkspace", Workspace)


class TestAttrHelpers:
    def test_attr_none_element(self):
        assert context._attr(None, "AXRole") is None

    def test_attr_success_and_error(self, ax):
        node = AXNode(role="AXButton")
        assert context._attr(node, "AXRole") == "AXButton"
        assert context._attr(node, "AXURL") is None

    def test_url_string_variants(self):
        assert context._url_string(None) is None
        assert context._url_string("https://a.com") == "https://a.com"
        assert context._url_string(NSURL.URLWithString_("https://b.com/x?y=1")) == "https://b.com/x?y=1"


class TestBrowserPage:
    def test_outermost_web_area_wins_over_iframe(self, ax):
        page = AXNode("AXWebArea", url="https://docs.example.com/doc/1", title="My Doc")
        iframe = AXNode("AXWebArea", url="https://editor.cdn.example/frame", title="frame", parent=AXNode("AXGroup", parent=page))
        field = AXNode("AXTextArea", parent=iframe)
        ax["app"].attrs["AXFocusedUIElement"] = field
        assert context._browser_page(1) == ("https://docs.example.com/doc/1", "My Doc")

    def test_single_web_area(self, ax):
        page = AXNode("AXWebArea", url="https://claude.ai/chat", title="Claude")
        ax["app"].attrs["AXFocusedUIElement"] = AXNode("AXTextArea", parent=page)
        assert context._browser_page(1) == ("https://claude.ai/chat", "Claude")

    def test_address_bar_falls_back_to_window_document(self, ax):
        window = AXNode(title="Tab Title")
        window.attrs["AXDocument"] = "https://example.com/tab"
        ax["app"].attrs["AXFocusedUIElement"] = AXNode("AXTextField", parent=AXNode("AXToolbar"))
        ax["app"].attrs["AXFocusedWindow"] = window
        assert context._browser_page(1) == ("https://example.com/tab", "Tab Title")

    def test_nothing_available(self, ax):
        assert context._browser_page(1) == (None, None)

    def test_sets_messaging_timeout(self, ax):
        context._browser_page(1)
        assert ax["timeout"] == context._AX_TIMEOUT

    def test_timeout_never_stalls_paste_noticeably(self):
        assert 0 < context._AX_TIMEOUT <= 0.3

    @staticmethod
    def chain(depth):
        """A focused element whose page (web area) is `depth` parents up."""
        node = AXNode("AXWebArea", url="https://deep.example", title="Deep")
        for _ in range(depth):
            node = AXNode("AXGroup", parent=node)
        return node

    def test_hop_limit_reaches_exactly_max_hops(self, ax):
        ax["app"].attrs["AXFocusedUIElement"] = self.chain(context._MAX_HOPS - 1)  # 60th node visited
        assert context._browser_page(1)[0] == "https://deep.example"

    def test_hop_limit_stops_after_max_hops(self, ax):
        ax["app"].attrs["AXFocusedUIElement"] = self.chain(context._MAX_HOPS)  # would be the 61st
        assert context._browser_page(1)[0] is None

    def test_max_hops_value(self):
        assert context._MAX_HOPS == 60

    def test_cyclic_parents_terminate(self, ax):
        a = AXNode("AXGroup")
        b = AXNode("AXGroup", parent=a)
        a.attrs["AXParent"] = b
        ax["app"].attrs["AXFocusedUIElement"] = a
        assert context._browser_page(1) == (None, None)  # bounded by _MAX_HOPS


class TestFrontmost:
    def test_no_frontmost_app(self, monkeypatch):
        set_frontmost(monkeypatch, None)
        assert context.frontmost() == {"app": None, "bundle_id": None, "url": None, "page_title": None}

    def test_non_browser_has_no_page(self, monkeypatch):
        set_frontmost(monkeypatch, FakeApp("Notes", "com.apple.Notes"))
        monkeypatch.setattr(context, "_browser_page", lambda pid: pytest.fail("not a browser"))
        assert context.frontmost() == {"app": "Notes", "bundle_id": "com.apple.Notes", "url": None, "page_title": None}

    def test_browser_includes_page(self, monkeypatch):
        set_frontmost(monkeypatch, FakeApp())
        monkeypatch.setattr(context, "_browser_page", lambda pid: ("https://x.com", "X"))
        info = context.frontmost()
        assert info["url"] == "https://x.com" and info["page_title"] == "X" and info["app"] == "Google Chrome"

    def test_include_page_false_skips_lookup(self, monkeypatch):
        set_frontmost(monkeypatch, FakeApp())
        monkeypatch.setattr(context, "_browser_page", lambda pid: pytest.fail("should not look up page"))
        assert context.frontmost(include_page=False)["url"] is None

    def test_lookup_errors_never_break_dictation(self, monkeypatch):
        set_frontmost(monkeypatch, FakeApp())

        def boom(pid):
            raise RuntimeError("AX hung")

        monkeypatch.setattr(context, "_browser_page", boom)
        assert context.frontmost()["url"] is None

    @pytest.mark.parametrize("bundle", ["com.apple.Safari", "com.google.Chrome", "company.thebrowser.Browser",
                                        "org.mozilla.firefox", "com.brave.Browser", "com.microsoft.edgemac"])
    def test_major_browsers_recognised(self, bundle):
        assert bundle in context.BROWSERS


class TextTargetNode:
    def __init__(self, role=None, editable=False, settable=False, selection=False):
        self.attrs = {"AXRole": role, "AXEditableAncestor": object() if editable else None,
                      "AXSelectedTextRange": object() if selection else None}
        self.settable = settable


@pytest.fixture
def focus(monkeypatch):
    """Fake the frontmost app's focused element: state["focused"] (or an AX error code)."""
    state = {"focused": None, "err": 0, "manual": []}
    app = object()

    def copy_attr(element, name, _):
        if element is app:
            if state["err"]:
                return state["err"], None
            return (0, state["focused"]) if state["focused"] is not None else (-25212, None)
        value = element.attrs.get(name)
        return (0, value) if value is not None else (-25212, None)

    monkeypatch.setattr(context.AS, "AXUIElementCreateApplication", lambda pid: app)
    monkeypatch.setattr(context.AS, "AXUIElementSetMessagingTimeout", lambda el, t: None)
    monkeypatch.setattr(context.AS, "AXUIElementSetAttributeValue", lambda el, name, v: state["manual"].append((name, v)))
    monkeypatch.setattr(context.AS, "AXUIElementCopyAttributeValue", copy_attr)
    monkeypatch.setattr(context.AS, "AXUIElementIsAttributeSettable",
                        lambda el, name, _: (0, el.settable) if name == "AXValue" else (-25205, False))
    return state


class TestTextTarget:
    @pytest.mark.parametrize("role", sorted(context.TEXT_ROLES))
    def test_text_roles(self, focus, role):
        focus["focused"] = TextTargetNode(role)
        assert context.text_target(1) == context.YES

    def test_contenteditable_in_a_browser(self, focus):
        focus["focused"] = TextTargetNode("AXGroup", editable=True)
        assert context.text_target(1) == context.YES

    def test_custom_view_with_editable_value_and_caret(self, focus):
        focus["focused"] = TextTargetNode("AXGroup", settable=True, selection=True)
        assert context.text_target(1) == context.YES

    @pytest.mark.parametrize("role", ["AXOutline", "AXWebArea", "AXList", "AXButton", "AXWindow"])
    def test_known_non_text_focus(self, focus, role):
        focus["focused"] = TextTargetNode(role)
        assert context.text_target(1) == context.NO

    def test_unfamiliar_role_gets_the_benefit_of_the_doubt(self, focus):
        focus["focused"] = TextTargetNode("AXGroup")
        assert context.text_target(1) == context.UNKNOWN

    def test_nothing_focused(self, focus):
        assert context.text_target(1) == context.NO

    def test_nothing_focused_in_electron_is_unknown(self, focus):
        assert context.text_target(1, electron=True) == context.UNKNOWN

    @pytest.mark.parametrize("err", [-25204, -25211, -25200])  # cannot complete, API disabled, failure
    def test_app_that_wont_answer(self, focus, err):
        focus["err"] = err
        assert context.text_target(1) == context.UNKNOWN

    def test_asks_electron_apps_to_build_their_tree(self, focus):
        context.text_target(1)
        assert focus["manual"] == [("AXManualAccessibility", True)]

    def test_exceptions_mean_unknown(self, focus, monkeypatch):
        monkeypatch.setattr(context.AS, "AXUIElementCreateApplication", lambda pid: 1 / 0)
        assert context.text_target(1) == context.UNKNOWN


class TestFocusedTextTarget:
    def test_no_frontmost_app(self, monkeypatch):
        set_frontmost(monkeypatch, None)
        assert context.focused_text_target() == context.NO

    @pytest.mark.parametrize("has_framework", [True, False])
    def test_detects_electron_from_the_bundle(self, monkeypatch, tmp_path, has_framework):
        bundle = tmp_path / "Some.app"
        (bundle / "Contents/Frameworks").mkdir(parents=True)
        if has_framework:
            (bundle / "Contents/Frameworks/Electron Framework.framework").mkdir()

        class App(FakeApp):
            def bundleURL(self):
                return NSURL.fileURLWithPath_(str(bundle))

        set_frontmost(monkeypatch, App())
        seen = []
        monkeypatch.setattr(context, "text_target", lambda pid, electron: seen.append((pid, electron)) or "x")
        assert context.focused_text_target() == "x" and seen == [(42, has_framework)]


class TestCopyText:
    def test_leaves_text_on_clipboard_without_cmd_v(self, board):
        board, posted = board
        paste.copy_text("Hi.")
        assert board.stringForType_(NSPasteboardTypeString) == "Hi." and posted == []
        assert "org.nspasteboard.ConcealedType" in board.types()


# --- paste -------------------------------------------------------------------------

@pytest.fixture
def board(monkeypatch):
    """A private, throwaway pasteboard standing in for the system clipboard; no real keystrokes."""
    pb = NSPasteboard.pasteboardWithUniqueName()

    class Pasteboard:  # module-level stand-in whose "general" pasteboard is the private one
        @staticmethod
        def generalPasteboard():
            return pb

    monkeypatch.setattr(paste, "NSPasteboard", Pasteboard)
    posted = []
    monkeypatch.setattr(paste, "_post_cmd_v", lambda: posted.append(pb.stringForType_(NSPasteboardTypeString)))
    yield pb, posted
    pb.releaseGlobally()


def put(pb, text, extra_type=None, extra=b""):
    pb.clearContents()
    pb.setString_forType_(text, NSPasteboardTypeString)
    if extra_type:
        pb.setData_forType_(NSData.dataWithBytes_length_(extra, len(extra)), extra_type)


class TestPaste:
    def test_pastes_text_via_cmd_v(self, board, monkeypatch):
        board, posted = board
        monkeypatch.setattr(paste.AppHelper, "callLater", lambda delay, fn: None)  # keep dictated text
        paste.paste_text("Hello there.")
        assert posted == ["Hello there."]
        assert board.stringForType_(NSPasteboardTypeString) == "Hello there."

    def test_paste_contains_only_dictation_during_paste(self, board, monkeypatch):
        board, posted = board
        put(board, "old", "com.test.custom", b"x")
        monkeypatch.setattr(paste.AppHelper, "callLater", lambda delay, fn: None)
        paste.paste_text("dictated")
        # nothing from the previous clipboard may leak into what the app pastes
        assert "com.test.custom" not in set(board.types())
        assert len(board.pasteboardItems()) == 1

    def test_timing_and_key_spec(self):
        assert paste.RESTORE_AFTER == 0.5  # long enough for Electron apps, short enough to feel instant
        assert paste.KEY_V == 9  # kVK_ANSI_V

    def test_dictated_text_marked_private(self, board, monkeypatch):
        board, posted = board
        monkeypatch.setattr(paste.AppHelper, "callLater", lambda delay, fn: None)
        paste.paste_text("secret")
        types = set(board.types())
        for t in paste._PRIVATE_TYPES:
            assert t in types

    def test_previous_clipboard_restored(self, board):
        board, posted = board
        put(board, "what I copied before", "com.test.custom", b"\x01\x02")
        paste.paste_text("dictated")
        assert board.stringForType_(NSPasteboardTypeString) == "what I copied before"
        assert bytes(board.dataForType_("com.test.custom")) == b"\x01\x02"
        assert "org.nspasteboard.TransientType" not in set(board.types())

    def test_restore_scheduled_after_delay(self, board, monkeypatch):
        board, posted = board
        delays = []
        monkeypatch.setattr(paste.AppHelper, "callLater", lambda delay, fn: delays.append(delay))
        paste.paste_text("x")
        assert delays == [paste.RESTORE_AFTER]

    def test_user_copy_during_paste_is_not_overwritten(self, board, monkeypatch):
        board, posted = board
        put(board, "old")
        pending = []
        monkeypatch.setattr(paste.AppHelper, "callLater", lambda delay, fn: pending.append(fn))
        paste.paste_text("dictated")
        put(board, "copied right after")  # user copies something within RESTORE_AFTER
        pending[0]()
        assert board.stringForType_(NSPasteboardTypeString) == "copied right after"

    def test_empty_clipboard_is_restored_empty(self, board):
        board, posted = board
        board.clearContents()
        paste.paste_text("dictated")
        assert board.stringForType_(NSPasteboardTypeString) is None

    def test_multiple_items_round_trip(self, board):
        board, posted = board
        from AppKit import NSPasteboardItem
        board.clearContents()
        items = []
        for text in ("one", "two"):
            item = NSPasteboardItem.alloc().init()
            item.setString_forType_(text, NSPasteboardTypeString)
            items.append(item)
        board.writeObjects_(items)
        snap = paste._snapshot(board)
        assert len(snap) == 2
        paste._restore(board, snap)
        assert [i.stringForType_(NSPasteboardTypeString) for i in board.pasteboardItems()] == ["one", "two"]

    def test_unicode_text(self, board, monkeypatch):
        board, posted = board
        monkeypatch.setattr(paste.AppHelper, "callLater", lambda delay, fn: None)
        paste.paste_text("naïve café — 😀")
        assert posted == ["naïve café — 😀"]


class TestPostCmdV:
    def test_posts_v_down_and_up_with_only_command(self, monkeypatch):
        posted = []
        monkeypatch.setattr(paste.Quartz, "CGEventPost", lambda tap, e: posted.append((tap, e)))
        paste._post_cmd_v()
        assert len(posted) == 2
        (tap1, down), (tap2, up) = posted
        assert tap1 == tap2 == Quartz.kCGSessionEventTap
        for e, is_down in ((down, True), (up, False)):
            assert Quartz.CGEventGetIntegerValueField(e, Quartz.kCGKeyboardEventKeycode) == paste.KEY_V
            assert Quartz.CGEventGetType(e) == (Quartz.kCGEventKeyDown if is_down else Quartz.kCGEventKeyUp)
            flags = Quartz.CGEventGetFlags(e)
            assert flags & Quartz.kCGEventFlagMaskCommand
            assert not flags & Quartz.kCGEventFlagMaskSecondaryFn  # fn must not leak into the paste
