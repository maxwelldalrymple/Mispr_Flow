import AVFoundation
@testable import MisprCore
import XCTest
@testable import MisprFlow

/// The last functions coverage found untested: app lifecycle, playback, the permission
/// request, prompt saving, person navigation, small text helpers, and the recorder's
/// system-audio callbacks.
final class AppLifecycleTests: XCTestCase {
    override func tearDown() {
        NSApp.windows.filter { ["Mispr Flow", "New note"].contains($0.title) }.forEach { $0.orderOut(nil) }
    }

    func testLaunchSetsUpTheMenuStartsTheEngineAndShowsTheWindow() {
        let delegate = AppDelegate()
        delegate.applicationDidFinishLaunching(Notification(name: NSApplication.didFinishLaunchingNotification))
        XCTAssertEqual(NSApp.mainMenu?.items.first?.submenu?.title, "Mispr Flow")
        XCTAssertNotEqual(delegate.model.engine.state, .stopped)  // tried to start (no engine in tests: failed)
        XCTAssertTrue(NSApp.windows.contains { $0.title == "Mispr Flow" && $0.isVisible })
        delegate.model.openNote()  // wired to the note window
        drainMain(0.5)
        XCTAssertTrue(NSApp.windows.contains { $0.title == "New note" })
        delegate.applicationWillTerminate(Notification(name: NSApplication.willTerminateNotification))
        XCTAssertEqual(delegate.model.engine.state, .failed("Can't find the Mispr Flow engine (no MisprProjectRoot)."))
    }

    func testClickingTheDockIconShowsTheWindow() {
        let delegate = AppDelegate()
        XCTAssertTrue(delegate.applicationShouldHandleReopen(NSApplication.shared, hasVisibleWindows: false))
        XCTAssertTrue(NSApp.windows.contains { $0.title == "Mispr Flow" && $0.isVisible })
    }

    func testModelStartOpensTheRequestedPage() {
        let t = TestApp()
        t.model.start()  // no config: the engine fails fast; the page stays Home without MISPR_PAGE
        XCTAssertEqual(t.model.page, .home)
    }
}

final class PlayerTests: XCTestCase {
    func silentRecording() throws -> Recording {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("player-\(UUID())")
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        try WAV.data([Float](repeating: 0, count: 16_000)).write(to: dir.appendingPathComponent("r.wav"))  // 1 s of silence
        var r = Samples.recording("r")
        r.audioFile = "r.wav"
        r.fileURL = dir.appendingPathComponent("r.json")
        return r
    }

    func testPlayToggleAndStop() throws {
        let player = Player()
        let r = try silentRecording()
        player.toggle(r)
        XCTAssertEqual(player.playing, "r")
        player.toggle(r)  // again: stop
        XCTAssertNil(player.playing)
        player.toggle(r)
        player.stop()
        XCTAssertNil(player.playing)
    }

    func testFinishingClearsThePlayingRow() throws {
        let player = Player()
        player.toggle(try silentRecording())
        player.audioPlayerDidFinishPlaying(try AVAudioPlayer(data: WAV.data([0, 0])), successfully: true)
        drainMain()
        XCTAssertNil(player.playing)
    }

    func testMissingAudioDoesNothing() {
        let player = Player()
        player.toggle(Samples.recording("no-file"))
        XCTAssertNil(player.playing)
    }
}

final class SmallHelperTests: XCTestCase {
    func testSnippet() {
        XCTAssertEqual(MoreInsightsView.snippet("Short."), "Short.")
        let long = String(repeating: "word ", count: 20)
        XCTAssertEqual(MoreInsightsView.snippet(long).count, 58)
        XCTAssertTrue(MoreInsightsView.snippet(long).hasSuffix("…"))
    }

    func testSpeedupVersusTyping() {
        var s = Stats()
        s.wordsPerMinute = 120
        XCTAssertEqual(s.speedup, 3)
    }

    func testPersonPage() {
        let page = NotesView.personPage("Priya Shah")
        XCTAssertEqual(page.tab, 1)
        XCTAssertNil(page.open)
        XCTAssertEqual(page.selected, ["Priya Shah"])
    }

    func testSavingPromptsWritesAndReloads() throws {
        let t = TestApp()
        let draft = PromptDraft(system: "Be brief.", examples: "Said: um a\nWrote: A.")
        let result = PromptsView.save(draft, to: t.prompts, engine: t.engine)
        XCTAssertTrue(result.ok)
        XCTAssertEqual(result.message, "Saved · used from your next dictation")
        XCTAssertEqual(PromptDraft.load(from: t.prompts, defaults: DefaultPrompts(system: "x", examples: "")).system, "Be brief.")
        XCTAssertEqual(t.commands, [.reloadSettings])
    }

