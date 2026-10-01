import AppKit
import AVFoundation
@testable import MisprCore
import SwiftUI
import XCTest
@testable import MisprFlow

/// The logic that lives behind the views: picking a key, the transcript's timer and search,
/// where the note window docks, the word-cloud layout, day groups, colors, and dev reports.
final class KeyPickTests: XCTestCase {
    typealias Pick = KeyRecorder.Pick

    func testEscCancels() {
        XCTAssertEqual(KeyRecorder.pick(keyDown: true, keyCode: 53, characters: "\u{1b}", flags: []), .cancel)
    }

    func testFunctionKeyIsChosenWithoutWarning() {
        XCTAssertEqual(KeyRecorder.pick(keyDown: true, keyCode: 96, characters: nil, flags: []),
                       .choose(DictationKey(kind: .key, keycode: 96, label: "F5"), warning: nil))
    }

    func testTypingKeyComesWithAWarning() {
        guard case let .choose(key, warning) = KeyRecorder.pick(keyDown: true, keyCode: 0, characters: "a", flags: []) else {
            return XCTFail("expected a choice")
        }
        XCTAssertEqual(key.label, "A")
        XCTAssertEqual(warning, "“A” won't type while Mispr Flow is running.")
    }

    func testHandsFreeKeysAreRefused() {
        guard case .refuse = KeyRecorder.pick(keyDown: true, keyCode: 49, characters: " ", flags: []) else { return XCTFail("space must be refused") }
    }

    func testModifierCountsOnPressNotRelease() {
        XCTAssertEqual(KeyRecorder.pick(keyDown: false, keyCode: 61, characters: nil, flags: .option),
                       .choose(DictationKey(kind: .modifier, keycode: 61, label: "Right ⌥"), warning: nil))
        XCTAssertEqual(KeyRecorder.pick(keyDown: false, keyCode: 61, characters: nil, flags: []), .ignore)
        XCTAssertEqual(KeyRecorder.pick(keyDown: false, keyCode: 57, characters: nil, flags: .capsLock), .ignore)  // caps lock
    }

    func testModifierFlagsBySide() {
        XCTAssertEqual(KeyRecorder.modifierFlag(59), .control)
        XCTAssertEqual(KeyRecorder.modifierFlag(60), .shift)
        XCTAssertEqual(KeyRecorder.modifierFlag(58), .option)
        XCTAssertEqual(KeyRecorder.modifierFlag(54), .command)
        XCTAssertEqual(KeyRecorder.modifierFlag(63), .function)
    }
}

final class TranscriptTextTests: XCTestCase {
    func testElapsed() {
        XCTAssertEqual(TranscriptText.elapsed(7), "0:07")
        XCTAssertEqual(TranscriptText.elapsed(750), "12:30")
        XCTAssertEqual(TranscriptText.elapsed(3723), "1:02:03")
        XCTAssertEqual(TranscriptText.elapsed(-5), "0:00")
    }

    func testMatchCount() {
        let lines = [LiveTranscript.Line(stream: "them", speaker: 1, offset: 0, text: "Free me, I'm free."),
                     LiveTranscript.Line(stream: "you", speaker: 0, offset: 1, text: "FREE")]
        XCTAssertEqual(TranscriptText.matchCount(lines, "free"), 3)
        XCTAssertEqual(TranscriptText.matchCount(lines, "  "), 0)
    }

    func testHighlightMarksEveryMatch() {
        let text = TranscriptText.highlight("free me til I'm Free", "free")
        let marked = text.runs.filter { $0.backgroundColor != nil }.map { String(text[$0.range].characters) }
        XCTAssertEqual(marked, ["free", "Free"])
        XCTAssertTrue(TranscriptText.highlight("nothing", "").runs.allSatisfy { $0.backgroundColor == nil })
    }
}

final class LayoutTests: XCTestCase {
    func testNoteWindowDocksRightFullHeight() {
        let frame = NoteWindowController.dockedFrame(in: NSRect(x: 0, y: 40, width: 1512, height: 900))
        XCTAssertEqual(frame, NSRect(x: 1512 - 470 - 8, y: 48, width: 470, height: 884))
    }

    func testFlowLayoutWraps() {
        let rows = FlowLayout(spacing: 10).arrange(width: 100, sizes: [CGSize(width: 40, height: 10), CGSize(width: 40, height: 20),
                                                                         CGSize(width: 40, height: 15)])
        XCTAssertEqual(rows.map(\.items), [[0, 1], [2]])
        XCTAssertEqual(rows[0].width, 90)
        XCTAssertEqual(rows[0].height, 20)
    }

    func testFlowLayoutPutsAnOversizedItemOnItsOwnLine() {
        let rows = FlowLayout().arrange(width: 50, sizes: [CGSize(width: 80, height: 10), CGSize(width: 10, height: 10)])
        XCTAssertEqual(rows.map(\.items), [[0], [1]])
    }

    func testDayGroupsNewestFirstWithFriendlyTitles() {
        let today = Samples.recording("a"), yesterday = Samples.recording("b", daysAgo: 1), old = Samples.recording("c", daysAgo: 5)
        let groups = DayGroup.group([old, today, yesterday])
        XCTAssertEqual(groups.map(\.title).prefix(2), ["Today", "Yesterday"])
        XCTAssertEqual(groups.map { $0.records.map(\.id) }, [["a"], ["b"], ["c"]])
        XCTAssertFalse(["Today", "Yesterday"].contains(groups[2].title))
    }

    func testSpeakerColors() {
        XCTAssertNotEqual(NSColor(SpeakerColors.color(1)), NSColor(SpeakerColors.color(2)))
        XCTAssertEqual(NSColor(SpeakerColors.color(1)), NSColor(SpeakerColors.color(1 + SpeakerColors.palette.count)))  // wraps
    }
}

final class DevToolsTests: XCTestCase {
    func testDetectReport() {
        let report = DevTools.detectReport(SystemSnapshot(windowTitles: [.init("com.google.Chrome", "Inbox")], micInUse: false),
                                           mic: .authorized, screenAllowed: false)
        XCTAssertEqual(report.split(separator: "\n").map(String.init), [
            "source: In person  title: -  why: No call app is in a meeting",
            "mic in use: false",
            "microphone permission: authorized, screen & system audio: not allowed",
            "window: com.google.Chrome: Inbox",
        ])
    }

    func testMicPermissionNames() {
        XCTAssertEqual([AVAuthorizationStatus.notDetermined, .restricted, .denied, .authorized].map(DevTools.micPermissionName),
                       ["notDetermined", "restricted", "denied", "authorized"])
    }

    func testSegmentReport() {
        var samples = [Float](repeating: 0.0005, count: 48_000)
        for i in 0..<32_000 {
            let gap: Float = (i / 2_400) % 4 == 3 ? 0.03 : 0.3
            samples[i] = Float(sin(Double(i) * 0.2)) * gap
        }
        let report = DevTools.segmentReport(wav: WAV.data(samples))
        XCTAssertTrue(report.hasPrefix("chunk at   0.0s"), report)  // speech, then a pause: one cut at the start
        XCTAssertEqual(DevTools.segmentReport(wav: Data()), "not a WAV with audio")
    }
}
