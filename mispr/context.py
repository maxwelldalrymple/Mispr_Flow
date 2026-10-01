"""Where the user is dictating: frontmost app and, in browsers, the page URL and title.

Uses the Accessibility API (already granted for the fn tap and paste), so no extra
per-browser Automation prompts are needed, unlike AppleScript.
"""

from pathlib import Path

import ApplicationServices as AS
from AppKit import NSWorkspace

BROWSERS = {
    "com.apple.Safari",
    "com.apple.SafariTechnologyPreview",
    "com.google.Chrome",
    "com.google.Chrome.canary",
    "com.brave.Browser",
    "com.microsoft.edgemac",
    "company.thebrowser.Browser",  # Arc
    "company.thebrowser.dia",
    "org.mozilla.firefox",
    "com.operasoftware.Opera",
    "com.vivaldi.Vivaldi",
    "org.chromium.Chromium",
}

_AX_TIMEOUT = 0.3  # seconds; never let a hung app stall the paste
_MAX_HOPS = 60


def _attr(element, name):
    if element is None:
        return None
    err, value = AS.AXUIElementCopyAttributeValue(element, name, None)
    return value if err == 0 else None


def _url_string(value):
    if value is None:
        return None
    return str(value.absoluteString()) if hasattr(value, "absoluteString") else str(value)


def _browser_page(pid):
    """(url, title) of the page holding keyboard focus, or of the focused window."""
    app = AS.AXUIElementCreateApplication(pid)
    AS.AXUIElementSetMessagingTimeout(app, _AX_TIMEOUT)
    # Walk up from the focused text field; the outermost web area is the page itself
    # (inner ones are iframes, e.g. an embedded editor).
    url = title = None
    node, hops = _attr(app, "AXFocusedUIElement"), 0
    while node is not None and hops < _MAX_HOPS:
        if _attr(node, "AXRole") == "AXWebArea":
            found = _url_string(_attr(node, "AXURL"))
            if found:
                url, title = found, _attr(node, "AXTitle") or title
        node, hops = _attr(node, "AXParent"), hops + 1
    if url is None:  # e.g. typing in the address bar: fall back to the window's document
        window = _attr(app, "AXFocusedWindow")
        url = _url_string(_attr(window, "AXDocument"))
        title = _attr(window, "AXTitle")
    return url, (str(title) if title else None)


# --- Is there somewhere to paste? ------------------------------------------------------------

YES, NO, UNKNOWN = "yes", "no", "unknown"
TEXT_ROLES = {"AXTextField", "AXTextArea", "AXComboBox", "AXSearchField"}
_NO_VALUE = -25212  # kAXErrorNoValue: the app answered, and nothing has keyboard focus


def _is_text_input(element):
    if _attr(element, "AXRole") in TEXT_ROLES:
        return True
    if _attr(element, "AXEditableAncestor") is not None:  # contenteditable in WebKit/Chromium
        return True
    err, settable = AS.AXUIElementIsAttributeSettable(element, "AXValue", None)
    return err == 0 and bool(settable) and _attr(element, "AXSelectedTextRange") is not None


def text_target(pid, electron=False):
    """YES if app `pid` has a focused text input, NO if it clearly has none (e.g. Finder,
    the desktop, a web page with nothing focused), UNKNOWN if the app won't say.

    Native apps and browsers report focus reliably, so anything that isn't a text input is
    NO there (the desktop, a Finder window, a web page with no field clicked). Electron apps
    (VS Code, Slack, Claude...) can report "nothing focused" or a bare container while their
    editor has the caret, so for them only known non-text roles are NO and the rest is
    UNKNOWN. Callers paste on UNKNOWN.
    """
    try:
        app = AS.AXUIElementCreateApplication(pid)
        AS.AXUIElementSetMessagingTimeout(app, _AX_TIMEOUT)
        # Electron apps only build their accessibility tree when asked to.
        AS.AXUIElementSetAttributeValue(app, "AXManualAccessibility", True)
        err, focused = AS.AXUIElementCopyAttributeValue(app, "AXFocusedUIElement", None)
        if err == _NO_VALUE:
            return UNKNOWN if electron else NO
        if err != 0 or focused is None:
            return UNKNOWN
        if _is_text_input(focused):
            return YES
        if not electron:
            return NO
        return NO if _attr(focused, "AXRole") in NOT_TEXT_ROLES else UNKNOWN
    except Exception:
        return UNKNOWN


NOT_TEXT_ROLES = {
    "AXWebArea", "AXList", "AXOutline", "AXTable", "AXBrowser", "AXButton", "AXWindow",
    "AXApplication", "AXImage", "AXStaticText", "AXLink", "AXCheckBox", "AXRadioButton",
    "AXPopUpButton", "AXMenuButton", "AXTabGroup", "AXSlider", "AXCell", "AXRow", "AXToolbar",
}


def _is_electron(app):
    url = app.bundleURL()
    return url is not None and (Path(str(url.path())) / "Contents/Frameworks/Electron Framework.framework").exists()


def focused_text_target():
    """(answer, why) for the frontmost app: text_target() plus a note for the debug log."""
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return NO, "no frontmost app"
    try:
        electron = _is_electron(app)
    except Exception:
        electron = True  # can't tell: take the cautious answer
    return text_target(app.processIdentifier(), electron), f"{app.localizedName()}{' (Electron)' if electron else ''}"


def is_browser(info):
    """True for a frontmost() result that is a web browser."""
    return bool(info) and info.get("bundle_id") in BROWSERS


def focus_chain(limit=4):
    """Roles from the focused element up ("AXGroup < AXWebArea < ..."), for the debug log."""
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return "nothing"
    try:
        ax = AS.AXUIElementCreateApplication(app.processIdentifier())
        AS.AXUIElementSetMessagingTimeout(ax, _AX_TIMEOUT)
        node, roles = _attr(ax, "AXFocusedUIElement"), []
        while node is not None and len(roles) < limit:
            roles.append(str(_attr(node, "AXRole")))
            node = _attr(node, "AXParent")
        return " < ".join(roles) or "nothing"
    except Exception as e:
        return f"unreadable ({e})"


def frontmost(include_page=True):
    """{"app", "bundle_id", "url", "page_title"} for the frontmost app."""
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return {"app": None, "bundle_id": None, "url": None, "page_title": None}
    bundle = app.bundleIdentifier()
    info = {"app": app.localizedName(), "bundle_id": bundle, "url": None, "page_title": None}
    if include_page and bundle in BROWSERS:
        try:
            info["url"], info["page_title"] = _browser_page(app.processIdentifier())
        except Exception:
            pass  # context is best-effort; never block dictation on it
    return info
