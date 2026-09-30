"""Where the user is dictating: frontmost app and, in browsers, the page URL and title.

Uses the Accessibility API (already granted for the fn tap and paste), so no extra
per-browser Automation prompts are needed, unlike AppleScript.
"""

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
