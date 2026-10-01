# `macos/Tests/MisprCoreTests/CoreTests.swift`

121 tests. Source: [`macos/Tests/MisprCoreTests/CoreTests.swift`](../../macos/Tests/MisprCoreTests/CoreTests.swift).


## EngineProtocolTests

- `testHello`: hello
- `testSaved`: saved
- `testNoteAndMeetingEvents`: note and meeting events
- `testEngineTracksMeetingAndNoteRequests`: engine tracks meeting and note requests
- `testIgnoresOtherOutput`: ignores other output
- `testTried`: tried
- `testUnknownEventsAreKept`: unknown events are kept
- `testCommandsAreJSONLines`: commands are jsonlines
- `testLineSplitterHoldsPartialLines`: line splitter holds partial lines

## EngineTests

- `testConfigFromInfoPlist`: config from info plist
- `testEnvironmentOverridesAndVenvDefault`: environment overrides and venv default
- `testNoConfigFails`: no config fails
- `testHelloMarksRunningAndStoresPaths`: hello marks running and stores paths
- `testSavedIsRelayed`: saved is relayed
- `testCleanExitQuitsTheApp`: clean exit quits the app
- `testCrashLoopGivesUp`: crash loop gives up
- `testOldCrashesAreForgotten`: old crashes are forgotten
- `testStoppingIsNotACrash`: stopping is not acrash

## RecordingTests

- `testDecodesTheEnginesFormat`: decodes the engines format
- `testNewestFirstAndBadFilesSkipped`: newest first and bad files skipped
- `testMissingFolderIsEmpty`: missing folder is empty
- `testDeleteRemovesJSONAndAudio`: delete removes jsonand audio

## StatsTests

- `testTotalsAndWPMSkipCancelled`: totals and wpmskip cancelled
- `testCopiedCountsAsDelivered`: copied counts as delivered
- `testStreakCountsBackFromToday`: streak counts back from today
- `testStreakSurvivesUntilTheDayIsOver`: streak survives until the day is over
- `testLongestStreakCanBeInThePast`: longest streak can be in the past
- `testPerDayCounts`: per day counts
- `testCategoriesAndApps`: categories and apps
- `testURLBeatsBundle`: urlbeats bundle
- `testCleanedCount`: cleaned count
- `testEmpty`: empty
- `testVoiceProfile`: voice profile

## SettingsFileTests

- `testDefaultsWhenMissing`: defaults when missing
- `testSetKeepsOtherKeys`: set keeps other keys

## ProfileTests

- `testGreetingPrefersNickname`: greeting prefers nickname
- `testGreetingFallsBackToFirstNameThenAccount`: greeting falls back to first name then account
- `testInitials`: initials

## PromptDraftTests

- `testExamplesTextMatchesPython`: examples text matches python
- `testMissingFileUsesDefaults`: missing file uses defaults
- `testRoundTrip`: round trip
- `testBlankSystemFallsBack`: blank system falls back

## MoreInsightsTests

- `testTimeSaved`: time saved
- `testWeekOverWeek`: week over week
- `testFillersRemovedOnlyCountsWhatCleanupTookOut`: fillers removed only counts what cleanup took out
- `testUniqueWordsHoursAndApps`: unique words hours and apps
- `testDailyPace`: daily pace
- `testPersona`: persona
- `testEquivalents`: equivalents
- `testEmpty`: empty

## FunFactsTests

- `testFunFacts`: fun facts
- `testShortDictationsDontCountAsFastest`: short dictations dont count as fastest

## DictationKeyTests

- `testModifiers`: modifiers
- `testKeys`: keys
- `testSavedInSettings`: saved in settings

## VoiceStyleTests

- `testStyleSignals`: style signals
- `testStyleThresholds`: style thresholds

## MeetingTests

- `testTalkTimeTurnsAndMonologue`: talk time turns and monologue
- `testEmptyTranscript`: empty transcript
- `testOverview`: overview
- `testDurationText`: duration text
- `testLoadsTheSampleFormat`: loads the sample format

## MeetingDetectorTests

- `testZoomAppInAMeeting`: zoom app in ameeting
- `testZoomOpenButNotInACallIsInPerson`: zoom open but not in acall is in person
- `testGoogleMeetTabWithName`: google meet tab with name
- `testMeetCodeIsNotAName`: meet code is not aname
- `testBrowserCallsNeedTheMic`: browser calls need the mic
- `testCallAppsNeedTheMic`: call apps need the mic
- `testSlackHuddle`: slack huddle
- `testZoomBeatsAnIdleMeetTab`: zoom beats an idle meet tab
- `testUnknownMicUserIsACall`: unknown mic user is acall
- `testNothingIsInPerson`: nothing is in person

## LiveMeetingTests

