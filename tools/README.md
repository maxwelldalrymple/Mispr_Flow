# `tools/`

| Script | Use |
|---|---|
| `build_app.sh [--open]` | Build and sign `build/Mispr Flow.app` (`--open` launches it) |
| `build_dmg.sh` | Build `dist/Mispr-Flow-<version>.dmg` and its `.sha256`: bundled Python 3.13 with the pinned requirements (llama.cpp built for macOS 14+, no curl/OpenSSL), the engine (git-tracked files only), ad-hoc signed. Fails if any recording, note, setting, model, or this Mac's paths or name end up inside |
| `screenshots.sh` | Render every window and state (all themes, light and dark) into `docs/screenshots/` with made-up sample data; see its README for the naming |
| `make_signing_cert.sh`, `trust_signing_cert.sh` | A local code-signing certificate, so macOS permissions survive rebuilds |
| `export_chat_history.py` | Export the Claude Code conversation into `knowledge-base/07-chat-log.md` and `08-your-messages.md` |
| `build_knowledge_base.py` | Write `knowledge-base/ALL-IN-ONE.md` from the knowledge base and guides |
| `test_catalog.py` | Write `logs/<time>_test-catalog.md`: every Python and Swift test with what it checks |
| `stress_test.py` | Repeated, random-order and parallel test runs |
| `mutation_test.py` | Plant bugs and check the tests catch them |
| `eval_cleanup.py` | Score cleanup models (invented words must be zero) |
| `make_sounds.py` | Generate the original sound cues into `mispr/assets/sounds/` |
| `make_icon.py` | Build `AppIcon.icns` from the logo |
| `make_sample_dictations.py`, `make_sample_meetings.py` | Sample history and meetings for screenshots and testing |
| `render_states.py` | Render every widget state to images |
