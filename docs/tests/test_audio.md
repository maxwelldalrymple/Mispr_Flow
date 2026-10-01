# `tests/test_audio.py`

61 tests. Source: [`tests/test_audio.py`](../../tests/test_audio.py).


## TestSecureAudioBuffer

- `test_starts_empty_zeroed_and_locked`: starts empty zeroed and locked
- `test_dtype_is_float32`: dtype is float32
- `test_append_stores_samples`: append stores samples
- `test_successive_appends_concatenate`: successive appends concatenate
- `test_append_past_capacity_clips_and_reports_full`: append past capacity clips and reports full
- `test_append_empty`: append empty
- `test_view_is_zero_copy`: view is zero copy
- `test_wipe_zeroes_written_region_and_resets`: wipe zeroes written region and resets
- `test_wipe_on_empty_buffer`: wipe on empty buffer
- `test_close_zeroes_everything_and_unlocks`: close zeroes everything and unlocks
- `test_close_is_idempotent`: close is idempotent
- `test_reusable_after_wipe`: reusable after wipe

## TestMemoryLocking

- `test_locks_exact_buffer_size`: locks exact buffer size
- `test_close_unlocks_once`: close unlocks once
- `test_mlock_failure_is_reported_and_not_unlocked`: mlock failure is reported and not unlocked
- `test_mlock_success_is_silent`: mlock success is silent
- `test_default_capacity_is_ten_minutes`: default capacity is ten minutes

## TestRecorder

- `test_prepare_builds_engine_without_starting_mic`: prepare builds engine without starting mic
- `test_prepare_failure_leaves_no_engine`: prepare failure leaves no engine
- `test_start_reuses_prepared_engine`: start reuses prepared engine
- `test_start_builds_engine_if_needed`: start builds engine if needed
- `test_samples_recorded_only_while_capturing`: samples recorded only while capturing
- `test_stop_flushes_resampler_tail`: stop flushes resampler tail
- `test_resampler_built_for_engine_rate`: resampler built for engine rate
- `test_stop_stops_engine_in_background_worker`: stop stops engine in background worker
- `test_stop_when_idle_does_not_touch_engine`: stop when idle does not touch engine
- `test_stop_never_blocks_even_if_coreaudio_hangs`: The regression: a deadlocked engine stop must not freeze the caller (the UI).
- `test_hung_stop_switches_to_fresh_engine`: hung stop switches to fresh engine
- `test_restart_waits_for_previous_stop`: restart waits for previous stop
- `test_start_while_recording_restarts_cleanly`: start while recording restarts cleanly
- `test_start_resets_level`: start resets level
- `test_start_retries_once_with_fresh_engine`: start retries once with fresh engine
- `test_start_tries_exactly_twice`: start tries exactly twice
- `test_start_gives_up_after_two_failures`: start gives up after two failures
- `test_successful_retry_reports_no_error`: successful retry reports no error
- `test_stop_turns_mic_off_but_keeps_audio`: stop turns mic off but keeps audio
- `test_wipe_returns_stats_and_zeroes`: wipe returns stats and zeroes
- `test_wipe_empty`: wipe empty
- `test_audio_is_view_of_buffer`: audio is view of buffer
- `test_recording_false_initially`: recording false initially
- `test_level_ignores_t_argument`: level ignores t argument

## TestLevel

- `test_dbfs_to_level_mapping`: dbfs to level mapping
- `test_mapping_constants`: mapping constants
- `test_silence_keeps_level_zero`: silence keeps level zero
- `test_level_saturates_at_one`: level saturates at one
- `test_level_decays_slower_than_it_rises`: level decays slower than it rises
- `test_empty_chunk_leaves_level`: empty chunk leaves level
- `test_level_not_updated_after_stop`: level not updated after stop

## TestInputDevice

- `test_built_in_mic`: built in mic
- `test_bluetooth_headset_is_not_built_in`: bluetooth headset is not built in
- `test_no_microphone`: no microphone
- `test_real_lookup_returns_a_pair`: real lookup returns a pair

## TestResampling

- `test_real_resampler_converts_44k1_to_16k`: real resampler converts 44k1 to 16k
- `test_tap_size_and_stop_timeout`: tap size and stop timeout

## TestMicEngine

- `test_prepare_taps_input_bus_zero_at_native_format`: prepare taps input bus zero at native format
- `test_tap_delivers_channel_zero_at_engine_rate`: tap delivers channel zero at engine rate
- `test_tap_uses_frame_length_not_capacity`: tap uses frame length not capacity
- `test_empty_tap_buffer_is_ignored`: empty tap buffer is ignored
- `test_start_reports_success`: start reports success
- `test_stop`: stop
- `test_default_engine_is_avaudioengine`: default engine is avaudioengine
