# `macos/Tests/MisprFlowTests/NoteModelTests.swift`

36 tests. Source: [`macos/Tests/MisprFlowTests/NoteModelTests.swift`](../../macos/Tests/MisprFlowTests/NoteModelTests.swift).


## NoteModelTests

NoteModel: a meeting note from Start to saved summary, with a fake recorder (no mic).

- `testStartRecordsAndShowsTheWidgetPill`: start records and shows the widget pill
- `testIncognitoKeepsNoAudio`: incognito keeps no audio
- `testCallsWithoutPermissionWaitForTheSetupCard`: calls without permission wait for the setup card
- `testInPersonNeedsNoPermission`: in person needs no permission
- `testBlockedSystemAudioKeepsTheMicAndOffersTurnOn`: blocked system audio keeps the mic and offers turn on
- `testMicFailureStopsWithAMessage`: mic failure stops with amessage
- `testChunksAreWrittenAndSentToTheEngine`: chunks are written and sent to the engine
- `testFinalAndLiveTextAppear`: final and live text appear
- `testAChunkSplitBetweenTwoPeopleCountsAsOneChunk`: achunk split between two people counts as one chunk
- `testMergedSpeakersShowAsOnePerson`: merged speakers show as one person
- `testOtherMeetingsEventsAreIgnored`: other meetings events are ignored
- `testPreviewSendsTheGrowingPhraseOnce`: preview sends the growing phrase once
- `testLiveTextRefreshesTwiceASecond`: live text refreshes twice asecond
- `testRenameASpeaker`: rename aspeaker
- `testStopAsksForASummaryButSavesNothingUntilSave`: stop asks for asummary but saves nothing until save
- `testSummaryArrivesWithATitleAndUpdatesTheSavedNote`: summary arrives with atitle and updates the saved note
- `testYourTitleIsKept`: your title is kept
- `testSilentMeetingIsNotSaved`: silent meeting is not saved
- `testIncognitoNoteIsNotSaved`: incognito note is not saved
- `testResumeContinuesTheSameNoteLaterInTime`: resume continues the same note later in time
- `testToggleStartsANewNoteAfterOneIsDone`: toggle starts anew note after one is done
- `testSaveWhileRecordingStopsAndSavesOnceTheWordsAreIn`: save while recording stops and saves once the words are in
- `testDiscardDeletesTheAudioAndStartsFresh`: discard deletes the audio and starts fresh
- `testDiscardWhileFinishingIgnoresTheLateWords`: discard while finishing ignores the late words
- `testClosingAnEmptyOrSavedNoteJustCloses`: closing an empty or saved note just closes
- `testClosingWithUnsavedWordsAsksAndEachAnswerWorks`: closing with unsaved words asks and each answer works
- `testDiscardFromTheQuestionClosesWithoutSaving`: discard from the question closes without saving
- `testStartingANewNoteOverAnUnsavedOneAsksFirst`: starting anew note over an unsaved one asks first
- `testIncognitoNotesOnlyAskWhileRecording`: incognito notes only ask while recording
- `testStopForQuitStopsTheRecorder`: stop for quit stops the recorder
- `testAskAndWhatDidIMiss`: ask and what did imiss
- `testPlainTextForShare`: plain text for share
- `testDetectionFillsTheSourceAndTitle`: detection fills the source and title
- `testDetectionStopsOnceRecording`: detection stops once recording
- `testStartAndStopDetectingManageTheTimer`: start and stop detecting manage the timer
- `testRefreshPermissionReadsTheCheck`: refresh permission reads the check
