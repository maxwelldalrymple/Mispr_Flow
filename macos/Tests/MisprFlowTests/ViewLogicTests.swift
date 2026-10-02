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

/// Wording and small rules behind the save, delete and people screens.
final class NotesWordingTests: XCTestCase {
    func testDeleteConfirmationTitles() {
        XCTAssertEqual(NotesView.deleteTitle([Samples.meeting("Standup")]), "Delete “Standup”?")
        XCTAssertEqual(NotesView.deleteTitle([Samples.meeting(), Samples.meeting(), Samples.meeting()]), "Delete 3 notes?")
    }

    func testSaveCardDetail() {
        XCTAssertEqual(SaveNoteCard.detail(lines: 1, seconds: 10), "1 line · 1 min · not saved yet")
        XCTAssertEqual(SaveNoteCard.detail(lines: 14, seconds: 720), "14 lines · 12 min · not saved yet")
    }

    func testSaveQuestionTitles() {
        XCTAssertEqual(SaveQuestionCard.title(recording: true, newNote: false), "Stop and save this note?")
        XCTAssertEqual(SaveQuestionCard.title(recording: false, newNote: false), "Save this note before closing?")
        XCTAssertEqual(SaveQuestionCard.title(recording: false, newNote: true), "Save this note before starting a new one?")
    }

    func testSelectionFollowsARename() {
        XCTAssertEqual(PeopleView.renamed(["Female 1", "Sam"], "Female 1", to: " Priya "), ["Priya", "Sam"])
        XCTAssertEqual(PeopleView.renamed(["Sam"], "Female 1", to: "Priya"), ["Sam"])
        XCTAssertEqual(PeopleView.renamed(["Sam"], "Sam", to: ""), ["Sam"])
    }

    func testPersonSubtitlePrefersTheirCard() {
        let person = PeopleIndex.Person(name: "Priya", role: "Design", meetings: 2, seconds: 60,
                                        firstMet: Date(timeIntervalSince1970: 1_756_900_000), lastMet: Date())
        XCTAssertTrue(PeopleView.subtitle(person, nil).hasPrefix("Design · First met "))
        XCTAssertTrue(PeopleView.subtitle(person, Contact(role: "Lead", company: "Acme")).hasPrefix("Lead · Acme · First met "))
    }

    func testContactEditorKnowsARename() {
        XCTAssertTrue(ContactEditor.isRename("Female 1", " Priya "))
        XCTAssertFalse(ContactEditor.isRename("Priya", "Priya "))
        XCTAssertFalse(ContactEditor.isRename("Priya", "  "))
    }
}

/// Picking the app switcher key: one key, one modifier side, a modifier combo, or modifiers + a key.
final class ComboPickerTests: XCTestCase {
    var picker = ComboPicker()
    let dictation = DictationKey.fn

    func flags(_ code: Int, _ f: NSEvent.ModifierFlags) -> KeyRecorder.Pick {
        picker.feed(keyDown: false, keyCode: code, characters: nil, flags: f, dictation: dictation)
    }

    func key(_ code: Int, _ chars: String, _ f: NSEvent.ModifierFlags = []) -> KeyRecorder.Pick {
        picker.feed(keyDown: true, keyCode: code, characters: chars, flags: f, dictation: dictation)
    }

    func testAModifierComboIsChosenWhenLetGo() {
        XCTAssertEqual(flags(59, .control), .ignore)
        XCTAssertEqual(flags(58, [.control, .option]), .ignore)
        XCTAssertEqual(flags(59, .option), .ignore)  // letting go of one: still deciding
        XCTAssertEqual(flags(58, []), .choose(DictationKey.combo(mods: ["control", "option"])!, warning: nil))
    }

    func testOneModifierSideOnItsOwn() {
        _ = flags(61, .option)
        XCTAssertEqual(flags(61, []), .choose(DictationKey(kind: .modifier, keycode: 61, label: "Right ⌥"), warning: nil))
    }

    func testModifiersPlusAKey() {
        _ = flags(58, .option)
        XCTAssertEqual(key(1, "s", .option), .choose(DictationKey.combo(mods: ["option"], key: DictationKey.key(keycode: 1, characters: "s"))!, warning: nil))
        XCTAssertEqual(flags(58, []), .ignore)  // already chosen; letting go doesn't pick ⌥ too
    }

    func testAPlainKeyWarnsIfItTypes() {
        XCTAssertEqual(key(96, ""), .choose(DictationKey(kind: .key, keycode: 96, label: "F5"), warning: nil))
        if case let .choose(_, warning) = key(1, "s") { XCTAssertNotNil(warning) } else { XCTFail() }
    }

