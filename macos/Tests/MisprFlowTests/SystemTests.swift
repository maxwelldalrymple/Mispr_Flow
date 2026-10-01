import AVFoundation
@testable import MisprCore
import XCTest
@testable import MisprFlow

/// The parts that touch audio and the system, tested without a microphone, plus the app's
/// menus and windows.
final class RecorderPartsTests: XCTestCase {
    func sine(rate: Double, seconds: Double) -> AVAudioPCMBuffer {
        let format = AVAudioFormat(standardFormatWithSampleRate: rate, channels: 2)!
        let frames = AVAudioFrameCount(rate * seconds)
        let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames)!
        buffer.frameLength = frames
        for ch in 0..<2 {
            for i in 0..<Int(frames) { buffer.floatChannelData![ch][i] = Float(sin(2 * .pi * 440 * Double(i) / rate)) * 0.5 }
        }
        return buffer
    }

    func testResamplerMakes16kMonoWithOnlyASmallHoldback() throws {
        // The converter keeps ~70 ms for its filter and releases it with the next buffer, so
        // over a stream nothing is lost except that fixed holdback at the very end.
        let resampler = Resampler(from: sine(rate: 48_000, seconds: 0.1).format)
        var total = 0
        var peak: Float = 0
        for _ in 0..<20 {  // 2 s, as 100 ms capture buffers
            let out = try XCTUnwrap(resampler.convert(sine(rate: 48_000, seconds: 0.1)))
            total += out.count
            peak = max(peak, out.map(abs).max() ?? 0)
        }
        XCTAssertLessThanOrEqual(total, 32_000)
        XCTAssertGreaterThan(total, 32_000 - 1_300)  // at most ~80 ms held back
        XCTAssertEqual(Double(peak), 0.5, accuracy: 0.1)  // mono mix keeps the level
    }

    func testResamplerIgnoresEmptyBuffers() {
        let empty = sine(rate: 44_100, seconds: 0.01)
        empty.frameLength = 0
        XCTAssertNil(Resampler(from: empty.format).convert(empty))
    }

    func testStreamingWAVWritesAPlayableFile() throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID()).wav")
        let wav = try StreamingWAV(url: url)
        wav.append([0, 0.5, -0.5])
        wav.append([1])
        wav.close()
        let file = try AVAudioFile(forReading: url)
        XCTAssertEqual(file.length, 4)
        XCTAssertEqual(file.fileFormat.sampleRate, 16_000)
        XCTAssertEqual(file.fileFormat.channelCount, 1)
    }

    func testRecorderChunksAtPausesAndMeters() {
        let recorder = MeetingRecorder()
        var chunks: [(String, Double, Int)] = []
        var levels: [Float] = []
        recorder.onChunk = { chunks.append(($0, $1, $2.count)) }
        recorder.onLevel = { levels.append($0) }
        var speech = [Float](repeating: 0.0005, count: 16_000 * 3)
        for i in 0..<(16_000 * 2) { speech[i] = Float(sin(Double(i) * 0.2)) * ((i / 2_400) % 4 == 3 ? 0.03 : 0.3) }
        recorder.ingest("them", Array(speech.prefix(16_000)))
        XCTAssertFalse(recorder.inProgress().isEmpty)  // a phrase is being spoken
        recorder.ingest("them", Array(speech.dropFirst(16_000)))
        XCTAssertEqual(chunks.first?.0, "them")
        XCTAssertEqual(chunks.first?.1, 0)
        XCTAssertFalse(levels.isEmpty)
        recorder.ingest("you", Array(speech.prefix(16_000)))
        recorder.stop()  // flushes what "you" was saying
        XCTAssertTrue(chunks.contains { $0.0 == "you" })
    }

    func testCMSampleBufferWithNoAudioGivesNothing() throws {
        var buffer: CMSampleBuffer?
        CMSampleBufferCreate(allocator: nil, dataBuffer: nil, dataReady: true, makeDataReadyCallback: nil, refcon: nil,
                             formatDescription: nil, sampleCount: 0, sampleTimingEntryCount: 0, sampleTimingArray: nil,
                             sampleSizeEntryCount: 0, sampleSizeArray: nil, sampleBufferOut: &buffer)
        XCTAssertNil(try XCTUnwrap(buffer).pcmBuffer)
    }

    func testRecorderErrorReadsWell() {
        XCTAssertEqual(RecorderError("No mic.").errorDescription, "No mic.")
    }
}

