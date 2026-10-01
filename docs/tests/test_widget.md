# `tests/test_widget.py`

230 tests. Source: [`tests/test_widget.py`](../../tests/test_widget.py).


## (module)

- `test_state_matches_golden_image`: state matches golden image
- `test_mic_notice_matches_golden_image`: mic notice matches golden image
- `test_copied_notice_matches_golden_image`: copied notice matches golden image
- `test_incognito_outline_matches_golden_image`: incognito outline matches golden image

## TestShape

- `test_values_roundtrip`: values roundtrip
- `test_values_order`: values order

## TestLayout

- `test_every_state_has_a_layout`: every state has a layout
- `test_interactive_elements_exist`: interactive elements exist
- `test_everything_fits_in_the_panel`: everything fits in the panel
- `test_opacities_valid`: opacities valid
- `test_unknown_state_raises`: unknown state raises
- `test_clickable_elements_do_not_overlap`: clickable elements do not overlap
- `test_hover_buttons_sized_and_lifted`: hover buttons sized and lifted
- `test_idle_pill_is_centered`: idle pill is centered
- `test_processing_has_no_clickable_parts`: processing has no clickable parts
- `test_idle_and_hold_are_click_through`: idle and hold are click through

## TestTooltips

- `test_every_tooltip_points_at_an_element`: every tooltip points at an element
- `test_handsfree_hint_matches_shortcuts`: handsfree hint matches shortcuts

## TestStateBasics

- `test_initial_state`: initial state
- `test_set_state_bumps_seq_and_resets_fade`: set state bumps seq and resets fade
- `test_set_same_state_is_noop`: set same state is noop
- `test_state_since_updates`: state since updates
- `test_to_idle_suppresses_hover`: to idle suppresses hover
- `test_scheduled_callback_runs_when_due`: scheduled callback runs when due
- `test_stale_callbacks_are_dropped_after_state_change`: stale callbacks are dropped after state change
- `test_callbacks_run_in_schedule_order`: callbacks run in schedule order
- `test_hidden`: hidden

## TestFnGestures

- `test_hold_records_then_finishes`: hold records then finishes
- `test_quick_tap_is_discarded_silently`: quick tap is discarded silently
- `test_tap_vs_hold_threshold`: tap vs hold threshold
- `test_double_tap_starts_handsfree`: double tap starts handsfree
- `test_double_tap_window_is_measured_from_first_press`: double tap window is measured from first press
- `test_slow_second_tap_is_a_new_hold`: slow second tap is a new hold
- `test_fn_in_handsfree_cancels`: fn in handsfree cancels
- `test_fn_ignored_while_busy`: fn ignored while busy
- `test_fn_works_from_hover`: fn works from hover
- `test_mic_failure_keeps_state`: mic failure keeps state
- `test_fn_combo_discards_hold`: fn combo discards hold
- `test_fn_combo_clears_pending_double_tap`: fn combo clears pending double tap
- `test_fn_combo_ignored_outside_fn_hold`: fn combo ignored outside fn hold
- `test_fn_up_without_press_is_harmless`: fn up without press is harmless
- `test_fn_up_ignored_for_mouse_hold`: fn up ignored for mouse hold

## TestKeys

- `test_accept_keys_finish`: accept keys finish
- `test_delete_cancels`: delete cancels
- `test_delete_on_toast_discards_immediately`: delete on toast discards immediately
- `test_keys_pass_through_in_other_states`: keys pass through in other states
- `test_space_on_toast_passes_through`: space on toast passes through
- `test_other_keys_pass_through`: other keys pass through
- `test_deferred_action_skipped_if_state_changed`: deferred action skipped if state changed

## TestCancelUndo

- `test_cancel_keeps_audio_until_toast_expires`: cancel keeps audio until toast expires
- `test_undo_processes_the_recording`: undo processes the recording
- `test_undo_cancels_the_expiry`: undo cancels the expiry
- `test_new_recording_supersedes_toast`: new recording supersedes toast
- `test_cancel_sets_end_time`: cancel sets end time

## TestTranscribed

- `test_text_is_pasted_saved_and_wiped`: text is pasted saved and wiped
- `test_empty_transcript_pastes_and_saves_nothing`: empty transcript pastes and saves nothing
- `test_rejected_cleanup_info_is_handled`: rejected cleanup info is handled
- `test_cleanup_used_when_enabled`: cleanup used when enabled
- `test_cleanup_skipped_when_disabled`: cleanup skipped when disabled
- `test_transcriber_gets_the_recorded_audio`: transcriber gets the recorded audio

