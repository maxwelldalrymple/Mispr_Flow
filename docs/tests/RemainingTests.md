# `macos/Tests/MisprFlowTests/RemainingTests.swift`

15 tests. Source: [`macos/Tests/MisprFlowTests/RemainingTests.swift`](../../macos/Tests/MisprFlowTests/RemainingTests.swift).


## AppLifecycleTests

The last functions coverage found untested: app lifecycle, playback, the permission request, prompt saving, person navigation, small text helpers, and the recorder's system-audio callbacks.

- `testLaunchSetsUpTheMenuStartsTheEngineAndShowsTheWindow`: launch sets up the menu starts the engine and shows the window
- `testClickingTheDockIconShowsTheWindow`: clicking the dock icon shows the window
- `testModelStartOpensTheRequestedPage`: model start opens the requested page

## PlayerTests

- `testPlayToggleAndStop`: play toggle and stop
- `testFinishingClearsThePlayingRow`: finishing clears the playing row
- `testMissingAudioDoesNothing`: missing audio does nothing

## SmallHelperTests

- `testSnippet`: snippet
- `testSpeedupVersusTyping`: speedup versus typing
- `testPersonPage`: person page
- `testSavingPromptsWritesAndReloads`: saving prompts writes and reloads
- `testSavingPromptsSomewhereUnwritableSaysSo`: saving prompts somewhere unwritable says so

## PermissionRequestTests

- `testAskingOpensSettingsWhenMacOSSaysNoThenWatchesForTheSwitch`: asking opens settings when mac ossays no then watches for the switch
- `testNoSettingsPaneWhenMacOSAlreadyAllows`: no settings pane when mac osalready allows

## RecorderCallbackTests

- `testSystemAudioArrivesAsThemAndIsMetered`: system audio arrives as them and is metered
- `testStreamStoppingReportsAnError`: stream stopping reports an error
