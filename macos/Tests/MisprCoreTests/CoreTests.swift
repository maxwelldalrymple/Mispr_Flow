import Combine
import XCTest
@testable import MisprCore

final class EngineProtocolTests: XCTestCase {
    func testHello() {
        let event = EngineEvent.parse(#"@mispr {"event": "hello", "recordings_dir": "/r", "settings_path": "/s/settings.json"}"#)
        XCTAssertEqual(event, .hello(recordingsDir: URL(fileURLWithPath: "/r"), settingsFile: URL(fileURLWithPath: "/s/settings.json"),
                                     promptsFile: nil, defaultPrompts: nil))
        let full = EngineEvent.parse(#"@mispr {"event": "hello", "recordings_dir": "/r", "settings_path": "/s", "prompts_path": "/p.json", "default_prompts": {"system": "S", "examples": "Said: a\nWrote: b"}}"#)
        XCTAssertEqual(full, .hello(recordingsDir: URL(fileURLWithPath: "/r"), settingsFile: URL(fileURLWithPath: "/s"),
                                    promptsFile: URL(fileURLWithPath: "/p.json"), defaultPrompts: DefaultPrompts(system: "S", examples: "Said: a\nWrote: b")))
    }

    func testSaved() {
        XCTAssertEqual(EngineEvent.parse(#"@mispr {"event": "saved", "path": "/r/a.wav"}"#), .saved(URL(fileURLWithPath: "/r/a.wav")))
    }

    func testNoteAndMeetingEvents() {
        XCTAssertEqual(EngineEvent.parse(#"@mispr {"event": "open_note"}"#), .openNote)
        XCTAssertEqual(EngineEvent.parse(#"@mispr {"event": "meeting", "active": true}"#), .meeting(active: true))
        XCTAssertNil(EngineEvent.parse(#"@mispr {"event": "meeting"}"#))
        XCTAssertEqual(EngineCommand.startMeeting.rawValue, "start_meeting")  // must match mispr/app.py
        XCTAssertEqual(EngineCommand.stopMeeting.rawValue, "stop_meeting")
    }

    func testEngineTracksMeetingAndNoteRequests() {
        let engine = Engine(config: nil)
        var requests = 0
        let sub = engine.noteRequested.sink { requests += 1 }
        engine.receive(Data("@mispr {\"event\": \"open_note\"}\n@mispr {\"event\": \"meeting\", \"active\": true}\n".utf8))
        XCTAssertEqual(requests, 1)
        XCTAssertTrue(engine.meetingActive)
        engine.exited(status: 1)
        XCTAssertFalse(engine.meetingActive)  // a crashed engine isn't recording
        sub.cancel()
    }

    func testIgnoresOtherOutput() {
        for line in ["", "hello", "mispr: already running", #"{"event": "saved", "path": "/x"}"#, "@mispr not json",
                     #"@mispr {"no_event": 1}"#, #"@mispr {"event": "hello"}"#, #"@mispr {"event": "saved"}"#] {
            XCTAssertNil(EngineEvent.parse(line), line)
        }
    }

    func testTried() {
        XCTAssertEqual(EngineEvent.parse(#"@mispr {"event": "tried", "output": "Hi.", "applied": true, "rejected": null, "ms": 40}"#),
                       .tried(TryResult(output: "Hi.", applied: true, rejected: nil, ms: 40)))
    }

    func testUnknownEventsAreKept() {
        XCTAssertEqual(EngineEvent.parse(#"@mispr {"event": "future"}"#), .unknown("future"))
    }

    func testCommandsAreJSONLines() throws {
        for command in [EngineCommand.openSetup, .reloadSettings, .quit] {
            XCTAssertTrue(command.line.hasSuffix("\n"))
            let object = try JSONSerialization.jsonObject(with: Data(command.line.utf8)) as? [String: String]
            XCTAssertEqual(object, ["cmd": command.rawValue])
        }
        let withArgs = EngineCommand.tryPrompt.line(["text": "um \"hi\"\nthere", "guard": false])
        XCTAssertEqual(withArgs.filter { $0 == "\n" }.count, 1)  // newlines in values stay escaped
        let object = try JSONSerialization.jsonObject(with: Data(withArgs.utf8)) as? [String: Any]
        XCTAssertEqual(object?["cmd"] as? String, "try_prompt")
        XCTAssertEqual(object?["text"] as? String, "um \"hi\"\nthere")
        XCTAssertEqual(object?["guard"] as? Bool, false)
        XCTAssertEqual(EngineCommand.openSetup.rawValue, "open_setup")  // must match mispr/app.py
        XCTAssertEqual(EngineCommand.reloadSettings.rawValue, "reload_settings")
    }

    func testLineSplitterHoldsPartialLines() {
        var splitter = LineSplitter()
        XCTAssertEqual(splitter.feed(Data("one\ntw".utf8)), ["one"])
        XCTAssertEqual(splitter.feed(Data("o\n\nthree".utf8)), ["two", ""])
        XCTAssertEqual(splitter.feed(Data("\n".utf8)), ["three"])
    }
}

final class EngineTests: XCTestCase {
    func testConfigFromInfoPlist() {
        let config = EngineConfig.resolve(info: ["MisprProjectRoot": "/p", "MisprPython": "/p/py"], env: [:])
        XCTAssertEqual(config, EngineConfig(python: URL(fileURLWithPath: "/p/py"), projectRoot: URL(fileURLWithPath: "/p")))
    }

    func testEnvironmentOverridesAndVenvDefault() {
        let config = EngineConfig.resolve(info: ["MisprProjectRoot": "/p"], env: ["MISPR_PROJECT_ROOT": "/q"])
        XCTAssertEqual(config?.projectRoot.path, "/q")
        XCTAssertEqual(config?.python.path, "/q/.venv/bin/python")
    }

    func testNoConfigFails() {
        XCTAssertNil(EngineConfig.resolve(info: [:], env: [:]))
        let engine = Engine(config: nil)
        engine.start()
        guard case .failed = engine.state else { return XCTFail("expected failed, got \(engine.state)") }
    }

    func testHelloMarksRunningAndStoresPaths() {
        let engine = Engine(config: nil)
        engine.receive(Data((#"@mispr {"event": "hello", "recordings_dir": "/r", "settings_path": "/s"}"# + "\n").utf8))
        XCTAssertEqual(engine.state, .running)
        XCTAssertEqual(engine.recordingsDir?.path, "/r")
        XCTAssertEqual(engine.settingsFile?.path, "/s")
    }

    func testSavedIsRelayed() {
        let engine = Engine(config: nil)
        var saved: [URL] = []
        let sub = engine.saved.sink { saved.append($0) }
        engine.receive(Data("[log] noise\n@mispr {\"event\": \"saved\", \"path\": \"/r/a.wav\"}\n".utf8))
        XCTAssertEqual(saved, [URL(fileURLWithPath: "/r/a.wav")])
        sub.cancel()
    }

    func testCleanExitQuitsTheApp() {
        let engine = Engine(config: nil)
        var quit = 0
        engine.onCleanExit = { quit += 1 }
        engine.exited(status: 0)
        XCTAssertEqual(quit, 1)
        XCTAssertEqual(engine.state, .stopped)
    }

    func testCrashLoopGivesUp() {
        let engine = Engine(config: nil)
        let now = Date()
        for i in 0..<Engine.maxRestarts {
            engine.exited(status: 1, now: now.addingTimeInterval(Double(i)))
            if case .failed = engine.state { XCTFail("gave up too early") }
        }
        engine.exited(status: 1, now: now.addingTimeInterval(10))
        guard case .failed = engine.state else { return XCTFail("expected failed") }
    }

    func testOldCrashesAreForgotten() {
        let engine = Engine(config: nil)
        let now = Date()
        for i in 0..<10 {  // one crash every two minutes never trips the limit
            engine.exited(status: 1, now: now.addingTimeInterval(Double(i) * 120))
        }
        if case .failed = engine.state { XCTFail("should keep restarting") }
    }

    func testStoppingIsNotACrash() {
        let engine = Engine(config: nil)
        var quit = 0
        engine.onCleanExit = { quit += 1 }
        engine.stop()
        engine.exited(status: 15)
        XCTAssertEqual(engine.state, .stopped)
        XCTAssertEqual(quit, 0)
    }
}

final class RecordingTests: XCTestCase {
    var dir: URL!

    override func setUpWithError() throws {
        dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: dir.appendingPathComponent("2026-09-30"), withIntermediateDirectories: true)
    }

    override func tearDownWithError() throws {
        try? FileManager.default.removeItem(at: dir)
    }

    func write(_ name: String, _ json: String) throws {
        try Data(json.utf8).write(to: dir.appendingPathComponent("2026-09-30/\(name).json"))
    }

    static let sample = """
    {"id": "2026-09-30_16-21-43-757", "started_at": "2026-09-30T16:21:43.757-04:00",
     "ended_at": "2026-09-30T16:21:52.382-04:00", "duration_s": 8.6, "status": "pasted",
     "transcript": "Hello there.", "raw_transcript": "um hello there", "words": 2,
     "recorded_in": {"app": "Claude", "bundle_id": "com.anthropic.claudefordesktop"},
     "pasted_into": {"app": "Chrome", "bundle_id": "com.google.Chrome", "url": "https://mail.google.com/x", "page_title": "Inbox"},
     "model": "m", "cleanup": {"applied": true}, "audio_file": "2026-09-30_16-21-43-757.wav"}
    """

    func testDecodesTheEnginesFormat() throws {
        try write("a", Self.sample)
        let records = RecordingStore.load(from: dir)
        XCTAssertEqual(records.count, 1)
        let r = records[0]
        XCTAssertEqual(r.status, .pasted)
        XCTAssertEqual(r.words, 2)
        XCTAssertEqual(r.startedAt.timeIntervalSince1970, 1790799703.757, accuracy: 0.001)
        XCTAssertEqual(r.app?.pageTitle, "Inbox")
        XCTAssertTrue(r.wasCleaned)
        // The audio sits next to its JSON (compared that way because the temp folder is
        // reachable as both /var and /private/var).
        XCTAssertEqual(r.audioURL?.lastPathComponent, "2026-09-30_16-21-43-757.wav")
        XCTAssertEqual(r.audioURL?.deletingLastPathComponent(), r.fileURL?.deletingLastPathComponent())
    }

    func testNewestFirstAndBadFilesSkipped() throws {
        try write("a", Self.sample)
        try write("b", Self.sample.replacingOccurrences(of: "16:21:43.757", with: "17:00:00").replacingOccurrences(of: "\"id\": \"2026-09-30_16-21-43-757\"", with: "\"id\": \"later\""))
        try write("broken", "{not json")
        try Data("x".utf8).write(to: dir.appendingPathComponent("2026-09-30/a.wav"))
        XCTAssertEqual(RecordingStore.load(from: dir).map(\.id), ["later", "2026-09-30_16-21-43-757"])
    }

    func testMissingFolderIsEmpty() {
        XCTAssertEqual(RecordingStore.load(from: dir.appendingPathComponent("nope")), [])
    }

    func testDeleteRemovesJSONAndAudio() throws {
        try write("2026-09-30_16-21-43-757", Self.sample)
        let wav = dir.appendingPathComponent("2026-09-30/2026-09-30_16-21-43-757.wav")
        try Data("x".utf8).write(to: wav)
        let record = RecordingStore.load(from: dir)[0]
        try RecordingStore.delete(record)
        XCTAssertFalse(FileManager.default.fileExists(atPath: wav.path))
        XCTAssertEqual(RecordingStore.load(from: dir), [])
    }
}

final class StatsTests: XCTestCase {
    let calendar: Calendar = {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "America/New_York")!
        return c
    }()

    func day(_ d: Int, hour: Int = 10) -> Date {
        calendar.date(from: DateComponents(year: 2026, month: 9, day: d, hour: hour))!
    }

    func rec(_ d: Int, words: Int = 10, seconds: Double = 6, status: Recording.Status = .pasted,
             bundle: String? = "com.apple.Terminal", url: String? = nil, raw: String? = nil, text: String = "hello world") -> Recording {
        Recording(id: UUID().uuidString, startedAt: day(d), endedAt: day(d), durationS: seconds, status: status,
                  transcript: text, rawTranscript: raw, words: words, pastedInto: AppRef(app: "App", bundleId: bundle, url: url))
    }

    func testTotalsAndWPMSkipCancelled() {
        let stats = Stats([rec(28, words: 10, seconds: 6), rec(29, words: 20, seconds: 18), rec(29, words: 99, status: .cancelled)],
                          now: day(30), calendar: calendar)
        XCTAssertEqual(stats.totalWords, 30)
        XCTAssertEqual(stats.dictations, 2)
        XCTAssertEqual(stats.wordsPerMinute, 75)  // 30 words / 0.4 min
    }

    func testCopiedCountsAsDelivered() {
        XCTAssertEqual(Stats([rec(30, status: .copied)], now: day(30), calendar: calendar).dictations, 1)
    }

    func testStreakCountsBackFromToday() {
        let stats = Stats([rec(26), rec(28), rec(29), rec(30)], now: day(30, hour: 18), calendar: calendar)
        XCTAssertEqual(stats.currentStreak, 3)
        XCTAssertEqual(stats.longestStreak, 3)
    }

    func testStreakSurvivesUntilTheDayIsOver() {
        XCTAssertEqual(Stats([rec(28), rec(29)], now: day(30), calendar: calendar).currentStreak, 2)
        XCTAssertEqual(Stats([rec(27), rec(28)], now: day(30), calendar: calendar).currentStreak, 0)
    }

    func testLongestStreakCanBeInThePast() {
        let stats = Stats([rec(10), rec(11), rec(12), rec(13), rec(30)], now: day(30), calendar: calendar)
        XCTAssertEqual(stats.currentStreak, 1)
        XCTAssertEqual(stats.longestStreak, 4)
    }

    func testPerDayCounts() {
        let stats = Stats([rec(29), rec(29), rec(30)], now: day(30), calendar: calendar)
        XCTAssertEqual(stats.perDay[calendar.startOfDay(for: day(29))], 2)
    }

    func testCategoriesAndApps() {
        let stats = Stats([rec(30, bundle: "com.anthropic.claudefordesktop"), rec(30, bundle: "com.google.Chrome", url: "https://mail.google.com/u/0"),
                           rec(30, bundle: "com.tinyspeck.slackmacgap"), rec(30, bundle: "com.unknown.app"), rec(30, bundle: "com.anthropic.claudefordesktop")],
                          now: day(30), calendar: calendar)
        let counts = Dictionary(uniqueKeysWithValues: stats.categories.map { ($0.category, $0.count) })
        XCTAssertEqual(counts[.aiPrompts], 2)
        XCTAssertEqual(counts[.emails], 1)
        XCTAssertEqual(counts[.workMessages], 1)
        XCTAssertEqual(counts[.other], 1)
        XCTAssertEqual(stats.categories.first?.category, .aiPrompts)  // biggest first
        XCTAssertEqual(stats.categories.count, UsageCategory.allCases.count)  // zeros shown too
        XCTAssertEqual(stats.appsUsed, 4)
        XCTAssertEqual(stats.percent(2), 40)
    }

    func testURLBeatsBundle() {
        XCTAssertEqual(UsageCategory.of(AppRef(bundleId: "com.google.Chrome", url: "https://claude.ai/chat/1")), .aiPrompts)
        XCTAssertEqual(UsageCategory.of(AppRef(bundleId: "com.google.Chrome", url: "https://evilclaude.ai")), .other)
        XCTAssertEqual(UsageCategory.of(nil), .other)
    }

    func testCleanedCount() {
        let stats = Stats([rec(30, raw: "um hello world"), rec(30, raw: "hello world"), rec(30, raw: nil)], now: day(30), calendar: calendar)
        XCTAssertEqual(stats.cleaned, 1)
    }

    func testEmpty() {
        let stats = Stats([], now: day(30), calendar: calendar)
        XCTAssertEqual(stats.wordsPerMinute, 0)
        XCTAssertEqual(stats.percent(0), 0)
        XCTAssertEqual(stats.currentStreak, 0)
    }

    func testVoiceProfile() {
        let records = [
            rec(30, words: 6, text: "Deploy the widget, then deploy the docs."),
            rec(29, words: 4, text: "Widget looks great now."),
            rec(29, words: 2, status: .cancelled, text: "ignored ignored ignored"),
        ]
        let profile = VoiceProfile(records, calendar: calendar)
        XCTAssertEqual(profile.mostUsedWords, ["deploy", "widget"])
        XCTAssertEqual(profile.peakHour, 10)
        XCTAssertEqual(profile.topApp, "App")
        XCTAssertEqual(profile.averageWords, 5)
        XCTAssertEqual(profile.longestWords, 6)
        XCTAssertEqual(VoiceProfile([], calendar: calendar), VoiceProfile())
    }
}

final class SettingsFileTests: XCTestCase {
    func testDefaultsWhenMissing() {
        let file = SettingsFile(url: FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID())/settings.json"))
        XCTAssertTrue(file.bool("cleanup"))
        XCTAssertTrue(file.bool("sounds"))
        XCTAssertFalse(file.bool("incognito"))
    }

    func testSetKeepsOtherKeys() throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID())/settings.json")
        let file = SettingsFile(url: url)
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data(#"{"onboarded": true, "future_key": "x"}"#.utf8).write(to: url)
        try file.set("incognito", true)
        let object = file.read()
        XCTAssertEqual(object["incognito"] as? Bool, true)
        XCTAssertEqual(object["onboarded"] as? Bool, true)
        XCTAssertEqual(object["future_key"] as? String, "x")
    }
}

final class ProfileTests: XCTestCase {
    func testGreetingPrefersNickname() {
        XCTAssertEqual(ProfileInfo(name: "Maxwell Dalrymple", nickname: "Max").greetingName(account: "cyb"), "Max")
    }

    func testGreetingFallsBackToFirstNameThenAccount() {
        XCTAssertEqual(ProfileInfo(name: "Maxwell Dalrymple").greetingName(account: "cyb"), "Maxwell")
        XCTAssertEqual(ProfileInfo(nickname: "   ").greetingName(account: "cyb"), "Cyb")
        XCTAssertEqual(ProfileInfo().greetingName(account: "Jane Doe"), "Jane")
    }

    func testInitials() {
        XCTAssertEqual(ProfileInfo(name: "Maxwell Dalrymple").initials(account: "cyb"), "MD")
        XCTAssertEqual(ProfileInfo(name: "Cher").initials(account: "cyb"), "C")
        XCTAssertEqual(ProfileInfo(nickname: "max").initials(account: "cyb"), "M")
        XCTAssertEqual(ProfileInfo().initials(account: ""), "?")
    }
}


final class PromptDraftTests: XCTestCase {
    let defaults = DefaultPrompts(system: "Default.", examples: "Said: um a\nWrote: A.")

    func testExamplesTextMatchesPython() {
        let pairs = [["um hi", "Hi."], ["a, a b", "A b."]]
        XCTAssertEqual(PromptDraft.format(pairs), "Said: um hi\nWrote: Hi.\n\nSaid: a, a b\nWrote: A b.")
        XCTAssertEqual(PromptDraft.parse(PromptDraft.format(pairs)), pairs)
        XCTAssertEqual(PromptDraft.parse("Said: one\nnoise\nWrote: 1\n\nWrote: orphan\nSaid: dangling"), [["one", "1"]])
    }

    func testMissingFileUsesDefaults() {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID())/prompts.json")
        XCTAssertEqual(PromptDraft.load(from: url, defaults: defaults), PromptDraft(system: "Default.", examples: "Said: um a\nWrote: A."))
    }

    func testRoundTrip() throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID())/prompts.json")
        let draft = PromptDraft(system: "Mine.", extra: "No emoji.", examples: "Said: x\nWrote: X.", guardOn: false)
        try draft.save(to: url)
        XCTAssertEqual(PromptDraft.load(from: url, defaults: defaults), draft)
        let object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any]
        XCTAssertEqual(object?["examples"] as? [[String]], [["x", "X."]])  // the engine's format
    }

    func testBlankSystemFallsBack() throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID())/prompts.json")
        try PromptDraft(system: "", examples: "").save(to: url)
        XCTAssertEqual(PromptDraft.load(from: url, defaults: defaults).system, "Default.")
    }
}

final class MoreInsightsTests: XCTestCase {
    let calendar: Calendar = {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "America/New_York")!
        c.firstWeekday = 1
        return c
    }()

    func at(_ day: Int, _ hour: Int = 10) -> Date {
        calendar.date(from: DateComponents(year: 2026, month: 9, day: day, hour: hour))!
    }

    func rec(_ day: Int, hour: Int = 10, words: Int = 10, seconds: Double = 6, raw: String? = nil,
             text: String = "hello world", app: String = "Notes", status: Recording.Status = .pasted) -> Recording {
        Recording(id: UUID().uuidString, startedAt: at(day, hour), endedAt: at(day, hour), durationS: seconds, status: status,
                  transcript: text, rawTranscript: raw, words: words, pastedInto: AppRef(app: app, bundleId: "x." + app))
    }

    func testTimeSaved() {
        // 400 words take 10 min to type; 2 min spoken -> 8 min saved
        let i = MoreInsights([rec(30, words: 400, seconds: 120)], now: at(30), calendar: calendar)
        XCTAssertEqual(i.minutesSaved, 8)
    }

    func testWeekOverWeek() {
        // Sep 30 2026 is a Wednesday; the week starts Sunday Sep 27.
        let i = MoreInsights([rec(28, words: 30), rec(22, words: 20), rec(10, words: 99)], now: at(30), calendar: calendar)
        XCTAssertEqual(i.thisWeekWords, 30)
        XCTAssertEqual(i.lastWeekWords, 20)
        XCTAssertEqual(i.weekChange, 50)
        XCTAssertNil(MoreInsights([rec(28)], now: at(30), calendar: calendar).weekChange)
    }

    func testFillersRemovedOnlyCountsWhatCleanupTookOut() {
        let i = MoreInsights([
            rec(30, raw: "Um, I, uh, like it, um.", text: "I like it."),       // 2 um + 1 uh; "like" kept
            rec(30, raw: "Basically done.", text: "Done."),
        ], now: at(30), calendar: calendar)
        XCTAssertEqual(i.fillersRemoved, 4)
        XCTAssertEqual(i.topFillers, ["um", "basically", "uh"])
    }

    func testUniqueWordsHoursAndApps() {
        let i = MoreInsights([rec(30, hour: 9, words: 50, text: "Ship it. Ship it now.", app: "Slack"),
                              rec(30, hour: 9, words: 5, text: "Now!", app: "Notes"),
                              rec(30, hour: 22, words: 70, app: "Slack")], now: at(30), calendar: calendar)
        XCTAssertEqual(i.uniqueWords, 5)  // ship, it, now, hello, world
        XCTAssertEqual(i.byHour[9], 2)
        XCTAssertEqual(i.byHour[22], 1)
        XCTAssertEqual(i.topApps, [.init(app: "Slack", words: 120), .init(app: "Notes", words: 5)])
    }

    func testDailyPace() {
        let i = MoreInsights([rec(29, words: 30, seconds: 30), rec(30, words: 10, seconds: 6)], now: at(30), calendar: calendar)
        XCTAssertEqual(i.dailyPace.map(\.wpm), [60, 100])
    }

    func testPersona() {
        XCTAssertEqual(MoreInsights([rec(30)], now: at(30), calendar: calendar).persona, .newcomer)
        let owls = (0..<5).map { _ in rec(30, hour: 23) }
        XCTAssertEqual(MoreInsights(owls, now: at(30), calendar: calendar).persona, .nightOwl)
        let birds = (0..<5).map { _ in rec(30, hour: 6) }
        XCTAssertEqual(MoreInsights(birds, now: at(30), calendar: calendar).persona, .earlyBird)
        let talkers = (0..<5).map { _ in rec(30, hour: 23, words: 100) }
        XCTAssertEqual(MoreInsights(talkers, now: at(30), calendar: calendar).persona, .marathoner)
        XCTAssertEqual(MoreInsights((0..<5).map { _ in rec(30, hour: 14) }, now: at(30), calendar: calendar).persona, .nineToFiver)
    }

    func testEquivalents() {
        XCTAssertEqual(MoreInsights.equivalent(words: 40), "about 1 tweet")
        XCTAssertEqual(MoreInsights.equivalent(words: 120), "about 3 tweets")
        XCTAssertEqual(MoreInsights.equivalent(words: 1_813), "about 6 pages of a book")
        XCTAssertEqual(MoreInsights.equivalent(words: 12_000), "about 3 chapters of a novel")
        XCTAssertEqual(MoreInsights.equivalent(words: 120_000), "about 1.5 novels")
    }

    func testEmpty() {
        XCTAssertEqual(MoreInsights([], now: at(30), calendar: calendar), MoreInsights())
    }
}


final class FunFactsTests: XCTestCase {
    let calendar: Calendar = {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "America/New_York")!
        return c
    }()

    func rec(_ day: Int, words: Int, seconds: Double, text: String, raw: String? = nil) -> Recording {
        let date = calendar.date(from: DateComponents(year: 2026, month: 9, day: day, hour: 10))!
        return Recording(id: UUID().uuidString, startedAt: date, endedAt: date, durationS: seconds, status: .pasted,
                         transcript: text, rawTranscript: raw, words: words)
    }

    func testFunFacts() {
        let records = [
            rec(30, words: 12, seconds: 6, text: "Can you ship the build today? Thanks, ship the build!"),
            rec(30, words: 10, seconds: 10, text: "Please ship the build now?", raw: "Ship it, no wait, please ship the build now?"),
            rec(29, words: 40, seconds: 30, text: "A long one about nothing much at all."),
        ]
        let i = MoreInsights(records, now: records[0].startedAt, calendar: calendar)
        XCTAssertEqual(i.keystrokesSaved, records.reduce(0) { $0 + $1.transcript.count })
        XCTAssertEqual(i.talkSeconds, 46)
        XCTAssertEqual(i.byWeekday[3], 22)  // Wednesday Sep 30
        XCTAssertEqual(i.byWeekday[2], 40)  // Tuesday Sep 29
        XCTAssertEqual(i.biggestDay?.words, 40)
        XCTAssertEqual(i.fastest?.wpm, 120)  // 12 words in 6 s
        XCTAssertEqual(i.longest?.words, 40)
        XCTAssertEqual(i.catchphrase, "ship the build")
        XCTAssertEqual(i.questions, 2)
        XCTAssertEqual(i.politeness, 2)
        XCTAssertEqual(i.selfCorrections, 1)
    }

    func testShortDictationsDontCountAsFastest() {
        let i = MoreInsights([rec(30, words: 3, seconds: 0.5, text: "Yes do it.")], now: Date(), calendar: calendar)
        XCTAssertNil(i.fastest)
        XCTAssertNil(i.catchphrase)
    }
}
