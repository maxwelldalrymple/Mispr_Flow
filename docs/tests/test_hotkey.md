# `tests/test_hotkey.py`

59 tests. Source: [`tests/test_hotkey.py`](../../tests/test_hotkey.py).


## TestPermissions

- `test_input_monitoring`: input monitoring
- `test_request_input_monitoring`: request input monitoring
- `test_accessibility`: accessibility
- `test_request_accessibility_asks_for_prompt`: request accessibility asks for prompt

## TestSpec

- `test_globe_keycode`: globe keycode
- `test_fn_flag_is_secondary_fn`: fn flag is secondary fn

## TestFnKeySetting

- `test_reads_defaults`: reads defaults
- `test_runs_defaults_read_capturing_text`: runs defaults read capturing text

## TestFnFlag

- `test_fn_press_and_release`: fn press and release
- `test_listen_only_passes_fn_through`: listen only passes fn through
- `test_other_modifier_while_fn_held_is_ignored`: other modifier while fn held is ignored
- `test_other_modifier_without_fn_passes`: other modifier without fn passes

## TestGlobeKey

- `test_swallowed_when_active`: swallowed when active
- `test_passes_when_listen_only`: passes when listen only
- `test_globe_while_fn_held_is_not_a_combo`: globe while fn held is not a combo

## TestKeys

- `test_key_while_fn_held_is_combo_and_passes`: key while fn held is combo and passes
- `test_handled_key_swallowed_with_its_key_up`: handled key swallowed with its key up
- `test_unhandled_key_passes`: unhandled key passes
- `test_modified_keys_never_offered`: modified keys never offered
- `test_shift_does_not_block_shortcuts`: shift does not block shortcuts
- `test_listen_only_never_swallows_keys`: listen only never swallows keys
- `test_no_on_key_handler`: no on key handler

## TestTapHealth

- `test_disabled_tap_is_reenabled`: disabled tap is reenabled

## TestInstall

- `test_start_installs_active_hid_tap`: start installs active hid tap
- `test_start_falls_back_to_listen_only_session_tap`: start falls back to listen only session tap
- `test_start_fails_without_any_permission`: start fails without any permission
- `test_remove_tears_down_in_order`: remove tears down in order
- `test_remove_without_tap_is_safe`: remove without tap is safe
- `test_upgrade_noop_when_already_active`: upgrade noop when already active
- `test_upgrade_noop_without_accessibility`: upgrade noop without accessibility
- `test_upgrade_swaps_listen_tap_for_active`: upgrade swaps listen tap for active
- `test_upgrade_failure_restores_listen_tap`: upgrade failure restores listen tap

## TestNormalizeTrigger

- `test_malformed_means_fn`: malformed means fn
- `test_valid_triggers_kept`: valid triggers kept

## TestModifierTrigger

- `test_press_and_release_swallowed`: press and release swallowed
- `test_left_option_passes_and_does_nothing`: left option passes and does nothing
- `test_fn_no_longer_dictates`: fn no longer dictates
- `test_globe_key_passes_when_fn_is_not_the_trigger`: globe key passes when fn is not the trigger
- `test_key_while_held_is_a_combo`: key while held is a combo

## TestKeyTrigger

- `test_press_hold_release`: press hold release
- `test_listen_only_passes_the_key`: listen only passes the key
- `test_other_key_while_held_is_a_combo`: other key while held is a combo
- `test_fn_flag_ignored`: fn flag ignored

## TestSetTrigger

- `test_switching_mid_press_releases`: switching mid press releases
- `test_same_trigger_is_a_no_op`: same trigger is a no op

## TestNoteShortcut

- `test_option_m_opens_a_note_and_is_swallowed`: option m opens a note and is swallowed
- `test_plain_m_and_cmd_option_m_pass`: plain m and cmd option m pass
- `test_auto_repeat_opens_once`: auto repeat opens once

## TestSwitchTrigger

Which app switcher keys are allowed: a key, one side of a modifier, or a combo.

- `test_off_or_unusable`: off or unusable
- `test_never_the_dictation_key`: never the dictation key
- `test_combos_are_tidied`: combos are tidied

## TestSwitchKey

The app switcher key's press and release, without disturbing dictation.

- `test_single_key_down_up_swallowed_and_repeat_ignored`: single key down up swallowed and repeat ignored
- `test_single_modifier_side_passes_through`: single modifier side passes through
- `test_modifier_combo_needs_exactly_those_modifiers`: modifier combo needs exactly those modifiers
- `test_key_combo_fires_only_with_its_modifiers`: key combo fires only with its modifiers
- `test_a_shortcut_with_the_switch_modifier_held_is_dropped`: a shortcut with the switch modifier held is dropped
- `test_dictation_still_works_beside_it`: dictation still works beside it
- `test_changing_the_key_drops_a_press_in_progress`: changing the key drops a press in progress
- `test_off_without_a_handler`: off without a handler
