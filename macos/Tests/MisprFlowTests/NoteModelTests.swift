@testable import MisprCore
import XCTest
@testable import MisprFlow

/// NoteModel: a meeting note from Start to saved summary, with a fake recorder (no mic).
final class NoteModelTests: XCTestCase {
    var t: TestApp!
    var recorder: FakeRecorder!
    var note: NoteModel { t.model.note }

    override func setUp() {
        t = TestApp()
        recorder = FakeRecorder()
        note.makeRecorder = { [unowned self] in self.recorder }
        note.chosenSource = .inPerson
        note.permissionCheck = { true }  // never depend on this Mac's real permissions
        note.probe = { SystemSnapshot() }
    }

    func speech(_ seconds: Double = 1.2) -> [Float] {
        (0..<Int(seconds * 16_000)).map { i in Float(sin(Double(i) * 0.2)) * ((i / 2_400) % 4 == 3 ? 0.03 : 0.3) }
    }

    func say(_ stream: String, _ offset: Double, _ text: String, speaker: Int = 1, voice: String = "female", partial: Bool = false) {
        t.event(["event": "chunk_text", "id": note.meetingID, "stream": stream, "speaker": speaker, "offset": offset,
                 "text": text, "voice": voice, "partial": partial])
    }

    // MARK: start

    func testStartRecordsAndShowsTheWidgetPill() {
        note.start()
        drainMain()
        XCTAssertEqual(note.phase, .recording)
        XCTAssertNotNil(note.startedAt)
        XCTAssertEqual(t.commands, [.startMeeting])
        XCTAssertEqual(recorder.started?.systemAudio, true)  // always tries the Mac's sound
        let saveTo = try? XCTUnwrap(recorder.started?.saveTo)  // meeting-recordings/<day>/<id>
        XCTAssertEqual(saveTo?.lastPathComponent, note.meetingID)
        XCTAssertEqual(saveTo?.deletingLastPathComponent().deletingLastPathComponent().lastPathComponent, "meeting-recordings")
    }

    func testIncognitoKeepsNoAudio() {
        t.model.setSetting("incognito", true)
        note.start()
        drainMain()
        XCTAssertNil(recorder.started?.saveTo)
    }

    func testCallsWithoutPermissionWaitForTheSetupCard() {
        note.chosenSource = .zoom
        note.permissionCheck = { false }
        note.refreshPermission()
        XCTAssertTrue(note.needsPermission)
        note.start()
        XCTAssertEqual(note.phase, .ready)
        XCTAssertNil(recorder.started)
    }

    func testInPersonNeedsNoPermission() {
        note.screenAudioAllowed = false
        XCTAssertFalse(note.needsPermission)
    }

    func testBlockedSystemAudioKeepsTheMicAndOffersTurnOn() {
        recorder.warning = "Screen & System Audio isn't allowed"
        note.start()
        drainMain()
        XCTAssertEqual(note.phase, .recording)
        XCTAssertTrue(note.systemAudioBlocked)
        XCTAssertEqual(note.error, "Screen & System Audio isn't allowed")
    }

    func testMicFailureStopsWithAMessage() {
        recorder.failure = RecorderError("No microphone is available.")
        note.start()
        drainMain()
        XCTAssertNotEqual(note.phase, .recording)
        XCTAssertTrue(note.error?.contains("No microphone") ?? false)
    }

    // MARK: transcript

    func testChunksAreWrittenAndSentToTheEngine() throws {
        note.start()
        drainMain()
        recorder.onChunk("them", 2.5, speech())
        drainMain()
        let (command, args) = try XCTUnwrap(t.sent.last)
        XCTAssertEqual(command, .transcribeChunk)
        XCTAssertEqual(args["stream"] as? String, "them")
        XCTAssertEqual(args["offset"] as? Double, 2.5)
        XCTAssertTrue(FileManager.default.fileExists(atPath: args["path"] as! String))
    }

