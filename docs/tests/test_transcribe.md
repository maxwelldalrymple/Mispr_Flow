# `tests/test_transcribe.py`

25 tests. Source: [`tests/test_transcribe.py`](../../tests/test_transcribe.py).


## TestCleanText

- `test_cases`: cases
- `test_keeps_normal_punctuation`: keeps normal punctuation

## TestGates

Boundary-value tables for the two gates that stop Whisper hallucinating on non-speech.

- `test_minimum_length`: minimum length
- `test_silence_threshold`: silence threshold
- `test_thresholds_are_the_documented_values`: thresholds are the documented values
- `test_negative_only_signal_counts_as_loud`: negative only signal counts as loud
- `test_waits_for_model_to_finish_loading`: waits for model to finish loading
- `test_model_unavailable_returns_empty`: model unavailable returns empty
- `test_audio_is_passed_without_copy`: audio is passed without copy
- `test_segments_joined_and_cleaned`: segments joined and cleaned
- `test_language_is_configurable`: language is configurable

## TestTimedSegments

Meeting chunks get Whisper's segments with times, to split where the speaker changes.

- `test_seconds_and_clean_text`: seconds and clean text
- `test_silence_and_short_audio_have_none`: silence and short audio have none

## TestEnsureLoaded

- `test_loads_once_on_the_calling_thread`: loads once on the calling thread
- `test_not_again_while_a_background_load_runs`: not again while a background load runs

## TestTranscribeAsync

- `test_without_post`: without post
- `test_runs_on_named_daemon_worker`: runs on named daemon worker
- `test_post_processing_applied`: post processing applied
- `test_post_skipped_for_empty_transcript`: post skipped for empty transcript
- `test_elapsed_includes_post_processing`: elapsed includes post processing

## TestTranscriberLifecycle

- `test_ready_property`: ready property
- `test_load_configures_quiet_model`: load configures quiet model
- `test_load_warms_up_with_one_second_of_silence`: load warms up with one second of silence
- `test_load_failure_recorded`: load failure recorded
- `test_load_async_uses_named_daemon_worker`: load async uses named daemon worker
