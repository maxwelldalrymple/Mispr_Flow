# Screenshots

Every window and state of Mispr Flow, rendered offscreen with made-up sample data (the user "Alex Rivera"; nothing real). Regenerate with:

```bash
tools/screenshots.sh
```

**Names:** `<window>_<page>_<state>_<theme>-<light|dark>.png`. For example, `main-window_home_incognito-on_classic-dark.png` is the main window on Home with Incognito on, in the Classic theme, dark mode.
- Note window shots are numbered in the order you meet them.
- Setup window shots end in `system-light`/`system-dark`, because setup uses the macOS colors.
- Floating widget shots have no theme, because the pill looks the same in every theme.

The SwiftUI windows come from [ScreenshotTests.swift](../../macos/Tests/MisprFlowTests/ScreenshotTests.swift). The setup window and widget are the Python golden images in [tests/golden/](../../tests/golden/README.md).

## main-window/ (38)

The main window: Home (dictation and commands history), Voice Commands, Notetaker (notes, people, meeting detail, contact editor), Insights, Prompts, and the Incognito / Auto-Enter top-bar states.

- [home_auto-enter-on_classic-dark.png](main-window/home_auto-enter-on_classic-dark.png)
- [home_auto-enter-on_classic-light.png](main-window/home_auto-enter-on_classic-light.png)
- [home_commands-history_classic-dark.png](main-window/home_commands-history_classic-dark.png)
- [home_commands-history_classic-light.png](main-window/home_commands-history_classic-light.png)
- [home_dictation-history_classic-dark.png](main-window/home_dictation-history_classic-dark.png)
- [home_dictation-history_classic-light.png](main-window/home_dictation-history_classic-light.png)
- [home_incognito-and-auto-enter-on_classic-dark.png](main-window/home_incognito-and-auto-enter-on_classic-dark.png)
- [home_incognito-and-auto-enter-on_classic-light.png](main-window/home_incognito-and-auto-enter-on_classic-light.png)
- [home_incognito-on_classic-dark.png](main-window/home_incognito-on_classic-dark.png)
- [home_incognito-on_classic-light.png](main-window/home_incognito-on_classic-light.png)
- [insights_more-insights_classic-dark.png](main-window/insights_more-insights_classic-dark.png)
- [insights_more-insights_classic-light.png](main-window/insights_more-insights_classic-light.png)
- [insights_overview_classic-dark.png](main-window/insights_overview_classic-dark.png)
- [insights_overview_classic-light.png](main-window/insights_overview_classic-light.png)
- [notetaker_contact-editor_classic-dark.png](main-window/notetaker_contact-editor_classic-dark.png)
- [notetaker_contact-editor_classic-light.png](main-window/notetaker_contact-editor_classic-light.png)
- [notetaker_meeting-detail_insights-tab_classic-dark.png](main-window/notetaker_meeting-detail_insights-tab_classic-dark.png)
- [notetaker_meeting-detail_insights-tab_classic-light.png](main-window/notetaker_meeting-detail_insights-tab_classic-light.png)
- [notetaker_meeting-detail_my-thoughts-tab_classic-dark.png](main-window/notetaker_meeting-detail_my-thoughts-tab_classic-dark.png)
- [notetaker_meeting-detail_my-thoughts-tab_classic-light.png](main-window/notetaker_meeting-detail_my-thoughts-tab_classic-light.png)
- [notetaker_meeting-detail_summary-tab_classic-dark.png](main-window/notetaker_meeting-detail_summary-tab_classic-dark.png)
- [notetaker_meeting-detail_summary-tab_classic-light.png](main-window/notetaker_meeting-detail_summary-tab_classic-light.png)
- [notetaker_meeting-detail_transcript-tab_classic-dark.png](main-window/notetaker_meeting-detail_transcript-tab_classic-dark.png)
- [notetaker_meeting-detail_transcript-tab_classic-light.png](main-window/notetaker_meeting-detail_transcript-tab_classic-light.png)
- [notetaker_notes-list_classic-dark.png](main-window/notetaker_notes-list_classic-dark.png)
- [notetaker_notes-list_classic-light.png](main-window/notetaker_notes-list_classic-light.png)
- [notetaker_people-list_classic-dark.png](main-window/notetaker_people-list_classic-dark.png)
- [notetaker_people-list_classic-light.png](main-window/notetaker_people-list_classic-light.png)
- [notetaker_person-selected-with-contact-card_classic-dark.png](main-window/notetaker_person-selected-with-contact-card_classic-dark.png)
- [notetaker_person-selected-with-contact-card_classic-light.png](main-window/notetaker_person-selected-with-contact-card_classic-light.png)
- [notetaker_third-tab_classic-dark.png](main-window/notetaker_third-tab_classic-dark.png)
- [notetaker_third-tab_classic-light.png](main-window/notetaker_third-tab_classic-light.png)
- [notetaker_two-people-shared-meetings_classic-dark.png](main-window/notetaker_two-people-shared-meetings_classic-dark.png)
- [notetaker_two-people-shared-meetings_classic-light.png](main-window/notetaker_two-people-shared-meetings_classic-light.png)
- [prompts_cleanup-prompt_classic-dark.png](main-window/prompts_cleanup-prompt_classic-dark.png)
- [prompts_cleanup-prompt_classic-light.png](main-window/prompts_cleanup-prompt_classic-light.png)
- [voice-commands_overview_classic-dark.png](main-window/voice-commands_overview_classic-dark.png)
- [voice-commands_overview_classic-light.png](main-window/voice-commands_overview_classic-light.png)

