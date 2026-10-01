# `tests/test_cleanup.py`

52 tests. Source: [`tests/test_cleanup.py`](../../tests/test_cleanup.py).


## TestWords

- `test_lowercases_and_strips_punctuation`: lowercases and strips punctuation
- `test_straight_and_curly_apostrophes_ignored`: straight and curly apostrophes ignored
- `test_number_words_become_digits`: number words become digits
- `test_digits_and_letters_split`: digits and letters split
- `test_empty`: empty
- `test_numbers_beyond_twelve_left_as_words`: numbers beyond twelve left as words
- `test_non_ascii_letters_are_separators`: non ascii letters are separators

## TestCheck

- `test_identical_text_passes`: identical text passes
- `test_punctuation_and_case_changes_pass`: punctuation and case changes pass
- `test_filler_removal_passes`: filler removal passes
- `test_self_correction_passes`: self correction passes
- `test_contraction_normalisation_passes`: contraction normalisation passes
- `test_number_word_to_digit_passes`: number word to digit passes
- `test_empty_output_rejected`: empty output rejected
- `test_single_added_word_rejected`: single added word rejected
- `test_answering_a_question_rejected`: answering a question rejected
- `test_invented_words_listed_sorted`: invented words listed sorted
- `test_generating_content_rejected`: generating content rejected
- `test_obeying_injection_rejected`: obeying injection rejected
- `test_dropping_translate_instruction_rejected`: dropping translate instruction rejected
- `test_exactly_at_keep_threshold_passes`: exactly at keep threshold passes
- `test_just_below_keep_threshold_rejected`: just below keep threshold rejected
- `test_fillers_do_not_count_toward_content`: fillers do not count toward content
- `test_all_filler_input_falls_back_to_raw_word_count`: all filler input falls back to raw word count
- `test_reordering_without_new_words_passes`: reordering without new words passes
- `test_every_prompt_example_satisfies_the_guard`: every prompt example satisfies the guard

## TestCleanerClean

- `test_empty_raw_returns_immediately`: empty raw returns immediately
- `test_empty_raw_does_not_wait_for_model`: empty raw does not wait for model
- `test_waits_for_model_before_cleaning`: A dictation that finishes while the model is still loading must wait for it,
- `test_model_unavailable_returns_raw`: model unavailable returns raw
- `test_good_cleanup_applied`: good cleanup applied
- `test_elapsed_ms_uses_injected_clock`: elapsed ms uses injected clock
- `test_whitespace_and_quotes_stripped_from_output`: whitespace and quotes stripped from output
- `test_invented_output_falls_back_to_raw`: invented output falls back to raw
- `test_empty_model_output_falls_back_to_raw`: empty model output falls back to raw
- `test_request_uses_greedy_decoding_and_bounded_tokens`: request uses greedy decoding and bounded tokens
- `test_prompt_wraps_dictation_in_tags`: prompt wraps dictation in tags
- `test_calls_are_serialized_by_lock`: calls are serialized by lock

## TestCleanerMessages

- `test_structure`: structure
- `test_examples_alternate_user_assistant`: examples alternate user assistant
- `test_system_prompt_forbids_adding_and_answering`: system prompt forbids adding and answering

## TestCleanerLifecycle

- `test_close_frees_model`: close frees model
- `test_close_is_idempotent_and_safe_when_unloaded`: close is idempotent and safe when unloaded
- `test_load_configures_model`: load configures model
- `test_load_warms_up_deterministically`: load warms up deterministically
- `test_load_failure_is_recorded_and_still_ready`: load failure is recorded and still ready
- `test_load_async_uses_named_daemon_worker`: load async uses named daemon worker

## TestConfigurablePrompt

- `test_configure_changes_the_messages`: configure changes the messages
- `test_per_call_override_leaves_the_configuration_alone`: per call override leaves the configuration alone
- `test_guard_off_allows_rewording`: guard off allows rewording
- `test_guard_on_still_rejects_invented_words`: guard on still rejects invented words
- `test_guard_off_gives_more_room_to_write`: guard off gives more room to write
