import threading

from mispr.threads import start_daemon


def test_runs_target_on_a_new_named_daemon_thread():
    seen = {}
    done = threading.Event()

    def work():
        seen["thread"] = threading.current_thread()
        done.set()

    thread = start_daemon(work, "unit-test-worker")
    assert done.wait(2)
    thread.join(2)
    assert seen["thread"] is thread and thread is not threading.main_thread()
    assert thread.daemon is True  # never blocks the app from quitting
    assert thread.name == "unit-test-worker"


def test_returns_already_started_thread():
    gate = threading.Event()
    thread = start_daemon(gate.wait, "unit-test-gate")
    assert thread.is_alive()
    gate.set()
    thread.join(2)
    assert not thread.is_alive()