## settings/ (8)

The Settings modal, every section.

- [settings_data-and-privacy-section_classic-dark.png](settings/settings_data-and-privacy-section_classic-dark.png)
- [settings_data-and-privacy-section_classic-light.png](settings/settings_data-and-privacy-section_classic-light.png)
- [settings_general-section_classic-dark.png](settings/settings_general-section_classic-dark.png)
- [settings_general-section_classic-light.png](settings/settings_general-section_classic-light.png)
- [settings_profile-section_classic-dark.png](settings/settings_profile-section_classic-dark.png)
- [settings_profile-section_classic-light.png](settings/settings_profile-section_classic-light.png)
- [settings_system-section_classic-dark.png](settings/settings_system-section_classic-dark.png)
- [settings_system-section_classic-light.png](settings/settings_system-section_classic-light.png)

## tutorial/ (16)

The first-run tour, every step: the highlighted area and its card.

- [tutorial_step-1-of-8_dictate-anywhere_classic-dark.png](tutorial/tutorial_step-1-of-8_dictate-anywhere_classic-dark.png)
- [tutorial_step-1-of-8_dictate-anywhere_classic-light.png](tutorial/tutorial_step-1-of-8_dictate-anywhere_classic-light.png)
- [tutorial_step-2-of-8_your-history_classic-dark.png](tutorial/tutorial_step-2-of-8_your-history_classic-dark.png)
- [tutorial_step-2-of-8_your-history_classic-light.png](tutorial/tutorial_step-2-of-8_your-history_classic-light.png)
- [tutorial_step-3-of-8_auto-enter-and-incognito_classic-dark.png](tutorial/tutorial_step-3-of-8_auto-enter-and-incognito_classic-dark.png)
- [tutorial_step-3-of-8_auto-enter-and-incognito_classic-light.png](tutorial/tutorial_step-3-of-8_auto-enter-and-incognito_classic-light.png)
- [tutorial_step-4-of-8_control-your-mac-by-voice_classic-dark.png](tutorial/tutorial_step-4-of-8_control-your-mac-by-voice_classic-dark.png)
- [tutorial_step-4-of-8_control-your-mac-by-voice_classic-light.png](tutorial/tutorial_step-4-of-8_control-your-mac-by-voice_classic-light.png)
- [tutorial_step-5-of-8_insights_classic-dark.png](tutorial/tutorial_step-5-of-8_insights_classic-dark.png)
- [tutorial_step-5-of-8_insights_classic-light.png](tutorial/tutorial_step-5-of-8_insights_classic-light.png)
- [tutorial_step-6-of-8_meeting-notes_classic-dark.png](tutorial/tutorial_step-6-of-8_meeting-notes_classic-dark.png)
- [tutorial_step-6-of-8_meeting-notes_classic-light.png](tutorial/tutorial_step-6-of-8_meeting-notes_classic-light.png)
- [tutorial_step-7-of-8_prompts_classic-dark.png](tutorial/tutorial_step-7-of-8_prompts_classic-dark.png)
- [tutorial_step-7-of-8_prompts_classic-light.png](tutorial/tutorial_step-7-of-8_prompts_classic-light.png)
- [tutorial_step-8-of-8_make-it-yours_classic-dark.png](tutorial/tutorial_step-8-of-8_make-it-yours_classic-dark.png)
- [tutorial_step-8-of-8_make-it-yours_classic-light.png](tutorial/tutorial_step-8-of-8_make-it-yours_classic-light.png)

## themes/ (36)

All six themes in light and dark, on Home, Notetaker and Insights.

