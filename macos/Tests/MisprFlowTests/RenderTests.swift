@testable import MisprCore
import SwiftUI
import XCTest
@testable import MisprFlow

/// Every page and state is laid out and drawn offscreen, with data, so each view's `body`
/// (and everything it calls) runs; a crash or a blank render fails the test.
final class RenderTests: XCTestCase {
    var t: TestApp!

    override func setUp() {
        t = TestApp()
        Samples.write([Samples.recording("a"), Samples.recording("b", daysAgo: 1, text: "Hello, how are you today?"),
                       Samples.recording("c", status: .copied), Samples.recording("d", status: .cancelled)], to: t.recordings)
        try? Samples.meeting().save(in: t.meetings)
        try? Samples.meeting("Design review", people: ["Priya Shah", "Lena Novak"], daysAgo: 3).save(in: t.meetings)
        t.model.reloadRecordings()
        drainMain(0.5)
        XCTAssertFalse(t.model.recordings.isEmpty)
    }

    func check<V: View>(_ view: V, _ file: StaticString = #filePath, _ line: UInt = #line) {
        XCTAssertTrue(hasContent(render(view, model: t.model)), "rendered blank", file: file, line: line)
    }

    // MARK: main window

    func testEveryPageInTheMainWindow() {
        for page in Page.allCases {
            t.model.page = page
            check(RootView())
        }
    }

    func testHomeVoiceCommandsCardWithAndWithoutASwitchKey() {
        t.model.page = .home
        check(RootView())  // no switch key: "Set it up in Settings"
        t.model.setSwitchKey(DictationKey.combo(mods: ["control", "option"]))
        check(RootView())  // "Hold ⌃⌥, say it, let go."
        XCTAssertEqual(HomeView.commandGroups.map(\.title), ["Apps & windows", "Tabs & pages", "Sound"])
    }

    func testHomeEmpty() {
        let empty = TestApp()
        drainMain()
        check(HomeView())
        _ = empty
    }

    func testInsightsBothTabs() {
        check(InsightsView(initialTab: 0))
        check(InsightsView(initialTab: 1))
    }

    func testInsightsPiecesOnTheirOwn() {
        check(MoreInsightsView(more: t.model.more, totalWords: t.model.stats.totalWords))
        check(VoiceView(profile: t.model.voice))
        check(VoiceView(profile: VoiceProfile()))  // empty state
        check(StreakView(stats: t.model.stats))
        check(SpeedGauge(wpm: 135).frame(width: 200, height: 100))
        check(Bars(values: [0, 3, 1, 7], labels: [0: "a"], color: .green).frame(width: 200, height: 100))
    }

    func testNotetakerTabsAndDetail() {
        check(NotesView(initialTab: 0))
        check(NotesView(initialTab: 1))
        check(NotesView(initialTab: 1, people: ["Priya Shah"]))
        check(NotesView(initialTab: 1, people: ["Priya Shah", "Jordan Lee"]))
        check(NotesView(initialTab: 2))
        let meeting = t.model.meetings[0]
        for tab in ["Summary", "Transcript", "Insights", "My thoughts"] {
            check(MeetingDetailView(meeting: meeting, back: {}, initialTab: tab))
        }
        check(MeetingDetailView(meeting: meeting, back: {}, delete: {}))  // with its Delete button
    }

    func testNoteRowsInSelectModeAndWithDelete() {
        let meeting = t.model.meetings[0]
        check(NoteRow(meeting: meeting, delete: {}).frame(width: 700))
        check(NoteRow(meeting: meeting, selecting: true, picked: false).frame(width: 700))
        check(NoteRow(meeting: meeting, selecting: true, picked: true).frame(width: 700))
    }

    func testPeopleWithContactDetailsAndTheEditor() {
        t.model.saveContact(Contact(role: "Lead", company: "Acme", email: "p@acme.com", phone: "555 0100", notes: "Loves charts."),
                            for: "Priya Shah")
        check(NotesView(initialTab: 1, people: ["Priya Shah"]))
        check(ContactEditor(name: "Priya Shah", card: Contact(), meetings: 2, save: { _, _ in }, cancel: {}))
        check(ContactEditor(name: "Priya Shah", card: t.model.contacts["Priya Shah"]!, meetings: 1, save: { _, _ in }, cancel: {}))
    }

    func testNotetakerWithNoMeetings() {
        let empty = TestApp()
        drainMain()
        XCTAssertTrue(hasContent(render(NotesView(initialTab: 0), model: empty.model)))
        XCTAssertTrue(hasContent(render(NotesView(initialTab: 2), model: empty.model)))
    }

    func testPromptsPageWithAndWithoutTheEngine() {
        check(PromptsView())
        let waiting = TestApp(hello: false)
        XCTAssertTrue(hasContent(render(PromptsView(), model: waiting.model)))
    }

    func testSettingsEverySection() {
        t.model.showSettings = true
        for section in SettingsModal.Section.allCases {
            t.model.settingsSection = section
            check(RootView())
        }
    }

