import Combine
import XCTest
@testable import MisprCore

/// The engine as a real child process, using a small shell script in place of Python: it
/// announces itself, echoes one command back as an event, logs to stderr, then waits.
final class EngineProcessTests: XCTestCase {
    var dir: URL!

    override func setUpWithError() throws {
        dir = FileManager.default.temporaryDirectory.appendingPathComponent("engine-\(UUID())")
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
    }

    override func tearDownWithError() throws { try? FileManager.default.removeItem(at: dir) }

    func script(_ body: String) throws -> EngineConfig {
        let url = dir.appendingPathComponent("fake-engine.sh")
        try ("#!/bin/sh\n" + body).write(to: url, atomically: true, encoding: .utf8)
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: url.path)
        return EngineConfig(python: url, projectRoot: dir, arguments: [])
    }

    func wait(_ seconds: TimeInterval = 3, until done: () -> Bool) {
        let end = Date().addingTimeInterval(seconds)
        while !done() && Date() < end { RunLoop.main.run(until: Date().addingTimeInterval(0.05)) }
    }

    func testStartsTalksLogsAndStops() throws {
        let config = try script("""
        echo "starting" >&2
        echo '@mispr {"event": "hello", "recordings_dir": "/r", "settings_path": "/s"}'
        read line
        echo "@mispr {\\"event\\": \\"saved\\", \\"path\\": \\"/got\\"}"
        echo "command was: $line" >&2
        sleep 30
        """)
        let log = dir.appendingPathComponent("logs/engine.log")
        let engine = Engine(config: config, logURL: log)
        var saved: [URL] = []
        let sub = engine.saved.sink { saved.append($0) }
        engine.start()
        wait { engine.state == .running }
        XCTAssertEqual(engine.state, .running)
        XCTAssertEqual(engine.recordingsDir?.path, "/r")

        engine.send(.openSetup)
        wait { !saved.isEmpty }
        XCTAssertEqual(saved, [URL(fileURLWithPath: "/got")])

        engine.stop()
        wait { engine.state == .stopped }
        XCTAssertEqual(engine.state, .stopped)
        let text = try String(contentsOf: log, encoding: .utf8)
        XCTAssertTrue(text.contains("starting"))
        XCTAssertTrue(text.contains(#"command was: {"cmd":"open_setup"}"#))
        sub.cancel()
    }

    func testCleanExitQuitsTheApp() throws {
        let engine = Engine(config: try script("exit 0"))
        var quit = false
        engine.onCleanExit = { quit = true }
        engine.start()
        wait { quit }
        XCTAssertTrue(quit)
    }

    func testCrashRestartsTheEngine() throws {
        let counter = dir.appendingPathComponent("runs")
        let engine = Engine(config: try script("echo run >> '\(counter.path)'\nexit 3"))
        engine.start()
        wait(4) { ((try? String(contentsOf: counter, encoding: .utf8)) ?? "").components(separatedBy: "run").count - 1 >= 2 }
        engine.stop()
        let runs = ((try? String(contentsOf: counter, encoding: .utf8)) ?? "").components(separatedBy: "run").count - 1
        XCTAssertGreaterThanOrEqual(runs, 2)  // started again after crashing
    }

    func testMissingProgramFails() {
        let engine = Engine(config: EngineConfig(python: URL(fileURLWithPath: "/nonexistent/python"), projectRoot: dir))
        engine.start()
        guard case .failed = engine.state else { return XCTFail("expected failed, got \(engine.state)") }
    }

    func testSendWithoutAProcessIsIgnored() {
        Engine(config: nil).send(.quit)  // no process: nothing to write to, no crash
    }

    func testStopWithoutAProcessIsHarmless() {
        Engine(config: nil).stop()
    }
}

final class CoreGapTests: XCTestCase {
    func testTryArgs() {
        let draft = PromptDraft(system: "S", extra: "E", examples: "Said: a\nWrote: b", guardOn: false)
        let args = draft.tryArgs(text: "um hi")
        XCTAssertEqual(args["text"] as? String, "um hi")
        XCTAssertEqual(args["system"] as? String, "S")
        XCTAssertEqual(args["extra"] as? String, "E")
        XCTAssertEqual(args["examples"] as? String, "Said: a\nWrote: b")
        XCTAssertEqual(args["guard"] as? Bool, false)
    }

    func testDefaultSettingsLocation() {
        XCTAssertTrue(SettingsFile.defaultURL.path.hasSuffix("Library/Application Support/Mispr_Flow/settings.json"))
    }

    func testEveryMeetingSourceHasASymbolAndID() {
        for source in MeetingSource.allCases {
            XCTAssertFalse(source.symbol.isEmpty)
            XCTAssertEqual(source.id, source.rawValue)
        }
    }

    func testSpeakerPace() {
        let s = MeetingInsights.Speaker(name: "A", seconds: 30, words: 60, turns: 1, questions: 0, share: 50)
        XCTAssertEqual(s.wpm, 120)
        XCTAssertEqual(s.id, "A")
        XCTAssertEqual(MeetingInsights.Speaker(name: "B", seconds: 0, words: 5, turns: 1, questions: 0, share: 0).wpm, 0)
    }

    func testStatsEquality() {
        XCTAssertEqual(Stats(), Stats())
        var other = Stats()
        other.totalWords = 1
        XCTAssertNotEqual(Stats(), other)
    }

    func testUsageCategoryID() {
        XCTAssertEqual(UsageCategory.emails.id, "Emails")
    }
}