## TestSaving

- `test_incognito_saves_nothing`: incognito saves nothing
- `test_cancelled_recording_saved_on_expiry`: cancelled recording saved on expiry
- `test_short_audio_not_saved`: short audio not saved
- `test_nothing_saved_before_any_recording`: nothing saved before any recording
- `test_disk_errors_never_break_dictation`: disk errors never break dictation
- `test_note_context_records_app_only`: note context records app only

## TestMeeting

- `test_note_button_starts_meeting`: note button starts meeting
- `test_short_meeting_asks_started_by_mistake`: short meeting asks started by mistake
- `test_long_meeting_ends_normally`: long meeting ends normally
- `test_mistake_card_buttons_dismiss`: mistake card buttons dismiss
- `test_stop_button`: stop button

## TestMouse

- `test_hit_finds_each_interactive_element`: hit finds each interactive element
- `test_hit_outside_everything`: hit outside everything
- `test_retry_only_clickable_after_failure`: retry only clickable after failure
- `test_mic_click_starts_handsfree`: mic click starts handsfree
- `test_mic_long_press_is_push_to_talk`: mic long press is push to talk
- `test_long_press_cancelled_if_released_early`: long press cancelled if released early
- `test_release_on_different_element_does_nothing`: release on different element does nothing
- `test_press_on_nothing_does_nothing`: press on nothing does nothing
- `test_cancel_and_finish_buttons`: cancel and finish buttons
- `test_wave_zone_is_not_a_button`: wave zone is not a button

## TestSetupFlow

- `test_run_setup_resets_and_starts_download`: run setup resets and starts download
- `test_progress_is_stored`: progress is stored
- `test_done_loads_engines_and_unlocks`: done loads engines and unlocks
- `test_failure_shows_retry_and_stays_locked`: failure shows retry and stays locked
- `test_retry_only_after_failure`: retry only after failure
- `test_retry_button_click`: retry button click
- `test_dictation_locked_during_setup`: dictation locked during setup
- `test_load_engines`: load engines

## TestLevels

- `test_idle_levels_decay_to_zero`: idle levels decay to zero
- `test_recording_uses_mic_level_center_weighted`: recording uses mic level center weighted
- `test_meeting_uses_meeting_source`: meeting uses meeting source
- `test_bar_counts`: bar counts

## TestLog

- `test_silent_by_default`: silent by default
- `test_debug_prints_timestamped`: debug prints timestamped

## TestDraw

- `test_every_state_renders`: every state renders
- `test_hidden_draws_nothing`: hidden draws nothing

## TestSpecification

Product decisions, asserted as literal values (not compared to themselves).

- `test_fn_timing`: fn timing
- `test_undo_window_and_meeting_guard`: undo window and meeting guard
- `test_handsfree_keys`: handsfree keys
- `test_panel_and_animation`: panel and animation
- `test_tooltip_copy`: tooltip copy
- `test_icons`: icons
- `test_state_names_are_stable`: state names are stable

## TestLayoutSnapshot

- `test_every_state_matches_golden_geometry`: every state matches golden geometry

## TestInitialState

- `test_defaults`: defaults

## TestSoundCues

SpySounds records every cue, so each gesture's audible feedback is pinned.

- `test_fn_hold`: fn hold
- `test_double_tap_plays_start_then_lock`: double tap plays start then lock
- `test_no_lock_sound_if_mic_fails_on_second_tap`: no lock sound if mic fails on second tap
- `test_model_download_failure_plays_error`: model download failure plays error
- `test_quick_tap_discard_is_silent_after_start`: quick tap discard is silent after start
- `test_mouse_handsfree_then_cancel`: mouse handsfree then cancel
- `test_undo_and_expiry_are_silent`: undo and expiry are silent
- `test_meeting`: meeting
- `test_short_meeting_still_confirms_stop`: short meeting still confirms stop
- `test_mic_failure_plays_error`: mic failure plays error
- `test_paste_sound_when_text_lands`: paste sound when text lands
- `test_pastes_unless_sure_there_is_no_text_box`: pastes unless sure there is no text box
- `test_no_text_box_copies_instead_with_error_sound`: no text box copies instead with error sound
- `test_auto_enter_presses_return_after_pasting`: auto enter presses return after pasting
- `test_auto_enter_also_works_when_incognito_types`: auto enter also works when incognito types
- `test_auto_enter_never_presses_return_without_a_text_box`: auto enter never presses return without a text box
- `test_no_return_unless_auto_enter_is_on`: no return unless auto enter is on
- `test_alert_when_nothing_was_heard`: alert when nothing was heard
- `test_quick_tap_does_not_alert`: quick tap does not alert
- `test_models_installed_plays_success`: models installed plays success

