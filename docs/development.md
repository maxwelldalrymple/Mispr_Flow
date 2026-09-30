# Development

## Setup

Follow [getting-started.md](getting-started.md), then add the test tools:

```bash
.venv/bin/pip install -r requirements-dev.txt
```

## Running

```bash
MISPR_DEBUG=1 .venv/bin/python -m mispr
```

Restart after code changes: Python modules and the models load once at startup. Stop with `kill $(pgrep -f "m mispr")` (SIGTERM runs the clean shutdown).

## Tests

```bash
.venv/bin/python -m pytest                                    # all unit tests (~8 s)
.venv/bin/python -m pytest tests/test_audio.py                # just what you changed
MISPR_INTEGRATION=1 .venv/bin/python -m pytest tests/test_integration.py   # real models + mic
```

Run the test file that covers the module you changed. Run the full suite when a change is cross-cutting (renames, `conftest.py`, shared helpers) or before merging.

| Module | Tests |
|---|---|
| `widget.py` | `tests/test_widget.py` |
| `audio.py` | `tests/test_audio.py` |
| `hotkey.py` | `tests/test_hotkey.py` |
| `cleanup.py` | `tests/test_cleanup.py` |
| `transcribe.py` | `tests/test_transcribe.py` |
| `storage.py` | `tests/test_storage.py` |
| `context.py`, `paste.py` | `tests/test_context_paste.py` |
| `screens.py`, `sounds.py`, `app.py` | `tests/test_screens_sounds_app.py` |
| `settings.py`, `models.py`, `setup.py`, `levels.py` | `tests/test_settings_models_setup.py` |
| `draw.py` | `tests/test_draw.py` |
| `threads.py` | `tests/test_threads.py` |

### Rules the suite enforces

- **No real side effects.** `conftest.py` redirects the settings, recordings, and models folders to `tmp_path`, runs background threads inline, runs `callAfter` synchronously, and provides fakes: `FakeRecorder`, `FakeTranscriber`, `FakeCleaner`, `SpySounds`, `FakePanel`, `FakeView`, `FakeScreen`, a per-test pointer, and a private pasteboard. Tests never press keys, touch the clipboard, or open the mic.
- **Warnings are errors** (`filterwarnings = error` in `pyproject.toml`), so leaked files and deprecations fail fast.
- **Random order.** `pytest-randomly` shuffles tests on every run, so a hidden dependency between tests surfaces quickly. To reproduce a failure: `pytest -p randomly --randomly-seed=<seed from the header>`.

### Golden files

`tests/golden/` holds the widget layout snapshot, waveform characterization data, and PNGs of every widget state and drawing primitive. When you change the widget's look on purpose:

```bash
UPDATE_GOLDEN=1 .venv/bin/python -m pytest tests/test_widget.py tests/test_draw.py
```

Then **open the new PNGs and check them** before committing. A missing golden file fails the test once (after creating it) so it can't be approved silently.

### Writing tests

- Inject dependencies instead of patching internals: `Cleaner(clock=...)`, `Transcriber(clock=...)`, `Recorder(engine_factory=..., resampler_factory=...)`, `MicEngine(..., engine_cls=...)`, `_single_instance_lock(path)`, `setup.install_async(..., specs=...)`.
- To fake an Objective-C class, replace the module's reference to it (`monkeypatch.setattr(module, "NSScreen", Fake)`). PyObjC can't restore patched methods on real ObjC classes.
- Test boundaries on both sides (just below / at / just above), and assert product decisions as literal values.

## Quality tools

| Tool | What it does |
|---|---|
| `tools/stress_test.py LOG.md [round ...]` | Repetition, random-order, parallel (8 workers), warnings-as-errors, and coverage rounds. Appends a report to `LOG.md` and every run's full output to `LOG.raw.log` |
| `tools/mutation_test.py LOG.md [module ...]` | Plants one bug at a time (flipped comparisons, swapped operators, nudged constants, negated `if`s, dropped calls) in throwaway repo copies and checks the tests catch it |
| `tools/eval_cleanup.py [MODEL.gguf ...]` | Scores a cleanup model on 27 cases: invented words (must be 0), lost key words, leftover fillers, latency |
| `tools/render_states.py OUT_DIR` | Renders every widget state to PNG for review |

Save reports in `logs/` as `YYYY-MM-DD_HH-MM-SS_<topic>.md`.

## Branches and releases

- Work on `build`; merge into `main` with a GitHub PR (merge commit). After a merge, fast-forward `build` to `main` so it doesn't show as "behind".
- Feature and milestone branches (`Rebranding`, `planning`) follow the same PR flow.
- Tag milestones: `git tag -a vX.Y-name -m "..." && git push origin vX.Y-name` (existing: `v0.1-dictation`, `v0.2-llm-cleanup`).
- Commit messages: imperative summary line, then a body explaining why.

## Changing models

1. Get the file's size and SHA-256 from the Hugging Face API: `https://huggingface.co/api/models/<repo>/tree/main` (`size`, `lfs.oid`).
2. Add a `ModelSpec` in `mispr/models.py` and point `DEFAULT_MODEL` or `CLEANUP_MODEL` at it.
3. For cleanup models, run `tools/eval_cleanup.py` and require **0 invented words**.
4. Update `test_configured_models` and the integration checksum test.