- [main-window_home_classic-dark.png](themes/main-window_home_classic-dark.png)
- [main-window_home_classic-light.png](themes/main-window_home_classic-light.png)
- [main-window_home_forest-dark.png](themes/main-window_home_forest-dark.png)
- [main-window_home_forest-light.png](themes/main-window_home_forest-light.png)
- [main-window_home_lavender-dark.png](themes/main-window_home_lavender-dark.png)
- [main-window_home_lavender-light.png](themes/main-window_home_lavender-light.png)
- [main-window_home_midnight-dark.png](themes/main-window_home_midnight-dark.png)
- [main-window_home_midnight-light.png](themes/main-window_home_midnight-light.png)
- [main-window_home_ocean-dark.png](themes/main-window_home_ocean-dark.png)
- [main-window_home_ocean-light.png](themes/main-window_home_ocean-light.png)
- [main-window_home_sunset-dark.png](themes/main-window_home_sunset-dark.png)
- [main-window_home_sunset-light.png](themes/main-window_home_sunset-light.png)
- [main-window_insights_classic-dark.png](themes/main-window_insights_classic-dark.png)
- [main-window_insights_classic-light.png](themes/main-window_insights_classic-light.png)
- [main-window_insights_forest-dark.png](themes/main-window_insights_forest-dark.png)
- [main-window_insights_forest-light.png](themes/main-window_insights_forest-light.png)
- [main-window_insights_lavender-dark.png](themes/main-window_insights_lavender-dark.png)
- [main-window_insights_lavender-light.png](themes/main-window_insights_lavender-light.png)
- [main-window_insights_midnight-dark.png](themes/main-window_insights_midnight-dark.png)
- [main-window_insights_midnight-light.png](themes/main-window_insights_midnight-light.png)
- [main-window_insights_ocean-dark.png](themes/main-window_insights_ocean-dark.png)
- [main-window_insights_ocean-light.png](themes/main-window_insights_ocean-light.png)
- [main-window_insights_sunset-dark.png](themes/main-window_insights_sunset-dark.png)
- [main-window_insights_sunset-light.png](themes/main-window_insights_sunset-light.png)
- [main-window_notetaker_classic-dark.png](themes/main-window_notetaker_classic-dark.png)
- [main-window_notetaker_classic-light.png](themes/main-window_notetaker_classic-light.png)
- [main-window_notetaker_forest-dark.png](themes/main-window_notetaker_forest-dark.png)
- [main-window_notetaker_forest-light.png](themes/main-window_notetaker_forest-light.png)
- [main-window_notetaker_lavender-dark.png](themes/main-window_notetaker_lavender-dark.png)
- [main-window_notetaker_lavender-light.png](themes/main-window_notetaker_lavender-light.png)
- [main-window_notetaker_midnight-dark.png](themes/main-window_notetaker_midnight-dark.png)
- [main-window_notetaker_midnight-light.png](themes/main-window_notetaker_midnight-light.png)
- [main-window_notetaker_ocean-dark.png](themes/main-window_notetaker_ocean-dark.png)
- [main-window_notetaker_ocean-light.png](themes/main-window_notetaker_ocean-light.png)
- [main-window_notetaker_sunset-dark.png](themes/main-window_notetaker_sunset-dark.png)
- [main-window_notetaker_sunset-light.png](themes/main-window_notetaker_sunset-light.png)

## note-window/ (20)

The meeting note side panel, in order: permission needed, ready, recording, each tab, an answered question, the save card, the save question on close, and saved with a summary.

