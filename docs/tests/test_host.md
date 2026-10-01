# `tests/test_host.py`

14 tests. Source: [`tests/test_host.py`](../../tests/test_host.py).


## (module)

- `test_reload_applies_a_new_dictation_key`: reload applies a new dictation key

## TestHosted

- `test_env_flag`: env flag

## TestSend

- `test_one_prefixed_json_line`: one prefixed json line
- `test_defaults_to_stdout`: defaults to stdout

## TestChannel

- `test_survives_stdout_being_pointed_at_dev_null`: llama.cpp dup2()s /dev/null over fd 1 while loading; our channel must not care.

## TestParse

- `test_lines`: lines

## TestListen

- `test_runs_handlers_in_order_then_eof`: runs handlers in order then eof
- `test_unknown_and_malformed_commands_are_skipped`: unknown and malformed commands are skipped
- `test_arguments_reach_the_handler`: arguments reach the handler
- `test_closed_stdin_means_the_app_is_gone`: closed stdin means the app is gone
- `test_reads_on_a_named_daemon_thread`: reads on a named daemon thread

## TestConnectHost

- `test_wiring`: wiring

## TestTryPrompt

- `test_runs_the_draft_and_reports`: runs the draft and reports
- `test_blank_instructions_mean_the_default`: blank instructions mean the default
