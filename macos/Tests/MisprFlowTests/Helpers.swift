import AppKit
@testable import MisprCore
import SwiftUI
import XCTest
@testable import MisprFlow

/// A test app model: no engine process, everything in a temp folder, scratch preferences,
/// and every command the app sends recorded in `sent`.
final class TestApp {
    let dir: URL
    let engine = Engine(config: nil)
    let model: AppModel
    var sent: [(EngineCommand, [String: Any])] = []

    var recordings: URL { dir.appendingPathComponent("voice-recordings") }
    var meetings: URL { dir.appendingPathComponent("meeting-recordings") }
    var settings: URL { dir.appendingPathComponent("settings.json") }
    var prompts: URL { dir.appendingPathComponent("prompts.json") }

    init(hello: Bool = true) {
        dir = FileManager.default.temporaryDirectory.appendingPathComponent("mispr-tests-\(UUID().uuidString)")
        try? FileManager.default.createDirectory(at: dir.appendingPathComponent("voice-recordings"), withIntermediateDirectories: true)
        let defaults = UserDefaults(suiteName: "mispr-tests-\(UUID().uuidString)")!
        let profile = Profile(defaults: defaults, photoURL: dir.appendingPathComponent("photo.png"))
        model = AppModel(engine: engine, profile: profile)
        engine.sendHook = { [unowned self] command, args in self.sent.append((command, args)) }
        if hello { sayHello() }
    }

    /// What the engine sends at startup (paths and default prompts).
    func sayHello() {
        let object: [String: Any] = [
            "event": "hello", "recordings_dir": recordings.path, "settings_path": settings.path,
            "prompts_path": prompts.path,
            "default_prompts": ["system": "Clean it.", "examples": "Said: um hi\nWrote: Hi."],
        ]
        event(object)
    }

    func event(_ object: [String: Any]) {
        let json = String(decoding: try! JSONSerialization.data(withJSONObject: object), as: UTF8.self)
        engine.receive(Data((EngineEvent.prefix + json + "\n").utf8))
    }

    var commands: [EngineCommand] { sent.map(\.0) }

    deinit { try? FileManager.default.removeItem(at: dir) }
}

/// Stands in for the microphone + system audio recorder.
final class FakeRecorder: MeetingRecording {
    var onChunk: (String, Double, [Float]) -> Void = { _, _, _ in }
    var onLevel: (Float) -> Void = { _ in }
    var onError: (String) -> Void = { _ in }
    var started: (systemAudio: Bool, saveTo: URL?)?
    var stopped = 0
    var warning: String?
    var failure: Error?
    var current: [(stream: String, start: Double, samples: [Float])] = []

    func start(systemAudio: Bool, saveTo: URL?) async throws -> String? {
        if let failure { throw failure }
        started = (systemAudio, saveTo)
        return warning
    }

    func stop() { stopped += 1 }
    func inProgress() -> [(stream: String, start: Double, samples: [Float])] { current }
}

/// Wait for queued main-thread work (async hops in the models) to run.
func drainMain(_ seconds: TimeInterval = 0.2) {
    RunLoop.main.run(until: Date().addingTimeInterval(seconds))
}

/// Lay out and draw a SwiftUI view offscreen (so every `body` actually runs); returns the
/// rendered image so tests can check something was drawn.
@discardableResult
func render<V: View>(_ view: V, model: AppModel, size: CGSize = CGSize(width: 1180, height: 800),
                     appearance: NSAppearance? = nil) -> NSBitmapImageRep {
    let host = NSHostingView(rootView: view.environmentObject(model).environmentObject(model.note))
    host.frame = NSRect(origin: .zero, size: size)
    let window = NSWindow(contentRect: host.frame, styleMask: [.borderless], backing: .buffered, defer: false)
    window.appearance = appearance  // nil: the system's light or dark
    window.contentView = host
    host.layoutSubtreeIfNeeded()
    drainMain(0.05)
    let rep = host.bitmapImageRepForCachingDisplay(in: host.bounds)!
    host.cacheDisplay(in: host.bounds, to: rep)
    return rep
}

/// True when the image isn't a single flat color.
func hasContent(_ rep: NSBitmapImageRep) -> Bool {
    let first = rep.colorAt(x: 5, y: 5)
    for x in stride(from: 0, to: rep.pixelsWide, by: 37) {
        for y in stride(from: 0, to: rep.pixelsHigh, by: 41) where rep.colorAt(x: x, y: y) != first { return true }
    }
    return false
}

enum Samples {
    static func recording(_ id: String = UUID().uuidString, daysAgo: Double = 0, text: String = "Ship the release on Friday.",
                          status: Recording.Status = .pasted, app: String = "Slack", bundle: String = "com.tinyspeck.slackmacgap") -> Recording {
        let start = Date().addingTimeInterval(-daysAgo * 86_400)
        return Recording(id: id, startedAt: start, endedAt: start.addingTimeInterval(4), durationS: 4, status: status,
                         transcript: text, rawTranscript: "um " + text, words: text.split(separator: " ").count,
                         recordedIn: AppRef(app: app, bundleId: bundle), pastedInto: AppRef(app: app, bundleId: bundle),
                         audioFile: "\(id).wav")
    }

    /// Write recordings as the engine would (JSON + a WAV) under `dir/<day>/`.
    static func write(_ records: [Recording], to dir: URL) {
        let encoder = JSONEncoder()
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        encoder.dateEncodingStrategy = .custom { date, e in var c = e.singleValueContainer(); try c.encode(f.string(from: date)) }
        for r in records {
            let day = dir.appendingPathComponent("2026-10-01")
            try? FileManager.default.createDirectory(at: day, withIntermediateDirectories: true)
            try! encoder.encode(r).write(to: day.appendingPathComponent("\(r.id).json"))
            try! WAV.data([0, 0.1, -0.1]).write(to: day.appendingPathComponent("\(r.id).wav"))
        }
    }

    static func meeting(_ title: String = "Weekly sync", people: [String] = ["Priya Shah", "Jordan Lee"], daysAgo: Double = 1) -> Meeting {
        var m = Meeting(id: UUID().uuidString, title: title, startedAt: Date().addingTimeInterval(-daysAgo * 86_400), durationS: 600,
                        app: "Zoom",
                        participants: [Meeting.Participant(name: "You", role: nil, isMe: true)] + people.map { Meeting.Participant(name: $0, role: "Design") },
                        transcript: [Meeting.Line(speaker: "You", startS: 0, text: "Let's review the release plan?"),
                                     Meeting.Line(speaker: people[0], startS: 30, text: "The release ships Friday. Release notes are done.")],
                        myThoughts: "Ask about the installer.")
        m.summary = Meeting.Summary(overview: "Release is on track.", decisions: ["Ship Friday"],
                                    actionItems: [.init(owner: people[0], task: "Send the notes", due: "Thursday")],
                                    openQuestions: ["Pricing?"])
        return m
    }
}
