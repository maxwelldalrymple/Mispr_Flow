"""Background work. Every worker is a daemon so a stuck model load or download can
never keep the app from quitting."""

import threading


def start_daemon(target, name):
    thread = threading.Thread(target=target, name=name, daemon=True)
    thread.start()
    return thread
