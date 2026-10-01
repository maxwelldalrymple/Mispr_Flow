# `macos/Tests/MisprFlowTests/AppModelTests.swift`

34 tests. Source: [`macos/Tests/MisprFlowTests/AppModelTests.swift`](../../macos/Tests/MisprFlowTests/AppModelTests.swift).


## AppModelTests

AppModel: settings, the dictation key, loading and deleting recordings, profile, and how it reacts to the engine's events.

- `testSettingsReadDefaultsBeforeAnyFileExists`: settings read defaults before any file exists
- `testSwitchKeyAndNicknames`: switch key and nicknames
- `testANicknameSetByVoiceRefreshesTheApp`: anickname set by voice refreshes the app
- `testAutoEnterButtonTogglesTheSettingForTheEngine`: auto enter button toggles the setting for the engine
- `testChangingASettingWritesTheFileAndTellsTheEngine`: changing asetting writes the file and tells the engine
- `testBindingReadsAndWrites`: binding reads and writes
- `testUnwritableSettingsShowAnError`: unwritable settings show an error
- `testDictationKeyRoundTripsAndReloadsTheEngine`: dictation key round trips and reloads the engine
- `testRecordingsAndStatsLoadAfterHello`: recordings and stats load after hello
- `testSavedEventReloadsHistory`: saved event reloads history
- `testMeetingsLoadFromTheFolderNextToRecordings`: meetings load from the folder next to recordings
- `testDeleteRemovesTheFilesAndReloads`: delete removes the files and reloads
- `testFirstNameUsesTheProfile`: first name uses the profile
- `testOpenProfileShowsSettingsOnProfile`: open profile shows settings on profile
- `testLaunchAtLoginReadsWithoutChangingAnything`: launch at login reads without changing anything
- `testNoteRequestOpensTheNoteAndStartsRecording`: note request opens the note and starts recording
- `testMeetingEventsReachTheNote`: meeting events reach the note
- `testEngineStoppingTheMeetingStopsTheNote`: engine stopping the meeting stops the note

## ProfileTests

Profile: what's remembered, the photo, and the theme and appearance it applies.

- `testEverythingIsRememberedAcrossLaunches`: everything is remembered across launches
- `testDefaults`: defaults
- `testThemeChangesThePaletteEverythingDrawsWith`: theme changes the palette everything draws with
- `testAppearanceIsAppliedToTheApp`: appearance is applied to the app
- `testPhotoIsSavedSquareAndCanBeRemoved`: photo is saved square and can be removed
- `testSquareThumbnailCropsTheMiddle`: square thumbnail crops the middle

## ThemeTests

Theme: palettes, the colors charts use, and hex parsing.

- `testSixPalettesWithUniqueNames`: six palettes with unique names
- `testUnknownThemeFallsBackToClassic`: unknown theme falls back to classic
- `testHexColors`: hex colors
- `testResolvedColorsFollowThePaletteAndScheme`: resolved colors follow the palette and scheme
- `testDisplayFontIsSerif`: display font is serif

## NotesAndPeopleActionsTests

Deleting notes, and renaming, removing and adding details for people, from the app.

- `testDeleteMeetingsRemovesThemAtOnceAndOnDisk`: delete meetings removes them at once and on disk
- `testRenamePersonEverywhereAndMoveTheirCard`: rename person everywhere and move their card
- `testSaveContactWithANewNameRenamesToo`: save contact with anew name renames too
- `testRemovePersonKeepsTheNotesAndDropsTheirCard`: remove person keeps the notes and drops their card
- `testFailuresShowAMessage`: failures show amessage
