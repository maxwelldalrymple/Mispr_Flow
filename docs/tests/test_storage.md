# `tests/test_storage.py`

26 tests. Source: [`tests/test_storage.py`](../../tests/test_storage.py).


## (module)

- `test_set_transcript_keeps_what_was_heard`: set transcript keeps what was heard

## TestStem

- `test_milliseconds`: milliseconds
- `test_zero_padded_fields`: zero padded fields
- `test_sorts_chronologically`: sorts chronologically

## TestDataRoot

- `test_source_checkout_uses_project_folder`: source checkout uses project folder
- `test_packaged_app_uses_application_support`: packaged app uses application support

## TestSaveRecording

- `test_files_named_by_start_time_in_day_folder`: files named by start time in day folder
- `test_wav_format`: wav format
- `test_samples_scaled_to_int16`: samples scaled to int16
- `test_out_of_range_samples_clipped`: out of range samples clipped
- `test_does_not_modify_input_audio`: does not modify input audio
- `test_metadata_fields`: metadata fields
- `test_timestamps_include_timezone_offset`: timestamps include timezone offset
- `test_duration_precision`: duration precision
- `test_recorded_in_keeps_only_app_fields`: recorded in keeps only app fields
- `test_recorded_in_missing_keys_become_null`: recorded in missing keys become null
- `test_pasted_into_stored_verbatim`: pasted into stored verbatim
- `test_cancelled_recording_has_no_paste_target`: cancelled recording has no paste target
- `test_raw_transcript_defaults_to_transcript`: raw transcript defaults to transcript
- `test_raw_transcript_and_cleanup_recorded`: raw transcript and cleanup recorded
- `test_json_is_pretty_printed_with_two_spaces`: json is pretty printed with two spaces
- `test_unicode_preserved_not_escaped`: unicode preserved not escaped
- `test_word_count_ignores_extra_whitespace`: word count ignores extra whitespace
- `test_two_recordings_same_second_do_not_collide`: two recordings same second do not collide
- `test_recordings_on_different_days_get_different_folders`: recordings on different days get different folders
- `test_empty_audio_still_writes_valid_files`: empty audio still writes valid files
