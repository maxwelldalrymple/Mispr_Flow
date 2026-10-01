# `tests/`: the Python test suite

`pytest`, about 13 s.

- **Fakes:** `conftest.py` fakes the mic, models, clipboard, sounds and screens, and redirects settings and recordings to temp folders.
- **Golden images:** `golden/` holds them, regenerated with `UPDATE_GOLDEN=1`.
- **What each file covers:** see [docs/testing.md](../docs/testing.md).
- **Every single test with what it checks:** the latest `logs/*_test-catalog.md`.
