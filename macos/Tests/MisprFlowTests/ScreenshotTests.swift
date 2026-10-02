@testable import MisprCore
import SwiftUI
import XCTest
@testable import MisprFlow

/// Screenshots of every window and state, with made-up sample data, for docs/screenshots/.
/// Skipped unless MISPR_SCREENSHOTS names the folder to write to (tools/screenshots.sh sets it).
///
/// Named <window>_<page>_<state>_<theme>-<light|dark>.png in a folder per window. Every state
/// is shot in light and dark with the Classic theme; themes/ has all six themes in both.
final class ScreenshotTests: XCTestCase {
    var t: TestApp!
    var out: URL!
    var theme = "classic"
    var dark = false
    static let mainSize = CGSize(width: 1180, height: 760)
    static let noteSize = CGSize(width: NoteWindowController.width, height: 700)

    override func setUpWithError() throws {
        guard let dir = ProcessInfo.processInfo.environment["MISPR_SCREENSHOTS"] else {
            throw XCTSkip("set MISPR_SCREENSHOTS to a folder to write screenshots")
        }
        out = URL(fileURLWithPath: dir)
        freshApp()
    }

    /// A new sample app: Alex's made-up dictations, meetings, a contact, a switch key and a nickname.
    func freshApp() {
        t = TestApp()
        t.model.profile.name = "Alex Rivera"
        t.model.profile.nickname = "Alex"
        Samples.write([
            Samples.recording("a", text: "Ship the release on Friday and send the notes to the team."),
            Samples.recording("b", daysAgo: 0.1, text: "Can you review the pull request before lunch?", app: "Google Chrome", bundle: "com.google.Chrome"),
            Samples.recording("c", daysAgo: 0.2, text: "git commit -m \"fix the login bug\"", app: "Terminal", bundle: "com.apple.Terminal"),
            Samples.recording("d", daysAgo: 1, text: "Thanks for the update, I'll take a look tomorrow morning.", status: .copied),
            Samples.recording("e", daysAgo: 1.2, text: "Let's move the design review to Thursday at three.", app: "Mail", bundle: "com.apple.mail"),
            Samples.recording("f", daysAgo: 2, text: "Chrome beside VS Code", status: .command, app: "Google Chrome", bundle: "com.google.Chrome"),
            Samples.recording("g", daysAgo: 2.1, text: "new tab", status: .command, app: "Google Chrome", bundle: "com.google.Chrome"),
        ], to: t.recordings)
        try? Samples.meeting().save(in: t.meetings)
        try? Samples.meeting("Design review", people: ["Priya Shah", "Lena Novak"], daysAgo: 3).save(in: t.meetings)
        try? Samples.meeting("Roadmap planning", people: ["Jordan Lee", "Sam Okafor"], daysAgo: 5).save(in: t.meetings)
        t.model.saveContact(Contact(role: "Design lead", company: "Acme", email: "priya@example.com", phone: "555 0100",
                                    notes: "Prefers async updates."), for: "Priya Shah")
        t.model.setSwitchKey(DictationKey.combo(mods: ["control", "option"]))
        t.model.setNickname("scooby snacks", app: "Google Chrome")
        t.model.reloadRecordings()
        drainMain(0.5)
    }

    /// Shoot `view` into `<folder>/<name>_<theme>-<light|dark>.png`.
    func shot<V: View>(_ folder: String, _ name: String, _ view: V, size: CGSize = mainSize) throws {
        Palette.current = Palette.all.first { $0.id == theme }!
        t.model.profile.themeID = theme
        // The window background: pages shot on their own (not inside RootView) are otherwise see-through.
        let rep = render(view.background(Theme.content), model: t.model, size: size, appearance: NSAppearance(named: dark ? .darkAqua : .aqua))
        XCTAssertTrue(hasContent(rep), "\(name) rendered blank")
        let dir = out.appendingPathComponent(folder)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let file = "\(name)_\(theme)-\(dark ? "dark" : "light").png"
        try rep.representation(using: .png, properties: [:])!.write(to: dir.appendingPathComponent(file))
    }

    /// Run `body` once in light and once in dark.
    func bothModes(_ body: () throws -> Void) rethrows {
        for mode in [false, true] { dark = mode; try body() }
        dark = false
    }

    static func slug(_ text: String) -> String {
        text.lowercased().map { $0.isLetter || $0.isNumber ? String($0) : "-" }.joined()
            .split(separator: "-").joined(separator: "-")
    }

