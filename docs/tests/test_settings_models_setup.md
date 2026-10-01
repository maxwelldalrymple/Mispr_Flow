# `tests/test_settings_models_setup.py`

49 tests. Source: [`tests/test_settings_models_setup.py`](../../tests/test_settings_models_setup.py).


## TestSettings

- `test_defaults_when_file_missing`: defaults when file missing
- `test_save_then_load_roundtrip`: save then load roundtrip
- `test_save_creates_parent_folders`: save creates parent folders
- `test_save_creates_missing_grandparent_folders`: save creates missing grandparent folders
- `test_save_twice_overwrites`: save twice overwrites
- `test_saved_file_is_human_readable`: saved file is human readable
- `test_saved_file_is_readable_json`: saved file is readable json
- `test_save_nickname_keeps_other_settings`: save nickname keeps other settings
- `test_partial_file_fills_defaults`: partial file fills defaults
- `test_unknown_keys_ignored`: unknown keys ignored
- `test_corrupt_file_falls_back_to_defaults`: corrupt file falls back to defaults

## TestModelSpec

- `test_default_repo_is_whisper_cpp`: default repo is whisper cpp
- `test_custom_repo_url`: custom repo url
- `test_path_is_in_models_dir`: path is in models dir
- `test_shipped_specs_are_well_formed`: shipped specs are well formed
- `test_meeting_models_are_pinned_https_downloads`: meeting models are pinned https downloads
- `test_full_source_url_wins`: full source url wins
- `test_meeting_models_are_not_required_at_first_run`: meeting models are not required at first run
- `test_spec_is_immutable`: spec is immutable
- `test_configured_models`: configured models

## TestIsInstalled

- `test_missing`: missing
- `test_wrong_size`: wrong size
- `test_correct_size`: correct size

## TestEnsureModel

- `test_downloads_verifies_and_installs`: downloads verifies and installs
- `test_creates_missing_models_folder_tree`: creates missing models folder tree
- `test_download_has_a_timeout`: download has a timeout
- `test_no_partial_file_left_after_success`: no partial file left after success
- `test_progress_reports_monotonic_to_total`: progress reports monotonic to total
- `test_already_installed_skips_download`: already installed skips download
- `test_checksum_mismatch_rejected_and_cleaned_up`: checksum mismatch rejected and cleaned up
- `test_truncated_download_rejected`: truncated download rejected
- `test_network_error_propagates`: network error propagates
- `test_corrupt_existing_file_is_replaced`: corrupt existing file is replaced

## TestSetup

- `test_required_models`: required models
- `test_missing_defaults_to_required`: missing defaults to required
- `test_missing_excludes_installed`: missing excludes installed
- `test_nothing_missing`: nothing missing
- `test_progress_is_exact_fraction_of_all_bytes`: progress is exact fraction of all bytes
- `test_install_only_downloads_missing`: install only downloads missing
- `test_runs_on_named_daemon_worker`: runs on named daemon worker
- `test_install_failure_reports_error`: install failure reports error
- `test_install_stops_after_first_failure`: install stops after first failure
- `test_install_with_nothing_missing_finishes`: install with nothing missing finishes
- `test_defaults_install_the_required_models`: defaults install the required models

## TestFakeLevels

- `test_always_in_range`: always in range
- `test_varies_over_time`: varies over time
- `test_has_quiet_and_loud_moments`: has quiet and loud moments
- `test_instances_are_offset`: instances are offset
- `test_seeded_sequence_matches_snapshot`: Characterization test: pins the exact synthetic waveform for a fixed seed.
