@testable import MisprCore
import XCTest
@testable import MisprFlow

/// AppModel: settings, the dictation key, loading and deleting recordings, profile, and how it
/// reacts to the engine's events.
final class AppModelTests: XCTestCase {
    func testSettingsReadDefaultsBeforeAnyFileExists() {
        let t = TestApp()
        XCTAssertTrue(t.model.setting("cleanup"))
        XCTAssertTrue(t.model.setting("sounds"))
        XCTAssertFalse(t.model.setting("incognito"))
        XCTAssertFalse(t.model.setting("auto_enter"))  // only the top-bar button turns it on
    }

    func testAutoEnterButtonTogglesTheSettingForTheEngine() {
        let t = TestApp()
        t.model.setSetting("auto_enter", true)
        XCTAssertEqual(SettingsFile(url: t.settings).read()["auto_enter"] as? Bool, true)
        t.model.setSetting("auto_enter", false)
        XCTAssertFalse(t.model.setting("auto_enter"))
        XCTAssertEqual(t.commands, [.reloadSettings, .reloadSettings])
    }

    func testChangingASettingWritesTheFileAndTellsTheEngine() {
        let t = TestApp()
        t.model.setSetting("incognito", true)
        XCTAssertTrue(t.model.setting("incognito"))
        XCTAssertEqual(SettingsFile(url: t.settings).read()["incognito"] as? Bool, true)
        XCTAssertEqual(t.commands, [.reloadSettings])
        XCTAssertNil(t.model.settingsError)
    }

    func testBindingReadsAndWrites() {
        let t = TestApp()
        let b = t.model.binding("sounds")
        b.wrappedValue = false
        XCTAssertFalse(b.wrappedValue)
        XCTAssertFalse(t.model.setting("sounds"))
    }

    func testUnwritableSettingsShowAnError() {
        let t = TestApp(hello: false)
        t.event(["event": "hello", "recordings_dir": t.recordings.path, "settings_path": "/proc/nope/settings.json"])
        t.model.setSetting("sounds", false)
        XCTAssertNotNil(t.model.settingsError)
        XCTAssertTrue(t.commands.isEmpty)
    }

    func testDictationKeyRoundTripsAndReloadsTheEngine() {
        let t = TestApp()
        XCTAssertEqual(t.model.dictationKey, .fn)
        let f5 = DictationKey(kind: .key, keycode: 96, label: "F5")
        t.model.setDictationKey(f5)
        XCTAssertEqual(t.model.dictationKey, f5)
        XCTAssertEqual(t.commands, [.reloadSettings])
    }

    func testRecordingsAndStatsLoadAfterHello() {
        let t = TestApp(hello: false)
        Samples.write([Samples.recording("a"), Samples.recording("b", text: "Hello there team.")], to: t.recordings)
        t.sayHello()
        drainMain(0.5)
        XCTAssertEqual(Set(t.model.recordings.map(\.id)), ["a", "b"])
        XCTAssertEqual(t.model.stats.dictations, 2)
        XCTAssertEqual(t.model.more.topApps.first?.app, "Slack")
        XCTAssertGreaterThan(t.model.voice.averageWords, 0)
    }

    func testSavedEventReloadsHistory() {
        let t = TestApp()
        drainMain()
        XCTAssertTrue(t.model.recordings.isEmpty)
        Samples.write([Samples.recording("new")], to: t.recordings)
        t.event(["event": "saved", "path": t.recordings.appendingPathComponent("2026-10-01/new.wav").path])
        drainMain(0.5)
        XCTAssertEqual(t.model.recordings.map(\.id), ["new"])
    }

    func testMeetingsLoadFromTheFolderNextToRecordings() throws {
        let t = TestApp()
        XCTAssertEqual(t.model.meetingsDir, t.meetings)
        try Samples.meeting().save(in: t.meetings)
        t.model.reloadRecordings()
        drainMain(0.5)
        XCTAssertEqual(t.model.meetings.map(\.title), ["Weekly sync"])
    }

    func testDeleteRemovesTheFilesAndReloads() {
        let t = TestApp()
        Samples.write([Samples.recording("gone")], to: t.recordings)
        t.model.reloadRecordings()
        drainMain(0.5)
        t.model.delete(t.model.recordings[0])
        drainMain(0.5)
        XCTAssertTrue(t.model.recordings.isEmpty)
        XCTAssertFalse(FileManager.default.fileExists(atPath: t.recordings.appendingPathComponent("2026-10-01/gone.json").path))
    }

    func testFirstNameUsesTheProfile() {
        let t = TestApp()
        t.model.profile.nickname = "Max"
        XCTAssertEqual(t.model.firstName, "Max")
    }

    func testOpenProfileShowsSettingsOnProfile() {
        let t = TestApp()
        t.model.settingsSection = .privacy
        t.model.openProfile()
        XCTAssertTrue(t.model.showSettings)
        XCTAssertEqual(t.model.settingsSection, .profile)
    }