    func testMainWindow() throws {
        try bothModes {
            let names: [Page: String] = [.home: "home_dictation-history", .notetaker: "notetaker_notes-list",
                                         .insights: "insights_overview", .prompts: "prompts_cleanup-prompt"]
            for page in Page.allCases {
                t.model.page = page
                try shot("main-window", names[page]!, RootView())
            }
            try shot("main-window", "home_commands-history", HomeView(showCommands: true))
            try shot("main-window", "insights_more-insights", InsightsView(initialTab: 1))
            try shot("main-window", "notetaker_people-list", NotesView(initialTab: 1))
            try shot("main-window", "notetaker_person-selected-with-contact-card", NotesView(initialTab: 1, people: ["Priya Shah"]))
            try shot("main-window", "notetaker_two-people-shared-meetings", NotesView(initialTab: 1, people: ["Priya Shah", "Jordan Lee"]))
            try shot("main-window", "notetaker_third-tab", NotesView(initialTab: 2))
            let meeting = t.model.meetings[0]
            for tab in ["Summary", "Transcript", "Insights", "My thoughts"] {
                try shot("main-window", "notetaker_meeting-detail_\(Self.slug(tab))-tab",
                         MeetingDetailView(meeting: meeting, back: {}, delete: {}, initialTab: tab))
            }
            try shot("main-window", "notetaker_contact-editor",
                     ContactEditor(name: "Priya Shah", card: t.model.contacts["Priya Shah"]!, meetings: 2, save: { _, _ in }, cancel: {}),
                     size: CGSize(width: 520, height: 560))
            t.model.page = .home
            t.model.setSetting("incognito", true)
            try shot("main-window", "home_incognito-on", RootView())
            t.model.setSetting("incognito", false)
            t.model.setSetting("auto_enter", true)
            try shot("main-window", "home_auto-enter-on", RootView())
            t.model.setSetting("incognito", true)
            try shot("main-window", "home_incognito-and-auto-enter-on", RootView())
            t.model.setSetting("incognito", false)
            t.model.setSetting("auto_enter", false)
        }
    }

    func testSettings() throws {
        try bothModes {
            t.model.page = .home
            t.model.showSettings = true
            for section in SettingsModal.Section.allCases {
                t.model.settingsSection = section
                try shot("settings", "settings_\(Self.slug(section.rawValue))-section", RootView())
            }
            t.model.showSettings = false
        }
    }

    func testTutorial() throws {
        try bothModes {
            for (i, step) in TourStep.all.enumerated() {
                t.model.startTour()
                for _ in 0..<i { t.model.moveTour(1) }
                try shot("tutorial", "tutorial_step-\(i + 1)-of-\(TourStep.all.count)_\(Self.slug(step.title))", RootView())
            }
            t.model.endTour()
        }
    }

    /// Every theme in light and dark, on the three main pages.
    func testThemes() throws {
        for palette in Palette.all {
            theme = palette.id
            try bothModes {
                for (page, name) in [(Page.home, "home"), (.notetaker, "notetaker"), (.insights, "insights")] {
                    t.model.page = page
                    try shot("themes", "main-window_\(name)", ThemedRoot { RootView() })
                }
            }
        }
        theme = "classic"
    }

    func testNoteWindow() throws {
        try bothModes { try noteWindowStates() }
    }

    private func noteWindowStates() throws {
        freshApp()  // a note can only be recorded once
        let note = t.model.note
        let recorder = FakeRecorder()
        note.makeRecorder = { recorder }
        note.permissionCheck = { true }
        note.chosenSource = .zoom
        try shot("note-window", "note_1-ready-to-record", NoteView(close: {}), size: Self.noteSize)
        note.start()
        drainMain()
        let lines: [(Int, String, String, String, Double)] = [
            (1, "them", "female", "Morning everyone, let's start with the release.", 1),
            (0, "you", "", "Sounds good. The installer is ready for testing.", 5),
            (2, "them", "male", "Great. I'll write the release notes today.", 9),
            (1, "them", "female", "Can we ship on Friday?", 14),
        ]
        for (speaker, stream, voice, text, offset) in lines {
            t.event(["event": "chunk_text", "id": note.meetingID, "stream": stream, "speaker": speaker, "offset": offset,
                     "text": text, "voice": voice])
        }
        t.event(["event": "chunk_text", "id": note.meetingID, "stream": "you", "speaker": 0, "offset": 18.0,
                 "text": "Friday works if", "voice": "", "partial": true])
        try shot("note-window", "note_2-recording-live-transcript", NoteView(close: {}), size: Self.noteSize)
        for tab in NoteModel.Tab.allCases {
            note.tab = tab
            try shot("note-window", "note_3-recording_\(Self.slug(String(describing: tab)))-tab", NoteView(close: {}), size: Self.noteSize)
        }
        note.ask("When do we ship?")
        t.event(["event": "answer", "id": note.meetingID, "question": "When do we ship?", "text": "Friday, once the installer is tested."])
        note.tab = .transcript
        try shot("note-window", "note_4-recording-question-answered", NoteView(close: {}), size: Self.noteSize)
        note.stop()
        drainMain(0.8)
        try shot("note-window", "note_5-stopped-save-card", NoteView(close: {}), size: Self.noteSize)
        _ = note.requestClose()
        try shot("note-window", "note_6-closing-save-question", NoteView(close: {}), size: Self.noteSize)
        note.decide(.save)
        t.event(["event": "summary", "id": note.meetingID,
                 "summary": ["overview": "The team agreed to ship on Friday once the installer is tested.",
                             "decisions": ["Ship on Friday"],
                             "action_items": [["owner": "Female 1", "task": "Write the release notes", "due": "Today"]],
                             "open_questions": ["Who tests on an Intel Mac?"]]])
        note.tab = .summary
        try shot("note-window", "note_7-saved-with-summary", NoteView(close: {}), size: Self.noteSize)
    }

    func testNoteWindowNeedsPermission() throws {
        try bothModes {
            let note = t.model.note
            note.permissionCheck = { false }
            note.chosenSource = .zoom
            note.refreshPermission()
            try shot("note-window", "note_0-needs-screen-audio-permission", NoteView(close: {}), size: Self.noteSize)
        }
    }
}