    func testSavingPromptsSomewhereUnwritableSaysSo() {
        let t = TestApp()
        let result = PromptsView.save(PromptDraft(system: "S", examples: ""), to: URL(fileURLWithPath: "/proc/nope/p.json"), engine: t.engine)
        XCTAssertFalse(result.ok)
        XCTAssertTrue(result.message.hasPrefix("Couldn't save"))
        XCTAssertTrue(t.commands.isEmpty)
    }
}

final class PermissionRequestTests: XCTestCase {
    func testAskingOpensSettingsWhenMacOSSaysNoThenWatchesForTheSwitch() {
        let note = NoteModel()
        var allowed = false
        var openedSettings = 0
        note.permissionRequest = { false }
        note.openSettingsPane = { openedSettings += 1 }
        note.permissionCheck = { allowed }
        note.refreshPermission()  // a new note starts from the Mac's real state; use the fake
        note.requestPermission(every: 0.05)
        XCTAssertEqual(openedSettings, 1)
        XCTAssertFalse(note.screenAudioAllowed)
        allowed = true  // the user flips the switch
        drainMain(0.3)
        XCTAssertTrue(note.screenAudioAllowed)
    }

    func testNoSettingsPaneWhenMacOSAlreadyAllows() {
        let note = NoteModel()
        var openedSettings = 0
        note.permissionRequest = { true }
        note.openSettingsPane = { openedSettings += 1 }
        note.permissionCheck = { true }
        note.requestPermission(every: 0.05)
        drainMain(0.15)
        XCTAssertEqual(openedSettings, 0)
        XCTAssertTrue(note.screenAudioAllowed)
    }
}

final class RecorderCallbackTests: XCTestCase {
    /// A ScreenCaptureKit-style audio sample buffer (48 kHz mono float) holding a tone.
    func audioSampleBuffer(seconds: Double) throws -> CMSampleBuffer {
        let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 48_000, channels: 1, interleaved: false)!
        let frames = AVAudioFrameCount(48_000 * seconds)
        let pcm = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames)!
        pcm.frameLength = frames
        for i in 0..<Int(frames) { pcm.floatChannelData![0][i] = Float(sin(Double(i) * 0.06)) * 0.3 }
        var description: CMAudioFormatDescription?
        CMAudioFormatDescriptionCreate(allocator: nil, asbd: format.streamDescription, layoutSize: 0, layout: nil,
                                       magicCookieSize: 0, magicCookie: nil, extensions: nil, formatDescriptionOut: &description)
        var timing = CMSampleTimingInfo(duration: CMTime(value: 1, timescale: 48_000), presentationTimeStamp: .zero, decodeTimeStamp: .invalid)
        var buffer: CMSampleBuffer?
        CMSampleBufferCreate(allocator: nil, dataBuffer: nil, dataReady: false, makeDataReadyCallback: nil, refcon: nil,
                             formatDescription: description, sampleCount: CMItemCount(frames), sampleTimingEntryCount: 1,
                             sampleTimingArray: &timing, sampleSizeEntryCount: 0, sampleSizeArray: nil, sampleBufferOut: &buffer)
        let sample = try XCTUnwrap(buffer)
        XCTAssertEqual(CMSampleBufferSetDataBufferFromAudioBufferList(sample, blockBufferAllocator: nil, blockBufferMemoryAllocator: nil,
                                                                      flags: 0, bufferList: pcm.audioBufferList), noErr)
        return sample
    }

    func testSystemAudioArrivesAsThemAndIsMetered() throws {
        let recorder = MeetingRecorder()
        var levels: [Float] = []
        recorder.onLevel = { levels.append($0) }
        let sample = try audioSampleBuffer(seconds: 1.0)  // over the 0.5 s a phrase needs, after resampling
        XCTAssertNotNil(sample.pcmBuffer)
        let stream = SCStreamStandIn.make()
        recorder.stream(stream, didOutputSampleBuffer: sample, of: .audio)
        recorder.stream(stream, didOutputSampleBuffer: sample, of: .screen)  // video frames are ignored
        XCTAssertFalse(levels.isEmpty)
        XCTAssertFalse(recorder.inProgress().filter { $0.stream == "them" }.isEmpty)
    }

    func testStreamStoppingReportsAnError() {
        let recorder = MeetingRecorder()
        var errors: [String] = []
        recorder.onError = { errors.append($0) }
        recorder.stream(SCStreamStandIn.make(), didStopWithError: RecorderError("display went away"))
        XCTAssertEqual(errors, ["System audio stopped: display went away"])
    }
}

import ScreenCaptureKit

/// An SCStream to pass to the delegate callbacks (never started).
enum SCStreamStandIn {
    static func make() -> SCStream {
        SCStream(filter: SCContentFilter(), configuration: SCStreamConfiguration(), delegate: nil)
    }
}