    func testEscCancelsBlockedKeysAndFnAndTheDictationKeyAreRefused() {
        XCTAssertEqual(key(53, ""), .cancel)
        if case .refuse = key(49, " ") {} else { XCTFail("space is for hands-free") }
        if case .refuse = flags(63, .function) {} else { XCTFail("fn can't switch") }
        XCTAssertEqual(flags(63, []), .ignore)
        picker = ComboPicker()
        _ = picker.feed(keyDown: false, keyCode: 61, characters: nil, flags: .option,
                        dictation: DictationKey(kind: .modifier, keycode: 61, label: "Right ⌥"))
        if case .refuse = picker.feed(keyDown: false, keyCode: 61, characters: nil, flags: [],
                                      dictation: DictationKey(kind: .modifier, keycode: 61, label: "Right ⌥")) {} else { XCTFail() }
    }

    func testInstalledAppsAreListedByName() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: dir.appendingPathComponent("Zed.app"), withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: dir.appendingPathComponent("arc.app"), withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: dir.appendingPathComponent("notes.txt"), withIntermediateDirectories: true)
        XCTAssertEqual(NicknameList.installedApps(in: [dir.path, "/nope"]), ["arc", "Zed"])
    }
}

/// The first-run tour: 8 steps across the pages; Next, Back, Skip; once done it stays done.
final class TourTests: XCTestCase {
    func testEightStepsAcrossThePages() {
        XCTAssertEqual(TourStep.all.count, 8)
        XCTAssertEqual(Set(TourStep.all.map(\.page)), Set(Page.allCases))
        XCTAssertEqual(TourStep.all.first?.spot, .fnKey)
        XCTAssertEqual(TourStep.all.last?.spot, .settings)
    }

    func testNextBackAndDone() {
        let t = TestApp()
        t.model.startTour()
        XCTAssertEqual(t.model.tourStep, 0)
        t.model.moveTour(-1)  // Back on the first step stays
        XCTAssertEqual(t.model.tourStep, 0)
        for i in 1..<8 {
            t.model.moveTour(1)
            XCTAssertEqual(t.model.tourStep, i)
            XCTAssertEqual(t.model.page, TourStep.all[i].page)  // each step shows its page
        }
        t.model.moveTour(1)  // Done
        XCTAssertNil(t.model.tourStep)
        XCTAssertTrue(t.model.profile.tutorialDone)
        XCTAssertEqual(t.model.page, .home)
    }

    func testSkipEndsItForGood() {
        let t = TestApp()
        t.model.setSetting("onboarded", true)
        t.model.startTourIfNew()
        XCTAssertEqual(t.model.tourStep, 0)
        t.model.moveTour(1)
        t.model.endTour()  // Skip tour
        XCTAssertNil(t.model.tourStep)
        t.model.startTourIfNew()
        XCTAssertNil(t.model.tourStep)  // not again by itself
        t.model.startTour()  // Help → Show Tutorial
        XCTAssertEqual(t.model.tourStep, 0)
    }

    func testFinishingSetupOpensTheWindowAndStartsTheTour() {
        let t = TestApp()
        var shown = 0
        t.model.showMain = { shown += 1 }
        t.model.setSetting("onboarded", true)  // the engine saves this before telling the app
        t.event(["event": "setup_finished"])
        XCTAssertEqual(shown, 1)
        XCTAssertEqual(t.model.tourStep, 0)
        t.model.endTour()
        t.event(["event": "setup_finished"])  // setup reopened later from the menu: no tour again
        XCTAssertNil(t.model.tourStep)
        XCTAssertEqual(shown, 2)
    }

    func testOnlyStartsByItselfAfterSetup() {
        let t = TestApp()
        t.model.startTourIfNew()
        XCTAssertNil(t.model.tourStep)  // setup not finished yet
    }

    func testStartingClosesSettings() {
        let t = TestApp()
        t.model.showSettings = true
        t.model.startTour()
        XCTAssertFalse(t.model.showSettings)
    }

    func testCardPlacement() {
        let size = CGSize(width: 1000, height: 700), card = CGSize(width: 320, height: 170)
        XCTAssertEqual(TourOverlay.cardOrigin(near: nil, in: size, card: card), CGSize(width: 340, height: 265))  // centred
        XCTAssertEqual(TourOverlay.cardOrigin(near: CGRect(x: 100, y: 50, width: 200, height: 40), in: size, card: card),
                       CGSize(width: 40, height: 104))  // below, kept 16 pt inside
        XCTAssertEqual(TourOverlay.cardOrigin(near: CGRect(x: 600, y: 600, width: 100, height: 60), in: size, card: card).height,
                       600 - 14 - 170)  // above when there's no room below
        let tall = TourOverlay.cardOrigin(near: CGRect(x: 10, y: 10, width: 200, height: 680), in: size, card: card)
        XCTAssertEqual(tall.width, 224)  // beside a spot that fills the height
    }
}