    func testSettingsWithTheAppSwitcherAndNicknames() {
        t.model.setSwitchKey(DictationKey.combo(mods: ["control", "option"]))
        t.model.setNickname("c", app: "Google Chrome")
        t.model.showSettings = true
        t.model.settingsSection = .general
        check(RootView())
        check(NicknameList().frame(width: 500))
        check(KeyRecorder(slot: .appSwitch).padding())
    }

    func testIncognitoLook() {
        t.model.setSetting("incognito", true)
        check(RootView())
    }

    func testEngineBanners() {
        let failed = TestApp(hello: false)
        failed.engine.start()  // no config: fails with a message
        XCTAssertTrue(hasContent(render(RootView(), model: failed.model)))
    }

    func testEveryTheme() {
        for palette in Palette.all {
            t.model.profile.themeID = palette.id
            check(ThemedRoot { RootView() })
        }
        t.model.profile.themeID = "classic"
    }

    func testSmallPieces() {
        check(Logo(size: 40).padding())
        check(AvatarView(size: 40).padding())
        check(Initials(name: "Priya Shah").padding())
        check(PeopleStack(names: ["A B", "C D", "E F", "G H", "I J"]).padding())
        check(Badge(text: "Sample").padding())
        check(ThemeCard(palette: .ocean, selected: true, choose: {}).frame(width: 200))
        check(PlaceholderView(title: "T", symbol: "star", message: "M", detail: "D"))
        check(SettingsIllustration().frame(width: 400))
        check(SetupCard(back: {}, turnOn: {}).frame(width: 440))
        check(KeyRecorder().padding())
        check(IncognitoSwitch().padding())
        check(AutoEnterButton().scaleEffect(4).frame(width: 160, height: 120))  // off: just the ⏎ icon (enlarged: the blank check samples a sparse grid)
        t.model.setSetting("auto_enter", true)
        check(AutoEnterButton().padding())  // on: highlighted with its label
        check(InfoCard(title: "T", lines: ["One.", "Two."]).padding(.bottom, 80))
        // A native pop-up menu button: AppKit doesn't paint it into an offscreen snapshot, so
        // this only checks it builds and lays out; its choices are tested below.
        render(SourceChip().padding(), model: t.model)
    }

    func testSourceChipChoicesChangeTheMeetingType() {
        let note = t.model.note
        note.chosenSource = .teams
        XCTAssertEqual(note.source, .teams)
        note.chosenSource = nil  // "Detect automatically"
        XCTAssertEqual(note.source, note.detection.source)
        XCTAssertEqual(MeetingSource.allCases.count, 9)  // every choice the menu lists
    }

    // MARK: note window

    func testNoteWindowInEveryPhase() {
        let note = t.model.note
        let recorder = FakeRecorder()
        note.makeRecorder = { recorder }
        note.permissionCheck = { true }
        note.chosenSource = .inPerson
        check(NoteView(close: {}))  // ready: welcome text

        note.start()
        drainMain()
        check(NoteView(close: {}))  // recording, nothing heard yet
        t.event(["event": "chunk_text", "id": note.meetingID, "stream": "them", "speaker": 1, "offset": 1.0,
                 "text": "Free me now.", "voice": "female"])
        t.event(["event": "chunk_text", "id": note.meetingID, "stream": "you", "speaker": 0, "offset": 3.0,
                 "text": "Live words", "voice": "", "partial": true])
        note.search = "free"
        check(NoteView(close: {}))  // bubbles, a live line, highlighted search

        for tab in NoteModel.Tab.allCases {
            note.tab = tab
            check(NoteView(close: {}))
        }
        note.ask("What happened?")
        t.event(["event": "answer", "id": note.meetingID, "question": "What happened?", "text": "Free was said."])
        note.tab = .transcript
        check(NoteView(close: {}))  // answers panel

        note.stop()
        check(NoteView(close: {}))  // finishing
        drainMain(0.8)
        check(NoteView(close: {}))  // done: the Save note card
        XCTAssertFalse(note.requestClose())
        check(NoteView(close: {}))  // the "Save this note before closing?" card
        check(SaveQuestionCard().frame(width: 400))
        check(SaveNoteCard().frame(width: 440))
        note.decide(.save)
        check(SavedChip().padding())
        t.event(["event": "summary", "id": note.meetingID,
                 "summary": ["overview": "Talked.", "decisions": ["A"], "action_items": [["owner": "You", "task": "B", "due": "Fri"]],
                             "open_questions": ["C?"]]])
        note.tab = .summary
        check(NoteView(close: {}))  // done with a summary
    }

    func testNoteWindowPermissionCardAndWarning() {
        let note = t.model.note
        note.permissionCheck = { false }
        note.chosenSource = .zoom
        note.refreshPermission()
        check(NoteView(close: {}))  // the setup card over the note
        let recorder = FakeRecorder()
        recorder.warning = "Screen & System Audio isn't allowed"
        note.makeRecorder = { recorder }
        note.chosenSource = .inPerson
        note.start()
        drainMain()
        check(NoteView(close: {}))  // the orange banner with Turn on
    }
}
