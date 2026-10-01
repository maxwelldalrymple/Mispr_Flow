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
    @Published private(set) var recordings: [Recording] = []
    @Published private(set) var stats = Stats()
    @Published private(set) var more = MoreInsights()
    @Published private(set) var settingsError: String?
    let note = NoteModel()
    let profile = Profile()
    @Published var settingsSection: SettingsModal.Section = .profile
    /// Set by AppDelegate: shows the note side window.
    var openNote: () -> Void = {}
    private var cancellables: Set<AnyCancellable> = []

    init() {
        let logs = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/Mispr Flow/engine.log")
        engine = Engine(config: EngineConfig.resolve(info: Bundle.main.infoDictionary ?? [:], env: ProcessInfo.processInfo.environment),
                        logURL: logs)
        engine.objectWillChange.sink { [weak self] in self?.objectWillChange.send() }.store(in: &cancellables)
        engine.$recordingsDir.compactMap { $0 }.sink { [weak self] _ in
            DispatchQueue.main.async { self?.reloadRecordings() }
        }.store(in: &cancellables)
        engine.saved.sink { [weak self] _ in self?.reloadRecordings() }.store(in: &cancellables)
        profile.objectWillChange.sink { [weak self] in self?.objectWillChange.send() }.store(in: &cancellables)
        engine.noteRequested.sink { [weak self] in self?.openNote() }.store(in: &cancellables)
        engine.$meetingActive.sink { [weak self] active in self?.note.meetingChanged(active) }.store(in: &cancellables)
    }

    func start() {
        // Development: MISPR_PAGE=Insights (etc.) opens on that page, for screenshots.
        if let name = ProcessInfo.processInfo.environment["MISPR_PAGE"], let page = Page(rawValue: name) { self.page = page }
        engine.start()
    }

    func reloadRecordings() {
        guard let dir = engine.recordingsDir else { return }
        DispatchQueue.global(qos: .userInitiated).async {
            let records = RecordingStore.load(from: dir)
            let stats = Stats(records)
            let more = MoreInsights(records)
            DispatchQueue.main.async {
                self.recordings = records
                self.stats = stats
                self.more = more
            }
        }
    }

    func delete(_ record: Recording) {
        try? RecordingStore.delete(record)
        reloadRecordings()
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
