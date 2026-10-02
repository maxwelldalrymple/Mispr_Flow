import AppKit
import Combine
import MisprCore
import ServiceManagement

enum Page: String, CaseIterable, Identifiable {
    case home = "Home"
    case notetaker = "Notetaker"
    case insights = "Insights"
    case prompts = "Prompts"

    var id: String { rawValue }

    var symbol: String {
        switch self {
        case .home: "mic"
        case .notetaker: "record.circle"
        case .insights: "chart.bar"
        case .prompts: "text.bubble"
        }
    }
}

/// Everything the window shows: the engine, saved dictations, stats, and settings.
final class AppModel: ObservableObject {
    let engine: Engine
    @Published var page: Page = .home
    @Published var showSettings = false
    /// The tour step on screen (index into `TourStep.all`), or nil when the tour isn't showing.
    @Published var tourStep: Int?
    @Published private(set) var recordings: [Recording] = []
    @Published private(set) var stats = Stats()
    @Published private(set) var more = MoreInsights()
    @Published private(set) var voice = VoiceProfile()
    @Published private(set) var meetings: [Meeting] = []
    /// Contact cards for people from your meetings, by name.
    @Published private(set) var contacts: [String: Contact] = [:]
    /// The last delete/rename/contact change that failed, shown on the Notetaker page.
    @Published var notesError: String?
    @Published private(set) var settingsError: String?
    let note = NoteModel()
    let profile: Profile
    @Published var settingsSection: SettingsModal.Section = .profile
    /// Set by AppDelegate: shows the note side window.
    var openNote: () -> Void = {}
    private var cancellables: Set<AnyCancellable> = []

    /// Tests pass their own engine (no process) and profile (scratch preferences).
    init(engine injected: Engine? = nil, profile customProfile: Profile? = nil) {
        let logs = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/Mispr Flow/engine.log")
        self.engine = injected ?? Engine(config: EngineConfig.resolve(info: Bundle.main.infoDictionary ?? [:], env: ProcessInfo.processInfo.environment),
                                       logURL: logs)
        self.profile = customProfile ?? Profile()
        engine.objectWillChange.sink { [weak self] in self?.objectWillChange.send() }.store(in: &cancellables)
        engine.$recordingsDir.compactMap { $0 }.sink { [weak self] _ in
            DispatchQueue.main.async { self?.reloadRecordings() }
        }.store(in: &cancellables)
        engine.saved.sink { [weak self] _ in self?.reloadRecordings() }.store(in: &cancellables)
        profile.objectWillChange.sink { [weak self] in self?.objectWillChange.send() }.store(in: &cancellables)
        engine.noteRequested.sink { [weak self] start in
            guard let self else { return }
            self.openNote()
            if start { self.note.toggle() }  // ⌥M / ◉: start, or stop if already recording
        }.store(in: &cancellables)
        engine.meetingEvents.sink { [weak self] event in self?.note.handle(event) }.store(in: &cancellables)
        note.engine = engine
        note.meetingsDir = { [weak self] in self?.meetingsDir }
        note.incognito = { [weak self] in self?.setting("incognito") ?? false }
        note.onSaved = { [weak self] in self?.reloadRecordings() }
        engine.$meetingActive.sink { [weak self] active in self?.note.meetingChanged(active) }.store(in: &cancellables)
    }

    func start() {
        // Development: MISPR_PAGE=Insights (etc.) opens on that page, for screenshots.
        if let name = ProcessInfo.processInfo.environment["MISPR_PAGE"] {
            self.page = Page(rawValue: name) ?? (name == "Voice" ? .insights : page)
        }
        engine.start()
    }

    /// meeting-recordings/ sits next to voice-recordings/.
    var meetingsDir: URL? { engine.recordingsDir?.deletingLastPathComponent().appendingPathComponent("meeting-recordings") }

    func reloadRecordings() {
        guard let dir = engine.recordingsDir else { return }
        let meetingsDir = self.meetingsDir
        DispatchQueue.global(qos: .userInitiated).async {
            let records = RecordingStore.load(from: dir)
            let meetings = meetingsDir.map { MeetingStore.load(from: $0) } ?? []
            let contacts = meetingsDir.map { ContactBook.load(from: ContactBook.url(in: $0)) } ?? [:]
            let stats = Stats(records)
            let more = MoreInsights(records)
            let voice = VoiceProfile(records)
            DispatchQueue.main.async {
                self.meetings = meetings
                self.contacts = contacts
                self.voice = voice
                self.recordings = records
                self.stats = stats
                self.more = more
            }
        }
    }

    // MARK: - Tour

    func startTour() {
        showSettings = false
        tourStep = 0
        page = TourStep.all[0].page
    }

    /// The first time the window opens after setup.
    func startTourIfNew() {
        if tourStep == nil && !profile.tutorialDone && setting("onboarded") { startTour() }
    }

    /// Next (+1) or Back (-1); past the last step ends the tour.
    func moveTour(_ by: Int) {
        guard let step = tourStep else { return }
        let next = step + by
        guard next < TourStep.all.count else { return endTour() }
        tourStep = max(0, next)
        page = TourStep.all[max(0, next)].page
    }