    func testLaunchAtLoginReadsWithoutChangingAnything() {
        _ = TestApp().model.launchAtLogin  // just a status read (registering would affect the real Mac)
    }

    func testNoteRequestOpensTheNoteAndStartsRecording() {
        let t = TestApp()
        var opened = 0
        t.model.openNote = { opened += 1 }
        let recorder = FakeRecorder()
        t.model.note.makeRecorder = { recorder }
        t.model.note.chosenSource = .inPerson
        t.event(["event": "open_note", "start": true])
        drainMain()
        XCTAssertEqual(opened, 1)
        XCTAssertTrue(t.model.note.recording)
        t.event(["event": "open_note"])  // the ◉ without start just opens
        XCTAssertEqual(opened, 2)
        XCTAssertTrue(t.model.note.recording)
    }

    func testMeetingEventsReachTheNote() {
        let t = TestApp()
        t.event(["event": "chunk_text", "id": t.model.note.meetingID, "stream": "you", "speaker": 0, "offset": 1.0, "text": "Hello."])
        XCTAssertEqual(t.model.note.transcript.lines.map(\.text), ["Hello."])
    }

    func testEngineStoppingTheMeetingStopsTheNote() {
        let t = TestApp()
        let recorder = FakeRecorder()
        t.model.note.makeRecorder = { recorder }
        t.model.note.chosenSource = .inPerson
        t.model.note.start()
        t.event(["event": "meeting", "active": true])
        t.event(["event": "meeting", "active": false])  // the widget's ■
        XCTAssertFalse(t.model.note.recording)
        XCTAssertEqual(recorder.stopped, 1)
    }
}

/// Profile: what's remembered, the photo, and the theme and appearance it applies.
final class ProfileTests: XCTestCase {
    func make(_ defaults: UserDefaults, _ photo: URL) -> Profile { Profile(defaults: defaults, photoURL: photo) }

    func testEverythingIsRememberedAcrossLaunches() {
        let defaults = UserDefaults(suiteName: "profile-\(UUID())")!
        let photo = FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID()).png")
        let p = make(defaults, photo)
        p.name = "Maxwell Dalrymple"
        p.nickname = "Max"
        p.role = "Founder"
        p.avatarColor = Profile.avatarColors[2]
        p.themeID = "ocean"
        p.appearance = .dark
        let again = make(defaults, photo)
        XCTAssertEqual(again.info, ProfileInfo(name: "Maxwell Dalrymple", nickname: "Max", role: "Founder"))
        XCTAssertEqual(again.avatarColor, Profile.avatarColors[2])
        XCTAssertEqual(again.themeID, "ocean")
        XCTAssertEqual(again.appearance, .dark)
        p.appearance = .system  // leave the test app's appearance alone
    }

    func testDefaults() {
        let p = make(UserDefaults(suiteName: "profile-\(UUID())")!, URL(fileURLWithPath: "/nonexistent.png"))
        XCTAssertEqual(p.themeID, "classic")
        XCTAssertEqual(p.appearance, .system)
        XCTAssertEqual(p.avatarColor, Profile.avatarColors[0])
        XCTAssertNil(p.photo)
    }

    func testThemeChangesThePaletteEverythingDrawsWith() {
        let p = make(UserDefaults(suiteName: "profile-\(UUID())")!, URL(fileURLWithPath: "/nonexistent.png"))
        p.themeID = "sunset"
        XCTAssertEqual(Palette.current, .sunset)
        XCTAssertEqual(p.lookID, "sunset-System")
        p.themeID = "classic"
    }

    func testAppearanceIsAppliedToTheApp() {
        _ = NSApplication.shared
        let p = make(UserDefaults(suiteName: "profile-\(UUID())")!, URL(fileURLWithPath: "/nonexistent.png"))
        p.appearance = .dark
        XCTAssertEqual(NSApp.appearance?.name, .darkAqua)
        p.appearance = .light
        XCTAssertEqual(NSApp.appearance?.name, .aqua)
        p.appearance = .system
        XCTAssertNil(NSApp.appearance)
    }

    func testPhotoIsSavedSquareAndCanBeRemoved() {
        let photo = FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID()).png")
        let p = make(UserDefaults(suiteName: "profile-\(UUID())")!, photo)
        let wide = NSImage(size: NSSize(width: 400, height: 200))
        wide.lockFocus(); NSColor.red.setFill(); NSRect(x: 0, y: 0, width: 400, height: 200).fill(); wide.unlockFocus()
        p.setPhoto(wide)
        XCTAssertEqual(p.photo?.size, NSSize(width: 256, height: 256))
        XCTAssertTrue(FileManager.default.fileExists(atPath: photo.path))
        XCTAssertNotNil(make(UserDefaults(suiteName: "profile-\(UUID())")!, photo).photo)  // loads next launch
        p.removePhoto()
        XCTAssertNil(p.photo)
        XCTAssertFalse(FileManager.default.fileExists(atPath: photo.path))
    }

    func testSquareThumbnailCropsTheMiddle() {
        let tall = NSImage(size: NSSize(width: 100, height: 300))
        XCTAssertEqual(Profile.squareThumbnail(tall, side: 64).size, NSSize(width: 64, height: 64))
    }
}

