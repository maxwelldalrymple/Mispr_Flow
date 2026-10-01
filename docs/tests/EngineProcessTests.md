# `macos/Tests/MisprCoreTests/EngineProcessTests.swift`

12 tests. Source: [`macos/Tests/MisprCoreTests/EngineProcessTests.swift`](../../macos/Tests/MisprCoreTests/EngineProcessTests.swift).


## EngineProcessTests

The engine as a real child process, using a small shell script in place of Python: it announces itself, echoes one command back as an event, logs to stderr, then waits.

- `testStartsTalksLogsAndStops`: starts talks logs and stops
- `testCleanExitQuitsTheApp`: clean exit quits the app
- `testCrashRestartsTheEngine`: crash restarts the engine
- `testMissingProgramFails`: missing program fails
- `testSendWithoutAProcessIsIgnored`: send without aprocess is ignored
- `testStopWithoutAProcessIsHarmless`: stop without aprocess is harmless

## CoreGapTests

- `testTryArgs`: try args
- `testDefaultSettingsLocation`: default settings location
- `testEveryMeetingSourceHasASymbolAndID`: every meeting source has asymbol and id
- `testSpeakerPace`: speaker pace
- `testStatsEquality`: stats equality
- `testUsageCategoryID`: usage category id