    /// Done or Skip tour: it won't start by itself again (Help → Show Tutorial replays it).
    func endTour() {
        tourStep = nil
        profile.tutorialDone = true
        page = .home
    }

    func delete(_ record: Recording) {
        try? RecordingStore.delete(record)
        reloadRecordings()
    }

    // MARK: - Notes and people

    /// Delete notes (JSON and audio). They leave the list right away.
    func deleteMeetings(_ doomed: [Meeting]) {
        notesError = nil
        for meeting in doomed {
            do { try MeetingStore.delete(meeting) } catch { notesError = "Couldn't delete “\(meeting.title)”: \(error.localizedDescription)" }
        }
        let ids = Set(doomed.map(\.id))
        meetings.removeAll { ids.contains($0.id) }
        reloadRecordings()
    }

    /// Rename someone in every note, and move their contact card.
    func renamePerson(_ old: String, to new: String) {
        let new = new.trimmingCharacters(in: .whitespaces)
        guard !new.isEmpty, new != old else { return }
        notesError = nil
        do {
            try MeetingStore.rename(person: old, to: new, in: meetings)
            try writeContacts(ContactBook.renamed(contacts, old, to: new))
        } catch {
            notesError = "Couldn't rename \(old): \(error.localizedDescription)"
        }
        reloadRecordings()
    }

    /// Take someone out of People (their notes stay; their lines become "Unknown speaker").
    func removePerson(_ name: String) {
        notesError = nil
        do {
            try MeetingStore.remove(person: name, from: meetings)
            var book = contacts
            book[name] = nil
            try writeContacts(book)
        } catch {
            notesError = "Couldn't remove \(name): \(error.localizedDescription)"
        }
        reloadRecordings()
    }

    /// Save someone's contact card (and rename them if the name was changed on it).
    func saveContact(_ card: Contact, for name: String, newName: String? = nil) {
        notesError = nil
        var book = contacts
        book[name] = card
        do { try writeContacts(book) } catch { notesError = "Couldn't save \(name)'s details: \(error.localizedDescription)" }
        if let newName, !newName.trimmingCharacters(in: .whitespaces).isEmpty, newName != name {
            renamePerson(name, to: newName)
        }
    }

    private func writeContacts(_ book: [String: Contact]) throws {
        contacts = book.filter { !$0.value.isEmpty }
        guard let dir = meetingsDir else { return }
        try ContactBook.save(book, to: ContactBook.url(in: dir))
    }

    var firstName: String {
        profile.info.greetingName(account: NSFullUserName())
    }

    func openProfile() {
        settingsSection = .profile
        showSettings = true
    }

    // MARK: - Settings

    private var settingsFile: SettingsFile { SettingsFile(url: engine.settingsFile ?? SettingsFile.defaultURL) }

    func setting(_ key: String) -> Bool { settingsFile.bool(key) }

    var dictationKey: DictationKey { settingsFile.dictationKey }
    var switchKey: DictationKey? { settingsFile.switchKey }
    var nicknames: [String: String] { settingsFile.nicknames }

    /// The app switcher key (nil turns it off).
    func setSwitchKey(_ key: DictationKey?) {
        do {
            try settingsFile.setSwitchKey(key)
            settingsError = nil
            engine.send(.reloadSettings)
        } catch {
            settingsError = "Couldn't save the shortcut: \(error.localizedDescription)"
        }
        objectWillChange.send()
    }

    /// Add (or with app nil, remove) a spoken nickname. Nicknames are kept lowercase, as heard.
    func setNickname(_ nickname: String, app: String?) {
        let nick = nickname.trimmingCharacters(in: .whitespaces).lowercased()
        guard !nick.isEmpty else { return }
        var all = nicknames
        all[nick] = app
        do {
            try settingsFile.setNicknames(all)
            settingsError = nil
            engine.send(.reloadSettings)
        } catch {
            settingsError = "Couldn't save the nickname: \(error.localizedDescription)"
        }
        objectWillChange.send()
    }

    func setDictationKey(_ key: DictationKey) {
        do {
            try settingsFile.setDictationKey(key)
            settingsError = nil
            engine.send(.reloadSettings)  // the engine switches keys immediately
        } catch {
            settingsError = "Couldn't save the shortcut: \(error.localizedDescription)"
        }
        objectWillChange.send()
    }

    func setSetting(_ key: String, _ value: Bool) {
        do {
            try settingsFile.set(key, value)
            settingsError = nil
            engine.send(.reloadSettings)
        } catch {
            settingsError = "Couldn't save settings: \(error.localizedDescription)"
        }
        objectWillChange.send()
    }

    var launchAtLogin: Bool {
        get { SMAppService.mainApp.status == .enabled }
        set {
            do {
                if newValue { try SMAppService.mainApp.register() } else { try SMAppService.mainApp.unregister() }
                settingsError = nil
            } catch {
                settingsError = "Couldn't change Launch at login: \(error.localizedDescription)"
            }
            objectWillChange.send()
        }
    }
}
