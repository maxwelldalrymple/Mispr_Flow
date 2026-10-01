# `macos/Tests/MisprFlowTests/SystemTests.swift`

19 tests. Source: [`macos/Tests/MisprFlowTests/SystemTests.swift`](../../macos/Tests/MisprFlowTests/SystemTests.swift).


## RecorderPartsTests

The parts that touch audio and the system, tested without a microphone, plus the app's menus and windows.

- `testResamplerMakes16kMonoWithOnlyASmallHoldback`: resampler makes16k mono with only asmall holdback
- `testResamplerIgnoresEmptyBuffers`: resampler ignores empty buffers
- `testStreamingWAVWritesAPlayableFile`: streaming wavwrites aplayable file
- `testRecorderChunksAtPausesAndMeters`: recorder chunks at pauses and meters
- `testCMSampleBufferWithNoAudioGivesNothing`: cmsample buffer with no audio gives nothing
- `testRecorderErrorReadsWell`: recorder error reads well

## SystemProbeTests

- `testSeesRunningProcessesIncludingItself`: sees running processes including itself
- `testMicStatusIsReadable`: mic status is readable
- `testNoWindowTitlesForAProcessWithoutWindows`: no window titles for aprocess without windows
- `testSnapshotListsRunningApps`: snapshot lists running apps
- `testSplitScreenNeedsTheCallsApp`: split screen needs the calls app
- `testNoAccessibilityWindowForAMissingProcess`: no accessibility window for amissing process

## AppShellTests

- `testMainMenu`: main menu
- `testMainWindowIsBuiltButNotShown`: main window is built but not shown
- `testKeepsRunningWithTheWindowClosed`: keeps running with the window closed
- `testSettingsAndSetupGuideMenuActions`: settings and setup guide menu actions
- `testShowSettingsOpensTheWindowOnSettings`: show settings opens the window on settings
- `testNoteWindowSlidesInAndOut`: note window slides in and out
- `testClosingWithAnUnsavedNoteKeepsThePanelAndAsks`: closing with an unsaved note keeps the panel and asks