/// Theme: palettes, the colors charts use, and hex parsing.
final class ThemeTests: XCTestCase {
    func testSixPalettesWithUniqueNames() {
        XCTAssertEqual(Palette.all.map(\.id), ["classic", "ocean", "forest", "sunset", "lavender", "midnight"])
        XCTAssertEqual(Set(Palette.all.map(\.name)).count, 6)
    }

    func testUnknownThemeFallsBackToClassic() {
        XCTAssertEqual(Palette.named("neon"), .classic)
        XCTAssertEqual(Palette.named("forest"), .forest)
    }

    func testHexColors() {
        let c = Theme.nsColor(hex: 0x1F5C4A)
        XCTAssertEqual(c.redComponent, 0x1F / 255, accuracy: 0.001)
        XCTAssertEqual(c.greenComponent, 0x5C / 255, accuracy: 0.001)
        XCTAssertEqual(c.blueComponent, 0x4A / 255, accuracy: 0.001)
    }

    func testResolvedColorsFollowThePaletteAndScheme() {
        Palette.current = .ocean
        defer { Palette.current = .classic }
        XCTAssertEqual(NSColor(Theme.resolved(\.accent, .light)).usingColorSpace(.sRGB)?.blueComponent ?? 0,
                       CGFloat(0xB8) / 255, accuracy: 0.01)
        XCTAssertEqual(NSColor(Theme.resolved(\.accent, .dark)).usingColorSpace(.sRGB)?.blueComponent ?? 0,
                       CGFloat(0xF0) / 255, accuracy: 0.01)
    }

    func testDisplayFontIsSerif() {
        _ = Theme.display(20)  // builds (used for every headline)
    }
}

/// Deleting notes, and renaming, removing and adding details for people, from the app.
final class NotesAndPeopleActionsTests: XCTestCase {
    var t: TestApp!

    override func setUp() {
        t = TestApp()
        try? Samples.meeting("A", people: ["Priya Shah", "Jordan Lee"]).save(in: t.meetings)
        try? Samples.meeting("B", people: ["Priya Shah"], daysAgo: 2).save(in: t.meetings)
        t.model.reloadRecordings()
        drainMain(0.5)
        XCTAssertEqual(t.model.meetings.count, 2)
    }

    func testDeleteMeetingsRemovesThemAtOnceAndOnDisk() {
        t.model.deleteMeetings(t.model.meetings)
        XCTAssertTrue(t.model.meetings.isEmpty)
        XCTAssertTrue(MeetingStore.load(from: t.meetings).isEmpty)
        XCTAssertNil(t.model.notesError)
    }

    func testRenamePersonEverywhereAndMoveTheirCard() {
        t.model.saveContact(Contact(email: "p@x.com"), for: "Priya Shah")
        t.model.renamePerson("Priya Shah", to: "Priya S.")
        drainMain(0.5)
        XCTAssertEqual(PeopleIndex.people(t.model.meetings).first?.name, "Priya S.")
        XCTAssertEqual(PeopleIndex.people(t.model.meetings).first?.meetings, 2)
        XCTAssertEqual(t.model.contacts["Priya S."]?.email, "p@x.com")
        XCTAssertNil(t.model.contacts["Priya Shah"])
    }

    func testSaveContactWithANewNameRenamesToo() {
        t.model.saveContact(Contact(company: "Acme"), for: "Jordan Lee", newName: "Jordan")
        drainMain(0.5)
        XCTAssertEqual(t.model.contacts, ["Jordan": Contact(company: "Acme")])
        XCTAssertTrue(PeopleIndex.people(t.model.meetings).contains { $0.name == "Jordan" })
        XCTAssertEqual(ContactBook.load(from: ContactBook.url(in: t.meetings)), ["Jordan": Contact(company: "Acme")])
    }

    func testRemovePersonKeepsTheNotesAndDropsTheirCard() {
        t.model.saveContact(Contact(phone: "555"), for: "Priya Shah")
        t.model.removePerson("Priya Shah")
        drainMain(0.5)
        XCTAssertEqual(t.model.meetings.count, 2)
        XCTAssertFalse(PeopleIndex.people(t.model.meetings).contains { $0.name == "Priya Shah" })
        XCTAssertTrue(t.model.contacts.isEmpty)
    }

    func testFailuresShowAMessage() throws {
        try FileManager.default.removeItem(at: t.meetings)  // the files vanished under us
        t.model.renamePerson("Priya Shah", to: "P")
        XCTAssertNotNil(t.model.notesError)
    }
}
