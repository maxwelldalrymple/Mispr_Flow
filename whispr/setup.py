"""Mandatory first-run setup: every required model must be installed before dictation works.

Downloads run on a background thread; progress is exposed as a 0..1 fraction the widget
draws, and completion/failure are delivered on the main thread.
"""

from PyObjCTools import AppHelper

from .models import CLEANUP_MODEL, DEFAULT_MODEL, ensure_model, is_installed
from .threads import start_daemon

REQUIRED = (DEFAULT_MODEL, CLEANUP_MODEL)


def missing(specs=REQUIRED):
    return [spec for spec in specs if not is_installed(spec)]


def install_async(on_progress, on_done, on_error, specs=REQUIRED):
    """Download whatever is missing. `on_progress(fraction)` is called from the worker thread
    and must only store the value; `on_done()` / `on_error(message)` run on the main thread."""
    todo = missing(specs)
    total = sum(spec.size for spec in todo) or 1

    def work():
        finished = 0
        try:
            for spec in todo:
                ensure_model(spec, progress=lambda done, _t, base=finished: on_progress((base + done) / total))
                finished += spec.size
            AppHelper.callAfter(on_done)
        except Exception as e:
            AppHelper.callAfter(on_error, str(e))

    start_daemon(work, "model-setup")
