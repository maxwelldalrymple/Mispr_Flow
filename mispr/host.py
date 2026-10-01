"""Talking to the Swift app that hosts the engine (run with MISPR_HOSTED=1).

One JSON object per line. Engine -> app on stdout, each line prefixed with "@mispr " (the
debug log goes to stderr, so the two never mix). App -> engine on stdin, e.g.
{"cmd": "open_setup"}. When stdin closes, the app is gone and the engine quits with it.
"""

import json
import os
import sys

from PyObjCTools import AppHelper

from . import threads

PREFIX = "@mispr "

_channel = None  # our own copy of stdout; see open_channel()


def open_channel():
    """Duplicate stdout for messages to the app. Call before any model loads: llama.cpp
    points file descriptor 1 at /dev/null while it loads (on a worker thread), which would
    silently swallow anything written to stdout then, like the hello event."""
    global _channel
    if _channel is None:
        _channel = os.fdopen(os.dup(sys.stdout.fileno()), "w", buffering=1)
    return _channel


def hosted():
    return os.environ.get("MISPR_HOSTED") == "1"


def send(event, out=None, **fields):
    out = out or _channel or sys.stdout
    out.write(PREFIX + json.dumps({"event": event, **fields}) + "\n")
    out.flush()


def parse(line):
    """(command, arguments) from one stdin line, or (None, {}) for blank or malformed lines.
    Arguments are the message's other keys, e.g. {"cmd": "try_prompt", "text": "…"}."""
    try:
        message = json.loads(line)
    except ValueError:
        return None, {}
    cmd = message.get("cmd") if isinstance(message, dict) else None
    if not isinstance(cmd, str):
        return None, {}
    return cmd, {k: v for k, v in message.items() if k != "cmd"}


def listen(handlers, on_eof, stream=None, call=AppHelper.callAfter, start=threads.start_daemon):
    """Read commands on a daemon thread and run their handlers on the main thread."""
    stream = stream or sys.stdin

    def run():
        for line in stream:
            cmd, args = parse(line)
            handler = handlers.get(cmd)
            if handler is not None:
                call(lambda handler=handler, args=args: handler(**args))
            elif cmd is not None:
                print(f"mispr: unknown host command {cmd!r}", file=sys.stderr)
        call(on_eof)

    return start(run, "host-stdin")