- `testCutsAtAPause`: cuts at apause
- `testLongSpeechIsCutAtMax`: long speech is cut at max
- `testQuietContinuousSpeechKeepsComing`: quiet continuous speech keeps coming
- `testInProgressShowsTheCurrentPhrase`: in progress shows the current phrase
- `testSilenceProducesNothing`: silence produces nothing
- `testFeedInSmallPieces`: feed in small pieces
- `testWAVHeader`: wavheader
- `testTranscriptOrderLabelsAndGroups`: transcript order labels and groups
- `testSavesAsAMeetingTheNotesPageCanRead`: saves as ameeting the notes page can read

## PeopleIndexTests

- `testPeopleAreCountedAndSorted`: people are counted and sorted
- `testTogetherNeedsEveryoneSelected`: together needs everyone selected
- `testActionItemsMatchFullOrFirstName`: action items match full or first name
- `testGroupStats`: group stats

## LivePreviewTests

- `testPartialShowsThenFinalReplacesIt`: partial shows then final replaces it
- `testLatePartialForAFinishedPhraseIsIgnored`: late partial for afinished phrase is ignored
- `testFinalWithNoWordsStillClearsThePreview`: final with no words still clears the preview
- `testPartialLabelFollowsTheLastSpeaker`: partial label follows the last speaker
- `testPartialEventParses`: partial event parses

## NoteEditingTests

Deleting notes, renaming and removing people across notes, and contact cards.

- `testDeleteRemovesTheJSONAndItsAudioFolder`: delete removes the jsonand its audio folder
- `testDeletingANoteWithoutAFileDoesNothing`: deleting anote without afile does nothing
- `testRenameChangesParticipantsLinesAndActionItemsEverywhere`: rename changes participants lines and action items everywhere
- `testRenamingIntoSomeoneAlreadyThereMergesThem`: renaming into someone already there merges them
- `testRenameNeverTouchesYouOrBlankNames`: rename never touches you or blank names
- `testRemoveKeepsTheNoteButMakesTheirLinesUnknown`: remove keeps the note but makes their lines unknown
- `testRewriteNeedsAFile`: rewrite needs afile
- `testContactBookSavesLoadsAndDropsEmptyCards`: contact book saves loads and drops empty cards
- `testNoteIDsHaveMillisecondsSoBackToBackNotesDiffer`: note ids have milliseconds so back to back notes differ
- `testContactCardMovesWithARename`: contact card moves with arename

## ChunkLinesTests

The app switcher key and nicknames in settings.json, and combo shortcuts.

- `testLastDefaultsToTrueAndCanBeFalse`: last defaults to true and can be false

## SwitchKeyTests

- `testCombosNeedAKeyOrTwoModifiersAndReadInMacOrder`: combos need akey or two modifiers and read in mac order
- `testCombosRoundTripThroughJSONWithANullKey`: combos round trip through jsonwith anull key
- `testSwitchKeyAndNicknamesInTheSettingsFile`: switch key and nicknames in the settings file
- `testSettingsChangedEventParses`: settings changed event parses

## EchoTests

Speakers instead of headphones: the mic hears the call again. Those words must show once (as the other side), never duplicated as "You". Examples from a real test meeting.

- `testWordsIgnorePunctuationAndCase`: words ignore punctuation and case
- `testAMicLineThatRepeatsThemIsDropped`: amic line that repeats them is dropped
- `testYourOwnWordsAreKept`: your own words are kept
- `testTalkingOverTheEchoKeepsYourPart`: talking over the echo keeps your part
- `testShortRepliesNeedTwoWordsToCountAsEcho`: short replies need two words to count as echo
- `testTranscriptDropsEchoWhicheverArrivesFirst`: transcript drops echo whichever arrives first
- `testEchoOnlyCountsNearbyInTime`: echo only counts nearby in time
- `testEchoNeverShowsAsALiveLine`: echo never shows as alive line

## EchoGateTests

The call coming back in through the mic (speakers, no headphones) is silenced before it becomes "You"; your own voice, and everything with headphones, gets through.

- `testPureEchoIsSilenced`: pure echo is silenced
- `testYourVoiceGetsThroughEvenOverTheCall`: your voice gets through even over the call
- `testHeadphonesLetEverythingThrough`: headphones let everything through
- `testNoCallMeansNothingIsTouched`: no call means nothing is touched
- `testMicIsHeldBackBrieflyThenReleased`: mic is held back briefly then released

## SpeakerMergeTests

Two voices that turn out to be one person are merged: their lines relabelled, names kept.

- `testMergeRelabelsLinesAndKeepsAName`: merge relabels lines and keeps aname
- `testMergedEventParses`: merged event parses

## CommandHistoryTests

Voice commands are kept in history but aren't dictation: no word counts or speed.

- `testCommandsAreReadAndLeftOutOfStats`: commands are read and left out of stats