final class SystemProbeTests: XCTestCase {
    func testSeesRunningProcessesIncludingItself() {
        let names = SystemProbe.processNames()
        XCTAssertFalse(names.isEmpty)
        XCTAssertTrue(names.contains(ProcessInfo.processInfo.processName) || names.contains { $0.hasPrefix("xctest") || $0.contains("swiftpm") })
    }

    func testMicStatusIsReadable() {
        _ = SystemProbe.micInUse()  // true or false depending on the Mac; must not crash or hang
    }

    func testNoWindowTitlesForAProcessWithoutWindows() {
        XCTAssertEqual(SystemProbe.windowTitles(pid: getpid()), [])
    }

    func testSnapshotListsRunningApps() {
        XCTAssertTrue(SystemProbe.snapshot().runningBundleIDs.contains("com.apple.finder"))
    }

    func testSplitScreenNeedsTheCallsApp() {
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 400, height: 400), styleMask: [.titled], backing: .buffered, defer: true)
        XCTAssertFalse(WindowArranger.split(meeting: .init("com.example.not-running", "Call"), note: window))
    }

    func testNoAccessibilityWindowForAMissingProcess() {
        XCTAssertNil(WindowArranger.axWindow(pid: 999_999, title: ""))
    }
}

final class AppShellTests: XCTestCase {
    func testMainMenu() {
        _ = NSApplication.shared
        let delegate = AppDelegate()
        let menu = delegate.makeMainMenu()
        let app = menu.items[0].submenu!
        XCTAssertEqual(app.items.filter { !$0.isSeparatorItem }.map(\.title),
                       ["About Mispr Flow", "Settings…", "Setup Guide…", "Hide Mispr Flow", "Hide Others", "Show All", "Quit Mispr Flow"])
        XCTAssertEqual(app.item(withTitle: "Settings…")?.keyEquivalent, ",")
        XCTAssertTrue(app.item(withTitle: "Settings…")?.target === delegate)
        XCTAssertEqual(menu.items[1].submenu?.items.map(\.title).contains("Paste"), true)  // ⌘V works in text fields
        XCTAssertEqual(menu.items[2].submenu?.item(withTitle: "Mispr Flow")?.keyEquivalent, "0")
    }

    func testMainWindowIsBuiltButNotShown() {
        let window = AppDelegate().makeMainWindow()
        XCTAssertEqual(window.title, "Mispr Flow")
        XCTAssertEqual(window.minSize, NSSize(width: 900, height: 600))
        XCTAssertFalse(window.isVisible)
        window.contentView?.layoutSubtreeIfNeeded()
        XCTAssertEqual(window.frame.size.height, 760, accuracy: 30)  // content doesn't resize the window
    }

    func testKeepsRunningWithTheWindowClosed() {
        XCTAssertFalse(AppDelegate().applicationShouldTerminateAfterLastWindowClosed(NSApplication.shared))
    }

    func testSettingsAndSetupGuideMenuActions() {
        let delegate = AppDelegate()
        var sent: [EngineCommand] = []
        delegate.model.engine.sendHook = { command, _ in sent.append(command) }
        delegate.openSetupGuide()
        XCTAssertEqual(sent, [.openSetup])
    }

    func testShowSettingsOpensTheWindowOnSettings() {
        let delegate = AppDelegate()
        delegate.showSettings()
        XCTAssertTrue(delegate.model.showSettings)
        NSApp.windows.filter { $0.title == "Mispr Flow" }.forEach { $0.orderOut(nil) }
    }

    func testNoteWindowSlidesInAndOut() {
        let t = TestApp()
        t.model.note.probe = { SystemSnapshot() }
        let controller = NoteWindowController(model: t.model)
        controller.show()
        drainMain(0.5)
        let window = NSApp.windows.first { $0.title == "New note" }
        XCTAssertNotNil(window)
        XCTAssertEqual(window?.frame.width, NoteWindowController.width)
        controller.show()  // already open: just re-docks
        controller.close()
        drainMain(0.5)
        XCTAssertFalse(window?.isVisible ?? true)
        controller.close()  // closing twice is harmless
    }
}
