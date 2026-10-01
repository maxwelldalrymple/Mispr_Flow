# `tests/test_apps.py`

42 tests. Source: [`tests/test_apps.py`](../../tests/test_apps.py).


## TestParse

- `test_commands`: commands
- `test_nothing_usable`: nothing usable
- `test_normalize`: normalize

## TestMatch

- `test_finds_the_app`: finds the app
- `test_nickname_wins`: nickname wins
- `test_unsure_is_none`: unsure is none
- `test_running_apps_win_ties`: running apps win ties

## TestFindApps

- `test_finds_apps_one_level_deep_first_wins`: finds apps one level deep first wins
- `test_this_mac_has_apps`: this mac has apps

## TestSystem

- `test_running_apps_are_regular_apps`: running apps are regular apps
- `test_bring_to_front_asks_workspace_to_open_and_activate`: bring to front asks workspace to open and activate

## TestWindowCommands

close / minimize / expand, side by side, and "chrome 80%".

- `test_commands`: commands
- `test_layouts`: layouts
- `test_this_macs_screen_and_front_app`: this macs screen and front app

## TestShortcuts

Tab and browser commands are the apps' own keyboard shortcuts.

- `test_commands`: commands
- `test_every_alias_is_a_real_shortcut`: every alias is a real shortcut
- `test_keys_pressed`: keys pressed

## TestSound

Play/pause, volume, mic and tab muting.

- `test_commands`: commands
- `test_volume_scripts`: volume scripts
- `test_mic_level`: mic level
- `test_media_key_events`: media key events

## TestSeek

- `test_commands`: commands
- `test_one_arrow_per_five_seconds`: one arrow per five seconds

## TestScroll

- `test_commands`: commands
- `test_scroll_events`: scroll events
- `test_top_and_bottom_are_cmd_arrows`: top and bottom are cmd arrows

## TestConfidentMatching

Never open the wrong app: "Pro." (a clipped "Chrome") once opened Logic Pro.

- `test_scores`: scores

## TestFolders

- `test_commands`: commands
- `test_highest_level_wins_and_names_are_loose`: highest level wins and names are loose
- `test_skips_hidden_and_library`: skips hidden and library
- `test_files_by_name_without_extension_and_folders_first`: files by name without extension and folders first
- `test_gives_up_after_its_time_budget`: gives up after its time budget
- `test_finder_scripts`: finder scripts
- `test_finder_permission_check_never_prompts`: finder permission check never prompts

## TestSoundAlikeNames

Whisper wrote "clawed" for "Claude": the folder should still open.

- `test_sound_codes`: sound codes
- `test_exact_name_wins_then_highest_sound_alike`: exact name wins then highest sound alike

## TestSpotlightAndAccess

- `test_spotlight_exact_then_sound_alike_shallowest`: spotlight exact then sound alike shallowest
- `test_spotlight_off_or_failing_is_none`: spotlight off or failing is none
- `test_full_disk_access_check`: full disk access check

## TestSystemHelpersSafely

Window, tab, quit and open helpers, run where they can't change anything.

- `test_window_helpers_answer_no_window`: window helpers answer no window
- `test_quit_needs_a_real_app`: quit needs a real app
- `test_open_path_uses_open`: open path uses open
