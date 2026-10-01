# `tests/test_context_paste.py`

51 tests. Source: [`tests/test_context_paste.py`](../../tests/test_context_paste.py).


## TestAttrHelpers

- `test_attr_none_element`: attr none element
- `test_attr_success_and_error`: attr success and error
- `test_url_string_variants`: url string variants

## TestBrowserPage

- `test_outermost_web_area_wins_over_iframe`: outermost web area wins over iframe
- `test_single_web_area`: single web area
- `test_address_bar_falls_back_to_window_document`: address bar falls back to window document
- `test_nothing_available`: nothing available
- `test_sets_messaging_timeout`: sets messaging timeout
- `test_timeout_never_stalls_paste_noticeably`: timeout never stalls paste noticeably
- `test_hop_limit_reaches_exactly_max_hops`: hop limit reaches exactly max hops
- `test_hop_limit_stops_after_max_hops`: hop limit stops after max hops
- `test_max_hops_value`: max hops value
- `test_cyclic_parents_terminate`: cyclic parents terminate

## TestFrontmost

- `test_no_frontmost_app`: no frontmost app
- `test_non_browser_has_no_page`: non browser has no page
- `test_browser_includes_page`: browser includes page
- `test_include_page_false_skips_lookup`: include page false skips lookup
- `test_lookup_errors_never_break_dictation`: lookup errors never break dictation
- `test_major_browsers_recognised`: major browsers recognised

## TestTextTarget

- `test_text_roles`: text roles
- `test_contenteditable_in_a_browser`: contenteditable in a browser
- `test_custom_view_with_editable_value_and_caret`: custom view with editable value and caret
- `test_known_non_text_focus`: known non text focus
- `test_any_non_text_focus_in_a_native_app_or_browser_is_no`: any non text focus in a native app or browser is no
- `test_unfamiliar_role_in_electron_gets_the_benefit_of_the_doubt`: unfamiliar role in electron gets the benefit of the doubt
- `test_known_non_text_role_in_electron_is_no`: known non text role in electron is no
- `test_nothing_focused`: nothing focused
- `test_nothing_focused_in_electron_is_unknown`: nothing focused in electron is unknown
- `test_app_that_wont_answer`: app that wont answer
- `test_asks_electron_apps_to_build_their_tree`: asks electron apps to build their tree
- `test_exceptions_mean_unknown`: exceptions mean unknown

## TestFocusedTextTarget

- `test_no_frontmost_app`: no frontmost app
- `test_detects_electron_from_the_bundle`: detects electron from the bundle

## TestTypeText

- `test_types_in_chunks_without_the_clipboard`: types in chunks without the clipboard
- `test_handles_emoji_and_accents`: handles emoji and accents
- `test_no_modifier_flags`: no modifier flags

## TestPressEnter

Auto-Enter's keypress: one Return, down then up, with no modifiers.

- `test_one_return_with_no_modifiers`: one return with no modifiers

## TestCopyText

- `test_leaves_text_on_clipboard_without_cmd_v`: leaves text on clipboard without cmd v

## TestPaste

- `test_pastes_text_via_cmd_v`: pastes text via cmd v
- `test_paste_contains_only_dictation_during_paste`: paste contains only dictation during paste
- `test_timing_and_key_spec`: timing and key spec
- `test_dictated_text_marked_private`: dictated text marked private
- `test_previous_clipboard_restored`: previous clipboard restored
- `test_restore_scheduled_after_delay`: restore scheduled after delay
- `test_user_copy_during_paste_is_not_overwritten`: user copy during paste is not overwritten
- `test_empty_clipboard_is_restored_empty`: empty clipboard is restored empty
- `test_multiple_items_round_trip`: multiple items round trip
- `test_unicode_text`: unicode text

## TestPostCmdV

- `test_posts_v_down_and_up_with_only_command`: posts v down and up with only command

## TestBrowserHelpers

- `test_is_browser`: is browser
- `test_focus_chain_reads_this_mac`: focus chain reads this mac