## TestStateMachineDetails

- `test_tap_threshold_is_exclusive`: tap threshold is exclusive
- `test_save_minimum_length_boundary`: save minimum length boundary
- `test_saved_times_are_recording_start_and_stop`: saved times are recording start and stop
- `test_missing_end_time_falls_back_to_now`: missing end time falls back to now
- `test_superseded_cancel_is_saved_before_new_recording`: superseded cancel is saved before new recording
- `test_hold_records_where_dictation_started`: hold records where dictation started
- `test_discard_stops_the_mic`: discard stops the mic
- `test_long_press_ignored_if_released_outside`: long press ignored if released outside
- `test_long_press_only_on_mic`: long press only on mic
- `test_long_press_ignored_after_state_change`: long press ignored after state change

## TestLevelsCharacterization

- `test_envelope_snapshot`: envelope snapshot
- `test_center_bar_tallest_edges_symmetric`: center bar tallest edges symmetric

## TestPointer

- `test_entering_idle_zone_opens_hover`: entering idle zone opens hover
- `test_pointer_elsewhere_stays_idle`: pointer elsewhere stays idle
- `test_idle_hover_zone_edges`: idle hover zone edges
- `test_suppressed_until_pointer_leaves`: suppressed until pointer leaves
- `test_leaving_buttons_closes_hover`: leaving buttons closes hover
- `test_hover_has_a_ten_point_grace_margin`: hover has a ten point grace margin
- `test_hover_kept_while_button_pressed`: hover kept while button pressed
- `test_hidden_widget_ignores_pointer`: hidden widget ignores pointer
- `test_accepts_clicks_only_over_buttons`: accepts clicks only over buttons
- `test_pressed_button_keeps_accepting_clicks`: pressed button keeps accepting clicks
- `test_pointer_coordinates_are_panel_relative`: pointer coordinates are panel relative

## TestScreenFollowing

- `test_panel_centered_on_visible_frame_bottom`: panel centered on visible frame bottom
- `test_not_moved_when_unchanged`: not moved when unchanged
- `test_force_always_repositions`: force always repositions
- `test_moves_to_new_screen`: moves to new screen
- `test_records_fullscreen`: records fullscreen

## TestFrameLoop

- `test_tick_runs_due_callbacks`: tick runs due callbacks
- `test_screen_polled_on_cadence`: screen polled on cadence
- `test_shape_eases_thirty_percent_toward_target`: shape eases thirty percent toward target
- `test_content_fades_in`: content fades in
- `test_tooltip_follows_hovered_element`: tooltip follows hovered element
- `test_tooltip_fades_out_but_keeps_content`: tooltip fades out but keeps content
- `test_every_tick_redraws`: every tick redraws
- `test_tick_animates_waveform`: tick animates waveform

## TestStart

- `test_panel_configuration`: panel configuration
- `test_frame_timer_at_60fps_in_common_modes`: frame timer at 60fps in common modes
- `test_models_present_loads_engines`: models present loads engines
- `test_missing_models_enter_mandatory_setup`: missing models enter mandatory setup

## TestObjCBridges

- `test_view_contract`: view contract
- `test_view_forwards_mouse_in_view_coordinates`: view forwards mouse in view coordinates
- `test_ticker_forwards_to_callback`: ticker forwards to callback

## TestDebugLog

- `test_env_var_switches_debug_on_only_for_1`: env var switches debug on only for 1
- `test_fn_up_logs_how_long_fn_was_held`: fn up logs how long fn was held
- `test_consumed_fn_up_logs_plainly`: consumed fn up logs plainly

## TestMicNotice

- `test_wording`: wording
- `test_duration_spec`: duration spec
- `test_shown_on_first_dictation_only`: shown on first dictation only
- `test_also_on_first_handsfree_or_mouse_recording`: also on first handsfree or mouse recording
- `test_skipped_when_there_is_no_mic_name`: skipped when there is no mic name
- `test_visible_for_three_seconds_then_fades`: visible for three seconds then fades
- `test_only_while_recording`: only while recording
- `test_takes_priority_over_tooltips`: takes priority over tooltips

