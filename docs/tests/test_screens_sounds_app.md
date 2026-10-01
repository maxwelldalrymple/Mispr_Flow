# `tests/test_screens_sounds_app.py`

55 tests. Source: [`tests/test_screens_sounds_app.py`](../../tests/test_screens_sounds_app.py).


## TestFrontmostWindowBounds

- `test_no_app`: no app
- `test_first_matching_window`: first matching window
- `test_skips_non_normal_layers`: skips non normal layers
- `test_queries_only_onscreen_app_windows`: queries only onscreen app windows
- `test_min_window_size_boundary`: min window size boundary
- `test_skips_tiny_windows`: skips tiny windows
- `test_none_when_app_has_no_windows`: none when app has no windows

## TestActiveScreen

- `test_window_on_primary`: window on primary
- `test_window_on_second_screen`: window on second screen
- `test_fullscreen_detected`: fullscreen detected
- `test_fullscreen_on_second_screen`: fullscreen on second screen
- `test_maximized_but_not_fullscreen`: maximized but not fullscreen
- `test_straddling_window_belongs_to_screen_holding_its_center`: straddling window belongs to screen holding its center
- `test_vertical_center_uses_flipped_coordinates`: vertical center uses flipped coordinates
- `test_fullscreen_tolerance_is_under_one_point`: fullscreen tolerance is under one point
- `test_fullscreen_tolerates_subpixel_differences`: fullscreen tolerates subpixel differences
- `test_falls_back_to_mouse_screen`: falls back to mouse screen
- `test_falls_back_to_main_screen`: falls back to main screen

## TestSounds

- `test_plays_named_sound_at_volume`: plays named sound at volume
- `test_disabled_plays_nothing`: disabled plays nothing
- `test_unknown_sound_ignored`: unknown sound ignored
- `test_overlapping_cues_are_separate_copies`: overlapping cues are separate copies
- `test_finished_sounds_released`: finished sounds released
- `test_default_volume_is_full_because_levels_are_in_the_files`: default volume is full because levels are in the files
- `test_each_file_is_loaded_once`: each file is loaded once
- `test_missing_file_is_ignored`: missing file is ignored

## TestSoundFiles

The shipped cues: every one exists, is a short mono 48 kHz WAV, and isn't clipped.

- `test_file_shape`: file shape
- `test_dictation_cues_are_quiet_and_short`: dictation cues are quiet and short
- `test_generator_reproduces_the_shipped_files`: generator reproduces the shipped files

## TestSingleInstance

The lock path is injected, so tests never touch the real lock or patch tempfile.

- `test_default_path_is_in_temp_dir`: default path is in temp dir
- `test_first_instance_gets_lock`: first instance gets lock
- `test_second_instance_exits_with_code_1`: second instance exits with code 1
- `test_second_instance_releases_its_file`: second instance releases its file
- `test_lock_is_released_when_closed`: lock is released when closed
- `test_locks_are_independent_per_path`: locks are independent per path

## TestShutdown

- `test_handles_term_int_hup`: handles term int hup
- `test_signal_releases_everything`: signal releases everything
- `test_menu_quit_releases_models_and_audio`: menu quit releases models and audio

## TestBranding

- `test_app_name`: app name
- `test_menu_has_quit`: menu has quit
- `test_menubar_icon_is_the_logo_as_template`: menubar icon is the logo as template
- `test_menubar_icon_falls_back_to_symbol`: menubar icon falls back to symbol
- `test_app_icon_has_every_macos_size`: app icon has every macos size
- `test_icon_source_is_square_1024`: icon source is square 1024

## TestHotkeyMaintenance

- `test_starts_tap_once_permission_allows`: starts tap once permission allows
- `test_keeps_trying_without_permission`: keeps trying without permission
- `test_upgrades_listen_only_tap`: upgrades listen only tap
- `test_listen_only_waits_for_accessibility`: listen only waits for accessibility
- `test_active_tap_is_left_alone`: active tap is left alone

## TestDockApp

Mispr Flow is a regular Dock app (like Wispr Flow): logo in the Dock, app menu, reopen.

- `test_is_a_regular_dock_app_unless_hosted`: is a regular dock app unless hosted
- `test_process_is_named_mispr_flow`: process is named mispr flow
- `test_app_menu`: app menu
- `test_clicking_the_dock_icon_opens_the_window`: clicking the dock icon opens the window

## TestSetupWiring

- `test_setup_guide_is_first_menu_item_and_opens_setup`: setup guide is first menu item and opens setup
- `test_setup_flow_reads_widget_download_state`: setup flow reads widget download state