- [note_0-needs-screen-audio-permission_classic-dark.png](note-window/note_0-needs-screen-audio-permission_classic-dark.png)
- [note_0-needs-screen-audio-permission_classic-light.png](note-window/note_0-needs-screen-audio-permission_classic-light.png)
- [note_1-ready-to-record_classic-dark.png](note-window/note_1-ready-to-record_classic-dark.png)
- [note_1-ready-to-record_classic-light.png](note-window/note_1-ready-to-record_classic-light.png)
- [note_2-recording-live-transcript_classic-dark.png](note-window/note_2-recording-live-transcript_classic-dark.png)
- [note_2-recording-live-transcript_classic-light.png](note-window/note_2-recording-live-transcript_classic-light.png)
- [note_3-recording_summary-tab_classic-dark.png](note-window/note_3-recording_summary-tab_classic-dark.png)
- [note_3-recording_summary-tab_classic-light.png](note-window/note_3-recording_summary-tab_classic-light.png)
- [note_3-recording_thoughts-tab_classic-dark.png](note-window/note_3-recording_thoughts-tab_classic-dark.png)
- [note_3-recording_thoughts-tab_classic-light.png](note-window/note_3-recording_thoughts-tab_classic-light.png)
- [note_3-recording_transcript-tab_classic-dark.png](note-window/note_3-recording_transcript-tab_classic-dark.png)
- [note_3-recording_transcript-tab_classic-light.png](note-window/note_3-recording_transcript-tab_classic-light.png)
- [note_4-recording-question-answered_classic-dark.png](note-window/note_4-recording-question-answered_classic-dark.png)
- [note_4-recording-question-answered_classic-light.png](note-window/note_4-recording-question-answered_classic-light.png)
- [note_5-stopped-save-card_classic-dark.png](note-window/note_5-stopped-save-card_classic-dark.png)
- [note_5-stopped-save-card_classic-light.png](note-window/note_5-stopped-save-card_classic-light.png)
- [note_6-closing-save-question_classic-dark.png](note-window/note_6-closing-save-question_classic-dark.png)
- [note_6-closing-save-question_classic-light.png](note-window/note_6-closing-save-question_classic-light.png)
- [note_7-saved-with-summary_classic-dark.png](note-window/note_7-saved-with-summary_classic-dark.png)
- [note_7-saved-with-summary_classic-light.png](note-window/note_7-saved-with-summary_classic-light.png)

## setup-window/ (9)

The first-run setup window (Python): welcome, permissions, optional features, model downloads, ready.

- [setup-window_models_downloading_system-light.png](setup-window/setup-window_models_downloading_system-light.png)
- [setup-window_models_error_system-light.png](setup-window/setup-window_models_error_system-light.png)
- [setup-window_models_ready_system-light.png](setup-window/setup-window_models_ready_system-light.png)
- [setup-window_optional_features_system-light.png](setup-window/setup-window_optional_features_system-light.png)
- [setup-window_permissions_none_system-light.png](setup-window/setup-window_permissions_none_system-light.png)
- [setup-window_permissions_required_done_system-light.png](setup-window/setup-window_permissions_required_done_system-light.png)
- [setup-window_permissions_system-dark.png](setup-window/setup-window_permissions_system-dark.png)
- [setup-window_ready_system-light.png](setup-window/setup-window_ready_system-light.png)
- [setup-window_welcome_system-light.png](setup-window/setup-window_welcome_system-light.png)

## floating-widget/ (21)

The floating dictation pill (Python): idle, hover, hold, hands-free, processing, cancelled, meeting, setup and error states.

- [floating-widget_cancelled_plain.png](floating-widget/floating-widget_cancelled_plain.png)
- [floating-widget_cancelled_undo.png](floating-widget/floating-widget_cancelled_undo.png)
- [floating-widget_handsfree_cancel.png](floating-widget/floating-widget_handsfree_cancel.png)
- [floating-widget_handsfree_finish.png](floating-widget/floating-widget_handsfree_finish.png)
- [floating-widget_handsfree_plain.png](floating-widget/floating-widget_handsfree_plain.png)
- [floating-widget_handsfree_wave.png](floating-widget/floating-widget_handsfree_wave.png)
- [floating-widget_hold_incognito.png](floating-widget/floating-widget_hold_incognito.png)
- [floating-widget_hold_mic_notice.png](floating-widget/floating-widget_hold_mic_notice.png)
- [floating-widget_hold_plain.png](floating-widget/floating-widget_hold_plain.png)
- [floating-widget_hover_mic.png](floating-widget/floating-widget_hover_mic.png)
- [floating-widget_hover_note.png](floating-widget/floating-widget_hover_note.png)
- [floating-widget_hover_plain.png](floating-widget/floating-widget_hover_plain.png)
- [floating-widget_idle_copied_notice.png](floating-widget/floating-widget_idle_copied_notice.png)
- [floating-widget_idle_plain.png](floating-widget/floating-widget_idle_plain.png)
- [floating-widget_meeting_plain.png](floating-widget/floating-widget_meeting_plain.png)
- [floating-widget_meeting_stop.png](floating-widget/floating-widget_meeting_stop.png)
- [floating-widget_mistake_keep.png](floating-widget/floating-widget_mistake_keep.png)
- [floating-widget_mistake_plain.png](floating-widget/floating-widget_mistake_plain.png)
- [floating-widget_processing_plain.png](floating-widget/floating-widget_processing_plain.png)
- [floating-widget_setup_plain.png](floating-widget/floating-widget_setup_plain.png)
- [floating-widget_setup_retry.png](floating-widget/floating-widget_setup_retry.png)
