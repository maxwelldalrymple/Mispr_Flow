# `macos/Tests/MisprFlowTests/ViewLogicTests.swift`

29 tests. Source: [`macos/Tests/MisprFlowTests/ViewLogicTests.swift`](../../macos/Tests/MisprFlowTests/ViewLogicTests.swift).


## KeyPickTests

The logic that lives behind the views: picking a key, the transcript's timer and search, where the note window docks, the word-cloud layout, day groups, colors, and dev reports.

- `testEscCancels`: esc cancels
- `testFunctionKeyIsChosenWithoutWarning`: function key is chosen without warning
- `testTypingKeyComesWithAWarning`: typing key comes with awarning
- `testHandsFreeKeysAreRefused`: hands free keys are refused
- `testModifierCountsOnPressNotRelease`: modifier counts on press not release
- `testModifierFlagsBySide`: modifier flags by side

## TranscriptTextTests

- `testElapsed`: elapsed
- `testMatchCount`: match count
- `testHighlightMarksEveryMatch`: highlight marks every match

## LayoutTests

- `testNoteWindowDocksRightFullHeight`: note window docks right full height
- `testFlowLayoutWraps`: flow layout wraps
- `testFlowLayoutPutsAnOversizedItemOnItsOwnLine`: flow layout puts an oversized item on its own line
- `testDayGroupsNewestFirstWithFriendlyTitles`: day groups newest first with friendly titles
- `testSpeakerColors`: speaker colors

## DevToolsTests

- `testDetectReport`: detect report
- `testMicPermissionNames`: mic permission names
- `testSegmentReport`: segment report

## NotesWordingTests

Wording and small rules behind the save, delete and people screens.

- `testDeleteConfirmationTitles`: delete confirmation titles
- `testSaveCardDetail`: save card detail
- `testSaveQuestionTitles`: save question titles
- `testSelectionFollowsARename`: selection follows arename
- `testPersonSubtitlePrefersTheirCard`: person subtitle prefers their card
- `testContactEditorKnowsARename`: contact editor knows arename

## ComboPickerTests

Picking the app switcher key: one key, one modifier side, a modifier combo, or modifiers + a key.

- `testAModifierComboIsChosenWhenLetGo`: amodifier combo is chosen when let go
- `testOneModifierSideOnItsOwn`: one modifier side on its own
- `testModifiersPlusAKey`: modifiers plus akey
- `testAPlainKeyWarnsIfItTypes`: aplain key warns if it types
- `testEscCancelsBlockedKeysAndFnAndTheDictationKeyAreRefused`: esc cancels blocked keys and fn and the dictation key are refused
- `testInstalledAppsAreListedByName`: installed apps are listed by name