    func testFinalAndLiveTextAppear() {
        note.start()
        say("them", 3, "Let's ship", partial: true)
        XCTAssertEqual(note.transcript.partials["them"]?.text, "Let's ship")
        say("them", 3, "Let's ship on Friday.")
        XCTAssertNil(note.transcript.partials["them"])
        XCTAssertEqual(note.transcript.groups.map(\.label), ["Female 1"])
    }

    func testOtherMeetingsEventsAreIgnored() {
        t.event(["event": "chunk_text", "id": "someone-else", "stream": "you", "speaker": 0, "offset": 0.0, "text": "Hi."])
        XCTAssertTrue(note.transcript.lines.isEmpty)
    }

    func testPreviewSendsTheGrowingPhraseOnce() throws {
        note.start()
        drainMain()
        recorder.current = [("you", 4, speech(1.0))]
        note.preview()
        drainMain(0.4)
        let previews = t.sent.filter { $0.0 == .transcribeChunk }
        XCTAssertEqual(previews.count, 1)
        XCTAssertEqual(previews[0].1["partial"] as? Bool, true)
        note.preview()  // nothing new heard: no second request
        drainMain(0.4)
        XCTAssertEqual(t.sent.filter { $0.0 == .transcribeChunk }.count, 1)
        recorder.current = [("you", 4, speech(1.5))]
        note.preview()
        drainMain(0.4)
        XCTAssertEqual(t.sent.filter { $0.0 == .transcribeChunk }.count, 2)
    }

    func testRenameASpeaker() {
        note.start()
        say("them", 1, "Hello.", speaker: 2, voice: "male")
        note.rename(speaker: 2, to: " Jordan ")
        XCTAssertEqual(note.transcript.groups.first?.label, "Jordan")
    }

    // MARK: stop, save, summary

    func testStopSavesTheNoteAndAsksForASummary() throws {
        note.start()
        drainMain()
        say("you", 0.5, "Let's ship Friday.", speaker: 0, voice: "")
        note.stop()
        XCTAssertEqual(recorder.stopped, 1)
        drainMain(0.8)
        XCTAssertEqual(note.phase, .done)
        XCTAssertTrue(note.summarizing)
        XCTAssertEqual(t.commands.suffix(2), [.stopMeeting, .summarize])
        let saved = MeetingStore.load(from: t.meetings)
        XCTAssertEqual(saved.count, 1)
        XCTAssertEqual(saved[0].transcript.map(\.text), ["Let's ship Friday."])
        XCTAssertEqual(saved[0].app, "In person")
    }

    func testSummaryArrivesWithATitleAndIsSaved() throws {
        note.start()
        say("you", 0.5, "Ship Friday.", speaker: 0, voice: "")
        note.stop()
        drainMain(0.8)
        t.event(["event": "summary", "id": note.meetingID,
                 "summary": ["title": "Release plan", "overview": "Ship Friday.", "decisions": ["Friday"],
                             "action_items": [["owner": "You", "task": "Notes", "due": ""]], "open_questions": []]])
        XCTAssertFalse(note.summarizing)
        XCTAssertEqual(note.title, "Release plan")
        XCTAssertEqual(MeetingStore.load(from: t.meetings).first?.summary?.overview, "Ship Friday.")
    }

    func testYourTitleIsKept() {
        note.start()
        note.title = "Board meeting"
        say("you", 0.5, "Hi.", speaker: 0, voice: "")
        note.stop()
        drainMain(0.8)
        t.event(["event": "summary", "id": note.meetingID, "summary": ["title": "Something else", "overview": "O"]])
        XCTAssertEqual(note.title, "Board meeting")
    }

    func testSilentMeetingIsNotSaved() {
        note.start()
        note.stop()
        drainMain(0.8)
        XCTAssertEqual(note.phase, .done)
        XCTAssertTrue(MeetingStore.load(from: t.meetings).isEmpty)
        XCTAssertFalse(t.commands.contains(.summarize))
    }