## TestHostHooks

- `test_saved_recordings_are_reported`: saved recordings are reported
- `test_nothing_reported_in_incognito`: nothing reported in incognito
- `test_reload_settings_applies_sounds_switch`: reload settings applies sounds switch

## TestNoteWindowHooks

- `test_note_button_starts_a_meeting_when_standalone`: note button starts a meeting when standalone
- `test_option_m_toggles_the_meeting_when_standalone`: option m toggles the meeting when standalone
- `test_option_m_asks_the_app_from_any_state_when_hosted`: option m asks the app from any state when hosted
- `test_note_button_asks_the_app_when_hosted`: note button asks the app when hosted
- `test_meeting_changes_are_reported`: meeting changes are reported
- `test_start_meeting_ignored_while_busy`: start meeting ignored while busy
- `test_stop_meeting_ignored_when_not_in_one`: stop meeting ignored when not in one

## TestAppSwitcher

Hold the switch key, say an app, let go: it comes forward. Nicknames by voice.

- `test_saying_an_app_brings_it_forward`: saying an app brings it forward
- `test_running_app_path_is_used`: running app path is used
- `test_nickname_by_voice_then_use_it`: nickname by voice then use it
- `test_unknown_app_errors`: unknown app errors
- `test_nickname_for_an_unknown_app_errors`: nickname for an unknown app errors
- `test_silence_alerts`: silence alerts
- `test_commands_go_into_history_then_audio_is_wiped`: commands go into history then audio is wiped
- `test_history_keeps_the_outcome_with_real_names`: history keeps the outcome with real names
- `test_incognito_commands_are_not_saved`: incognito commands are not saved
- `test_quick_tap_or_shortcut_drops_it`: quick tap or shortcut drops it
- `test_close_minimize_expand`: close minimize expand
- `test_side_by_side_with_a_split`: side by side with a split
- `test_percent_of_the_screen`: percent of the screen
- `test_an_app_still_opening_is_retried`: an app still opening is retried
- `test_unknown_app_in_a_layout_errors`: unknown app in a layout errors
- `test_tab_shortcuts_here_or_in_a_named_app`: tab shortcuts here or in a named app
- `test_quit`: quit
- `test_play_pause_and_volume`: play pause and volume
- `test_mute_mic_and_unmute_it_by_voice`: mute mic and unmute it by voice
- `test_other_commands_while_muted_keep_it_muted`: other commands while muted keep it muted
- `test_mute_tab_and_mute_app`: mute tab and mute app
- `test_skip_forward_and_back`: skip forward and back
- `test_scrolling`: scrolling
- `test_a_guess_never_opens_an_app_that_isnt_running`: a guess never opens an app that isnt running
- `test_open_folder_searches_from_home`: open folder searches from home
- `test_in_finder_open_goes_into_folders_and_opens_files`: in finder open goes into folders and opens files
- `test_in_finder_not_found_says_where`: in finder not found says where
- `test_in_finder_open_an_app_still_works`: in finder open an app still works
- `test_ignored_while_busy_or_without_a_press`: ignored while busy or without a press

## TestAutoEnterCues

You can tell Auto-Enter is on: a chime and a notice when it changes, a ⏎ badge while on.

- `test_turning_it_on_and_off_chimes_and_says_so`: turning it on and off chimes and says so
- `test_other_setting_changes_stay_quiet`: other setting changes stay quiet
- `test_no_chime_when_sounds_are_off`: no chime when sounds are off
- `test_badge_is_drawn_only_while_on`: badge is drawn only while on

## TestBrowserTextBoxRecheck

A browser box that is still taking focus (YouTube's comment box) gets a second look.

- `test_browser_no_is_checked_again`: browser no is checked again
- `test_other_apps_are_not_rechecked`: other apps are not rechecked

## TestTerminalDictation

In a terminal, dictation becomes shell syntax and Auto-Enter never runs it.

- `test_terminal_gets_shell_syntax_and_others_the_usual_cleanup`: terminal gets shell syntax and others the usual cleanup
- `test_auto_enter_runs_the_command_in_terminals_too`: auto enter runs the command in terminals too

## TestIncognitoNeverUsesTheClipboard

- `test_types_instead_of_pasting`: types instead of pasting
- `test_no_text_box_drops_the_words`: no text box drops the words
- `test_normal_mode_still_pastes`: normal mode still pastes
