# `macos/Tests/MisprFlowTests/RenderTests.swift`

20 tests. Source: [`macos/Tests/MisprFlowTests/RenderTests.swift`](../../macos/Tests/MisprFlowTests/RenderTests.swift).


## RenderTests

Every page and state is laid out and drawn offscreen, with data, so each view's `body` (and everything it calls) runs; a crash or a blank render fails the test.

- `testEveryPageInTheMainWindow`: every page in the main window
- `testHomeVoiceCommandsCardWithAndWithoutASwitchKey`: home voice commands card with and without aswitch key
- `testHomeCommandsTab`: home commands tab
- `testHomeEmpty`: home empty
- `testInsightsBothTabs`: insights both tabs
- `testInsightsPiecesOnTheirOwn`: insights pieces on their own
- `testNotetakerTabsAndDetail`: notetaker tabs and detail
- `testNoteRowsInSelectModeAndWithDelete`: note rows in select mode and with delete
- `testPeopleWithContactDetailsAndTheEditor`: people with contact details and the editor
- `testNotetakerWithNoMeetings`: notetaker with no meetings
- `testPromptsPageWithAndWithoutTheEngine`: prompts page with and without the engine
- `testSettingsEverySection`: settings every section
- `testSettingsWithTheAppSwitcherAndNicknames`: settings with the app switcher and nicknames
- `testIncognitoLook`: incognito look
- `testEngineBanners`: engine banners
- `testEveryTheme`: every theme
- `testSmallPieces`: small pieces
- `testSourceChipChoicesChangeTheMeetingType`: source chip choices change the meeting type
- `testNoteWindowInEveryPhase`: note window in every phase
- `testNoteWindowPermissionCardAndWarning`: note window permission card and warning
