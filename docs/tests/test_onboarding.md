# `tests/test_onboarding.py`

45 tests. Source: [`tests/test_onboarding.py`](../../tests/test_onboarding.py).


## (module)

- `test_page_matches_golden_image`: page matches golden image
- `test_dark_mode_matches_golden_image`: dark mode matches golden image
- `test_setup_offers_finder_control_as_optional`: setup offers finder control as optional

## TestDefaultPermissions

- `test_keys_and_requirements`: keys and requirements
- `test_settings_panes`: settings panes
- `test_every_permission_explains_why`: every permission explains why

## TestPermissionWrappers

- `test_microphone_status`: microphone status
- `test_microphone_request_asks_for_audio`: microphone request asks for audio
- `test_screen_audio`: screen audio
- `test_open_pane_url`: open pane url

## TestWhenToShow

- `test_first_run_starts_at_welcome`: first run starts at welcome
- `test_revoked_required_permission_reopens_at_permissions`: revoked required permission reopens at permissions
- `test_missing_models_reopen_at_models`: missing models reopen at models
- `test_complete_setup_is_not_shown`: complete setup is not shown
- `test_missing_optional_permission_does_not_reopen`: missing optional permission does not reopen

## TestNavigation

- `test_welcome_can_always_continue`: welcome can always continue
- `test_permissions_block_until_required_granted`: permissions block until required granted
- `test_optional_permission_never_blocks`: optional permission never blocks
- `test_models_block_until_ready`: models block until ready
- `test_ready_is_the_last_step`: ready is the last step
- `test_back_stops_at_welcome`: back stops at welcome
- `test_missing_required_lists_keys_in_order`: missing required lists keys in order
- `test_granted_reports_every_permission`: granted reports every permission
- `test_finish_marks_onboarded_and_saves`: finish marks onboarded and saves

## TestAllow

- `test_first_click_shows_system_prompt`: first click shows system prompt
- `test_second_click_opens_system_settings`: second click opens system settings
- `test_denied_microphone_goes_straight_to_settings`: denied microphone goes straight to settings
- `test_already_granted_does_nothing`: already granted does nothing
- `test_unknown_key_raises`: unknown key raises

## TestModelStatus

- `test_downloading`: downloading
- `test_error`: error
- `test_ready_wins_over_stale_error`: ready wins over stale error

## TestWindow

- `test_opens_on_the_active_space`: opens on the active space
- `test_title_and_size`: title and size
- `test_footer_buttons`: footer buttons
- `test_permission_rows_track_grants_live`: permission rows track grants live
- `test_allow_button_targets_its_permission`: allow button targets its permission
- `test_continue_and_back_move_between_pages`: continue and back move between pages
- `test_model_page_progress_and_retry`: model page progress and retry
- `test_start_dictating_finishes_and_closes`: start dictating finishes and closes
- `test_granting_a_permission_plays_success_once`: granting a permission plays success once
- `test_already_granted_permissions_are_silent`: already granted permissions are silent
- `test_finishing_setup_plays_achievement`: finishing setup plays achievement
- `test_close_stops_refresh_timer`: close stops refresh timer
- `test_refresh_selector_calls_owner`: refresh selector calls owner
