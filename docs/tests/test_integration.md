# `tests/test_integration.py`

6 tests. Source: [`tests/test_integration.py`](../../tests/test_integration.py).


## (module)

End-to-end checks with the real Whisper and Gemma models (slow, ~30 s).

- `test_whisper_transcribes_speech`: whisper transcribes speech
- `test_whisper_skips_silence`: whisper skips silence
- `test_cleanup_is_faithful`: cleanup is faithful
- `test_full_pipeline_speech_to_clean_text`: full pipeline speech to clean text
- `test_installed_models_match_their_specs`: Verifies the hard-coded sizes and checksums against the real downloaded files.
- `test_real_microphone_start_stop_soak`: Regression for the PortAudio deadlock: many real start/stop cycles, each call watched.
