import Combine
import Foundation

/// Where to find the Python engine. The build script writes these into Info.plist
/// (MisprPython, MisprProjectRoot); the environment (MISPR_PYTHON, MISPR_PROJECT_ROOT)
/// overrides them for `swift run`.
public struct EngineConfig: Equatable {
    public var python: URL
    public var projectRoot: URL

    public init(python: URL, projectRoot: URL) {
        self.python = python
        self.projectRoot = projectRoot
    }

    public static func resolve(info: [String: Any], env: [String: String]) -> EngineConfig? {
        guard let root = env["MISPR_PROJECT_ROOT"] ?? info["MisprProjectRoot"] as? String else { return nil }
        let rootURL = URL(fileURLWithPath: root)
        let python = env["MISPR_PYTHON"] ?? info["MisprPython"] as? String
            ?? rootURL.appendingPathComponent(".venv/bin/python").path
        return EngineConfig(python: URL(fileURLWithPath: python), projectRoot: rootURL)
    }
}

/// Runs the Python engine as a child process: starts it, restarts it if it crashes (a few
/// times), relays its events, and stops it when the app quits.
public final class Engine: ObservableObject {
    public enum State: Equatable {
        case stopped, starting, running
        case failed(String)
    }

    @Published public private(set) var state: State = .stopped
    @Published public private(set) var recordingsDir: URL?
    @Published public private(set) var settingsFile: URL?
    @Published public private(set) var promptsFile: URL?
    @Published public private(set) var defaultPrompts: DefaultPrompts?
    /// Results of Prompts > Try it.
    public let tried = PassthroughSubject<TryResult, Never>()
    /// Fires on the main thread for each saved dictation.
    public let saved = PassthroughSubject<URL, Never>()
    /// The widget's note button was clicked.
    public let noteRequested = PassthroughSubject<Void, Never>()
    /// A meeting is being recorded (the widget shows its meeting pill).
    @Published public private(set) var meetingActive = false
    /// The engine exited cleanly by itself (e.g. Quit from its menu-bar icon): quit the app too.
    public var onCleanExit: () -> Void = {}

    public static let maxRestarts = 3
    public static let restartWindow: TimeInterval = 60

    private let config: EngineConfig?
    private let logURL: URL?
    private var process: Process?
    private var input: FileHandle?
    private var output: Pipe?  // retained: if the pipe is released, its read handler stops firing
    private var splitter = LineSplitter()
    private var crashes: [Date] = []
    private var stopping = false

    public init(config: EngineConfig?, logURL: URL? = nil) {
        self.config = config
        self.logURL = logURL
    }

    public func start() {
        guard let config else {
            state = .failed("Can't find the Mispr Flow engine (no MisprProjectRoot).")
            return
        }
        stopping = false
        state = .starting
        let process = Process()
        process.executableURL = config.python
        process.arguments = ["-u", "-m", "mispr"]
        process.currentDirectoryURL = config.projectRoot
        var env = ProcessInfo.processInfo.environment
        env["MISPR_HOSTED"] = "1"
        env["MISPR_DEBUG"] = env["MISPR_DEBUG"] ?? "1"  // the log file is the engine's trace
        process.environment = env

        let stdout = Pipe(), stdin = Pipe()
        process.standardOutput = stdout
        process.standardInput = stdin
        process.standardError = logHandle() ?? FileHandle.nullDevice
        stdout.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            DispatchQueue.main.async { self?.receive(data) }
        }
        process.terminationHandler = { [weak self] p in
            DispatchQueue.main.async { self?.exited(status: p.terminationStatus) }
        }
        do {
            try process.run()
            self.process = process
            self.input = stdin.fileHandleForWriting
            self.output = stdout
        } catch {
            state = .failed("Couldn't start the engine: \(error.localizedDescription)")
        }
    }

    public func send(_ command: EngineCommand, _ args: [String: Any] = [:]) {
        guard let input, process?.isRunning == true else { return }
        try? input.write(contentsOf: Data(command.line(args).utf8))
    }

    /// Stop the engine (it frees its models and wipes audio on SIGTERM) and wait briefly.
    public func stop(timeout: TimeInterval = 3) {
        stopping = true
        guard let process, process.isRunning else { return }
        process.terminate()
        let deadline = Date().addingTimeInterval(timeout)
        while process.isRunning && Date() < deadline { usleep(20_000) }
        if process.isRunning { kill(process.processIdentifier, SIGKILL) }
    }

    // MARK: - Events

    func receive(_ data: Data) {
        for line in splitter.feed(data) {
            guard let event = EngineEvent.parse(line) else { continue }
            handle(event)
        }
    }

    func handle(_ event: EngineEvent) {
        switch event {
        case let .hello(recordings, settings, prompts, defaults):
            recordingsDir = recordings
            settingsFile = settings
            promptsFile = prompts
            defaultPrompts = defaults
            state = .running
        case let .tried(result):
            tried.send(result)
        case let .saved(url):
            saved.send(url)
        case .openNote:
            noteRequested.send()
        case let .meeting(active):
            meetingActive = active
        case .unknown:
            break
        }
    }

    func exited(status: Int32, now: Date = Date()) {
        output?.fileHandleForReading.readabilityHandler = nil
        process = nil
        input = nil
        output = nil
        meetingActive = false
        if stopping { state = .stopped; return }
        if status == 0 { state = .stopped; onCleanExit(); return }
        crashes = crashes.filter { now.timeIntervalSince($0) < Self.restartWindow } + [now]
        if crashes.count > Self.maxRestarts {
            state = .failed("The engine keeps stopping (exit \(status)). See the engine log.")
            return
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [weak self] in
            guard let self, !self.stopping else { return }
            self.start()
        }
    }

    private func logHandle() -> FileHandle? {
        guard let logURL else { return nil }
        try? FileManager.default.createDirectory(at: logURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        if !FileManager.default.fileExists(atPath: logURL.path) {
            FileManager.default.createFile(atPath: logURL.path, contents: nil)
        }
        let handle = try? FileHandle(forWritingTo: logURL)
        _ = try? handle?.seekToEnd()
        return handle
    }
}