    func testIncognitoNoteIsNotSaved() {
        t.model.setSetting("incognito", true)
        note.start()
        say("you", 0.5, "Secret.", speaker: 0, voice: "")
        note.stop()
        drainMain(0.8)
        XCTAssertTrue(MeetingStore.load(from: t.meetings).isEmpty)
    }

    func testResumeContinuesTheSameNoteLaterInTime() throws {
        note.start()
        say("you", 0.5, "First.", speaker: 0, voice: "")
        let id = note.meetingID
        note.stop()
        drainMain(0.8)
        note.start(resume: true)
        drainMain()
        XCTAssertEqual(note.meetingID, id)
        recorder.onChunk("you", 1.0, speech())
        drainMain()
        let offset = try XCTUnwrap(t.sent.last { $0.0 == .transcribeChunk }?.1["offset"] as? Double)
        XCTAssertGreaterThan(offset, 1.0)  // after the first stretch
    }

    func testToggleStartsANewNoteAfterOneIsDone() {
        note.start()
        say("you", 0.5, "One.", speaker: 0, voice: "")
        let first = note.meetingID
        note.toggle()  // stop
        drainMain(1.2)
        note.toggle()  // a new note
        XCTAssertNotEqual(note.meetingID, first)
        XCTAssertTrue(note.transcript.lines.isEmpty)
        XCTAssertTrue(note.recording)
    }

    func testStopForQuitStopsTheRecorder() {
        note.start()
        drainMain()
        note.stopForQuit()
        XCTAssertEqual(recorder.stopped, 1)
    }

    // MARK: ask, share, detect

    func testAskAndWhatDidIMiss() {
        note.start()
        say("them", 1, "We ship Friday.")
        note.ask("When do we ship?")
        XCTAssertTrue(note.asking)
        XCTAssertEqual(t.sent.last?.0, .ask)
        XCTAssertEqual((t.sent.last?.1["lines"] as? [[String: String]])?.first?["text"], "We ship Friday.")
        t.event(["event": "answer", "id": note.meetingID, "question": "When do we ship?", "text": "Friday."])
        note.ask("")
        t.event(["event": "answer", "id": note.meetingID, "question": "", "text": "Shipping talk."])
        XCTAssertEqual(note.answers.map(\.question), ["When do we ship?", "What did I miss?"])
        XCTAssertEqual(note.answers.map(\.text), ["Friday.", "Shipping talk."])
        XCTAssertFalse(note.asking)
    }

    func testPlainTextForShare() {
        note.title = "Sync"
        note.start()
        say("you", 0, "Hi.", speaker: 0, voice: "")
        say("them", 1, "Hello.")
        XCTAssertEqual(note.plainText, "Sync\n\nYou:\nHi.\n\nFemale 1:\nHello.\n\n")
    }

    func testDetectionFillsTheSourceAndTitle() {
        note.chosenSource = nil
        note.probe = { SystemSnapshot(windowTitles: [.init("com.google.Chrome", "Meet – Design review - Google Chrome")]) }
        note.detect()
        drainMain(0.4)
        XCTAssertEqual(note.source, .googleMeet)
        XCTAssertEqual(note.title, "Design review")
        XCTAssertNotNil(note.detection.window)
    }

    func testDetectionStopsOnceRecording() {
        note.start()
        note.probe = { SystemSnapshot(processNames: ["CptHost"]) }
        note.detect()
        drainMain(0.4)
        XCTAssertEqual(note.detection.source, .inPerson)  // unchanged while recording
    }

    func testStartAndStopDetectingManageTheTimer() {
        note.probe = { SystemSnapshot() }
        note.startDetecting()
        note.stopDetecting()
        drainMain(0.3)
    }

    func testRefreshPermissionReadsTheCheck() {
        note.permissionCheck = { true }
        note.refreshPermission()
        XCTAssertTrue(note.screenAudioAllowed)
        note.permissionCheck = { false }
        note.refreshPermission()
        XCTAssertFalse(note.screenAudioAllowed)
    }
}
