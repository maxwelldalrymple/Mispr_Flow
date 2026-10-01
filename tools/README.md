# `tools/`

| Script | Use |
|---|---|
| `build_app.sh [--open]` | Build and sign `build/Mispr Flow.app` (`--open` launches it) |
| `make_signing_cert.sh`, `trust_signing_cert.sh` | A local code-signing certificate, so macOS permissions survive rebuilds |
| `build_knowledge_base.py` | Write `knowledge-base/ALL-IN-ONE.md` from the knowledge base and guides |
| `test_catalog.py` | Write `logs/<time>_test-catalog.md`: every Python and Swift test with what it checks |
| `stress_test.py` | Repeated, random-order and parallel test runs |
| `mutation_test.py` | Plant bugs and check the tests catch them |
| `eval_cleanup.py` | Score cleanup models (invented words must be zero) |
| `make_sounds.py` | Generate the original sound cues into `mispr/assets/sounds/` |
| `make_icon.py` | Build `AppIcon.icns` from the logo |
| `make_sample_dictations.py`, `make_sample_meetings.py` | Sample history and meetings for screenshots and testing |
| `render_states.py` | Render every widget state to images |
