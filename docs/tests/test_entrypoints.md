# `tests/test_entrypoints.py`

18 tests. Source: [`tests/test_entrypoints.py`](../../tests/test_entrypoints.py).


## (module)

The functions that start things: app.main's wiring, its helpers, the models CLI, and the

- `test_cleaner_complete_returns_the_reply`: cleaner complete returns the reply
- `test_cleaner_complete_without_a_model_is_none`: cleaner complete without a model is none
- `test_transcriber_transcribe_runs_on_the_calling_thread`: transcriber transcribe runs on the calling thread
- `test_meeting_worker_keeps_going_after_a_failed_job`: meeting worker keeps going after a failed job
- `test_widget_view_draws_through_its_controller`: widget view draws through its controller
- `test_setup_window_show_brings_it_forward_and_starts_refreshing`: setup window show brings it forward and starts refreshing

## TestMain

- `test_standalone_is_a_dock_app_with_its_own_menu`: standalone is a dock app with its own menu
- `test_hosted_hands_the_dock_to_the_swift_app`: hosted hands the dock to the swift app
- `test_fn_monitor_uses_the_chosen_key_and_option_m`: fn monitor uses the chosen key and option m
- `test_setup_window_opens_only_when_something_is_missing`: setup window opens only when something is missing
- `test_warns_when_fn_cannot_start`: warns when fn cannot start

## TestSetupOpener

- `test_reuses_the_open_window`: reuses the open window
- `test_makes_a_new_one_after_it_was_closed`: makes a new one after it was closed

## TestFnKeeper

- `test_logs_only_changes`: logs only changes

## TestModelsCli

- `test_prints_every_five_percent_once`: prints every five percent once
- `test_downloads_the_named_models`: downloads the named models
- `test_meeting_models_by_name`: meeting models by name
- `test_defaults_to_both`: defaults to both
