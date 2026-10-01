# Contributing to Mispr Flow

Thanks for helping. Mispr Flow is a private, on-device dictation, voice-command and meeting-notes app, so every change has to keep three promises: **no audio or text leaves the Mac**, **cleanup never adds words the speaker didn't say**, and **nothing acts on the Mac on a guess** (no app launched on a weak match, no shell word the speaker didn't say).

## Get set up

Follow [docs/getting-started.md](docs/getting-started.md), then:

```bash
.venv/bin/pip install -r requirements-dev.txt
MISPR_DEBUG=1 .venv/bin/python -m mispr
```

[docs/architecture.md](docs/architecture.md) explains how the pieces fit together; [docs/features/](docs/features/) explains every feature; [knowledge-base/](knowledge-base/README.md) has the history and the reasons behind decisions.

## Making a change

1. Branch from `main`, one branch per change.
2. Keep changes focused; match the surrounding code's style and comment density.
3. Add or update tests, in Python (`tests/`) and Swift (`macos/Tests/`). Tests must never touch the real microphone, clipboard, keyboard, models, windows, recordings, or settings; use the fakes in `tests/conftest.py` and `macos/Tests/MisprFlowTests/Helpers.swift`. See [docs/development.md](docs/development.md) and [docs/testing.md](docs/testing.md).
4. Run the tests for what you changed (for example `pytest tests/test_audio.py`), and the full suite before opening a PR:
   ```bash
   .venv/bin/python -m pytest
   ```
   Warnings fail the run. Tests run in random order.
5. If you changed how the widget looks, regenerate the golden images with `UPDATE_GOLDEN=1`, **look at them**, and commit them.
6. If you changed the cleanup prompt or model, run `tools/eval_cleanup.py`: invented words must stay at **0**.
7. Write a report in `logs/` (`YYYY-MM-DD_HH-MM-SS_<topic>.md`): what changed, why, measurements, and the tests you ran and what they check.
8. Update the docs (README, `plan.md`, `docs/`, the folder README, the knowledge base) and add a line to [CHANGELOG.md](CHANGELOG.md). Then run `python tools/test_catalog.py` (if tests changed) and `python tools/build_knowledge_base.py`.

## Pull requests

- Title: imperative and specific ("Swallow the globe key to stop the emoji picker").
- Description: what changed, why, and how you tested it (include real-mic or real-model checks if relevant).
- PRs are merged into `main` with a merge commit.

## Reporting bugs

Include your Mac model, macOS version, what you did, what happened, and the output of a run with `MISPR_DEBUG=1`. For a freeze, attach a thread sample: `sample $(pgrep -f "m mispr") 3 -file ~/Desktop/mispr-hang.txt` (see [docs/troubleshooting.md](docs/troubleshooting.md)).

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
