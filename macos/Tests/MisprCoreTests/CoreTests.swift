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
        XCTAssertEqual(EngineEvent.parse(#"@mispr {"event": "open_note"}"#), .openNote(start: false))
        XCTAssertEqual(EngineEvent.parse(#"@mispr {"event": "open_note", "start": true}"#), .openNote(start: true))
        XCTAssertEqual(EngineEvent.parse(#"@mispr {"event": "chunk_text", "id": "m", "stream": "them", "speaker": 2, "offset": 3.5, "text": "Hi.", "voice": "female"}"#),
                       .chunkText(meeting: "m", stream: "them", speaker: 2, offset: 3.5, text: "Hi.", voice: "female"))
        let summary = EngineEvent.parse(#"@mispr {"event": "summary", "id": "m", "summary": {"title": "Plan", "overview": "O", "decisions": ["D"], "action_items": [{"owner": "You", "task": "T", "due": ""}], "open_questions": []}}"#)
        XCTAssertEqual(summary, .summary(meeting: "m", summary: Meeting.Summary(overview: "O", decisions: ["D"],
                       actionItems: [.init(owner: "You", task: "T", due: nil)], openQuestions: []), title: "Plan"))
        XCTAssertEqual(EngineEvent.parse(#"@mispr {"event": "summary", "id": "m", "summary": null}"#), .summary(meeting: "m", summary: nil, title: ""))
        XCTAssertEqual(EngineEvent.parse(#"@mispr {"event": "meeting", "active": true}"#), .meeting(active: true))
        XCTAssertNil(EngineEvent.parse(#"@mispr {"event": "meeting"}"#))
        XCTAssertEqual(EngineCommand.startMeeting.rawValue, "start_meeting")  // must match mispr/app.py
        XCTAssertEqual(EngineCommand.stopMeeting.rawValue, "stop_meeting")
    }

    func testEngineTracksMeetingAndNoteRequests() {
        let engine = Engine(config: nil)
        var requests = 0
        let sub = engine.noteRequested.sink { _ in requests += 1 }
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


final class DictationKeyTests: XCTestCase {
    func testModifiers() {
        XCTAssertEqual(DictationKey.modifier(keycode: 61), DictationKey(kind: .modifier, keycode: 61, label: "Right ⌥"))
        XCTAssertEqual(DictationKey.modifier(keycode: 63), .fn)
        XCTAssertNil(DictationKey.modifier(keycode: 57))  // caps lock
    }

    func testKeys() {
        XCTAssertEqual(DictationKey.key(keycode: 96, characters: "\u{F708}")?.label, "F5")
        XCTAssertEqual(DictationKey.key(keycode: 50, characters: "`")?.label, "`")
        XCTAssertEqual(DictationKey.key(keycode: 0, characters: "a")?.label, "A")
        XCTAssertTrue(DictationKey.key(keycode: 0, characters: "a")!.typesCharacters)
        XCTAssertFalse(DictationKey.key(keycode: 96, characters: nil)!.typesCharacters)
        for blocked in [49, 36, 51, 53, 57] { XCTAssertNil(DictationKey.key(keycode: blocked, characters: "x"), "\(blocked)") }
    }

    func testSavedInSettings() throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID())/settings.json")
        let file = SettingsFile(url: url)
        XCTAssertEqual(file.dictationKey, .fn)
        try file.set("onboarded", true)
        let f5 = DictationKey(kind: .key, keycode: 96, label: "F5")
        try file.setDictationKey(f5)
        XCTAssertEqual(file.dictationKey, f5)
        XCTAssertEqual(file.read()["onboarded"] as? Bool, true)
        let hotkey = file.read()["hotkey"] as? [String: Any]
        XCTAssertEqual(hotkey?["kind"] as? String, "key")  // the engine's format
        XCTAssertEqual(hotkey?["keycode"] as? Int, 96)
    }
}


final class VoiceStyleTests: XCTestCase {
    func rec(_ text: String, words: Int, seconds: Double = 6) -> Recording {
        Recording(id: UUID().uuidString, startedAt: Date(), endedAt: Date(), durationS: seconds, status: .pasted,
                  transcript: text, words: words)
    }

    func testStyleSignals() {
        let p = VoiceProfile([
            rec("So I'm shipping the widget today. It's done!", words: 8),
            rec("So can we ship the widget tomorrow?", words: 7),
            rec("Okay. Ship it.", words: 3),
            rec("Widget review at noon.", words: 4),
        ])
        XCTAssertEqual(p.openers, ["so"])
        XCTAssertEqual(p.wordCloud.first?.word, "widget")
        XCTAssertEqual(p.wordCloud.first?.count, 3)
        XCTAssertEqual(p.contractionRate, 25)
        XCTAssertEqual(p.exclamationRate, 25)
        XCTAssertEqual(p.questionRate, 25)
        XCTAssertEqual(p.wordsPerSentence, 4)  // 22 words / 6 sentences
        XCTAssertEqual(p.pace, 55)             // 22 words in 24 s
        XCTAssertEqual(p.style, .deliberate)
        XCTAssertEqual(p.tone, "Balanced")
        XCTAssertGreaterThan(p.richness, 50)
    }

    func testStyleThresholds() {
        var p = VoiceProfile()
        p.pace = 160; XCTAssertEqual(p.style, .fast)
        p.pace = 120; XCTAssertEqual(p.style, .steady)
        p.contractionRate = 50; XCTAssertEqual(p.tone, "Casual")
        p.contractionRate = 5; XCTAssertEqual(p.tone, "Formal")
    }
}

final class MeetingTests: XCTestCase {
    let me = Meeting.Participant(name: "Max", isMe: true)

    func meeting(_ lines: [(String, Double, String)], duration: Double = 60, people: [String] = ["Max", "Ana"]) -> Meeting {
        Meeting(id: UUID().uuidString, title: "T", startedAt: Date(timeIntervalSince1970: 1_790_000_000), durationS: duration,
                participants: people.map { Meeting.Participant(name: $0, isMe: $0 == "Max") },
                transcript: lines.map { Meeting.Line(speaker: $0.0, startS: $0.1, text: $0.2) })
    }

    func testTalkTimeTurnsAndMonologue() {
        let m = meeting([("Max", 0, "Hello there everyone"), ("Ana", 10, "Hi. Shall we start the release review?"),
                         ("Max", 20, "Yes, release review first."), ("Max", 40, "Then the release dates.")])
        let i = MeetingInsights(m)
        XCTAssertEqual(i.speakers.map(\.name), ["Max", "Ana"])
        XCTAssertEqual(i.speakers[0].seconds, 50)   // 0-10 and 20-60
        XCTAssertEqual(i.speakers[0].share, 83)
        XCTAssertEqual(i.speakers[0].turns, 2)
        XCTAssertEqual(i.speakers[1].questions, 1)
        XCTAssertEqual(i.longestMonologue?.speaker, "Max")
        XCTAssertEqual(i.longestMonologue?.seconds, 40)  // 20 s + 20 s back to back
        XCTAssertEqual(i.turnsPerMinute, 3)
        XCTAssertEqual(i.topics.first, "release")
    }

    func testEmptyTranscript() {
        XCTAssertEqual(MeetingInsights(meeting([])), MeetingInsights())
    }

    func testOverview() {
        let a = meeting([("Max", 0, "a"), ("Ana", 30, "b")], duration: 600, people: ["Max", "Ana"])
        let b = meeting([("Max", 0, "a"), ("Bo", 15, "b")], duration: 300, people: ["Max", "Ana", "Bo"])
        let o = MeetingsOverview([a, b])
        XCTAssertEqual(o.count, 2)
        XCTAssertEqual(o.totalSeconds, 900)
        XCTAssertEqual(o.averageSeconds, 450)
        XCTAssertEqual(o.people.map(\.name), ["Ana", "Bo"])
        XCTAssertEqual(o.people.first?.meetings, 2)
        XCTAssertEqual(o.myShare, (5 + 5) / 2)  // 30/600 and 15/300
        XCTAssertEqual(MeetingsOverview([]), MeetingsOverview())
    }

    func testDurationText() {
        XCTAssertEqual(meeting([], duration: 690).durationText, "12 min")
        XCTAssertEqual(meeting([], duration: 3900).durationText, "1 h 5 min")
        XCTAssertEqual(meeting([], duration: 10).durationText, "1 min")
    }

    func testLoadsTheSampleFormat() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: dir.appendingPathComponent("2026-09-29"), withIntermediateDirectories: true)
        let json = """
        {"id": "x", "sample": true, "title": "Weekly sync", "started_at": "2026-09-29T10:00:00.000-04:00",
         "ended_at": "2026-09-29T10:11:30.000-04:00", "duration_s": 690.0, "app": "Zoom",
         "participants": [{"name": "Max", "role": "Founder", "is_me": true}, {"name": "Priya Shah", "role": "Design", "is_me": false}],
         "transcript": [{"speaker": "Max", "start_s": 2.0, "text": "Morning."}],
         "summary": {"overview": "O", "decisions": ["D"], "action_items": [{"owner": "Max", "task": "T", "due": "Fri"}], "open_questions": []},
         "my_thoughts": "", "audio_file": null}
        """
        try Data(json.utf8).write(to: dir.appendingPathComponent("2026-09-29/x.json"))
        let meetings = MeetingStore.load(from: dir)
        XCTAssertEqual(meetings.count, 1)
        XCTAssertEqual(meetings[0].participants[1].role, "Design")
        XCTAssertEqual(meetings[0].summary?.actionItems.first?.due, "Fri")
        XCTAssertEqual(meetings[0].durationText, "12 min")
    }
}

final class MeetingDetectorTests: XCTestCase {
    typealias W = SystemSnapshot.WindowTitle

    func detect(_ s: SystemSnapshot) -> MeetingSource { MeetingDetector.detect(s).source }

    func testZoomAppInAMeeting() {
        XCTAssertEqual(detect(.init(runningBundleIDs: ["us.zoom.xos"], processNames: ["CptHost"])), .zoom)
        XCTAssertEqual(detect(.init(windowTitles: [W("us.zoom.xos", "Zoom Meeting")])), .zoom)
    }

    func testZoomOpenButNotInACallIsInPerson() {
        XCTAssertEqual(detect(.init(runningBundleIDs: ["us.zoom.xos"], windowTitles: [W("us.zoom.xos", "Zoom Workplace")])), .inPerson)
    }

    func testGoogleMeetTabWithName() {
        let d = MeetingDetector.detect(.init(windowTitles: [W("com.google.Chrome", "Meet – Weekly product sync - Google Chrome")]))
        XCTAssertEqual(d.source, .googleMeet)
        XCTAssertEqual(d.title, "Weekly product sync")
        XCTAssertEqual(d.window, W("com.google.Chrome", "Meet – Weekly product sync - Google Chrome"))  // for Split screen
        XCTAssertNil(MeetingDetector.detect(.init()).window)
    }

    func testMeetCodeIsNotAName() {
        let d = MeetingDetector.detect(.init(windowTitles: [W("com.apple.Safari", "Meet - abc-defg-hij")]))
        XCTAssertEqual(d.source, .googleMeet)
        XCTAssertEqual(d.title, "")
    }

    func testBrowserCallsNeedTheMic() {
        let teams = W("com.google.Chrome", "Chat | Microsoft Teams")
        XCTAssertEqual(detect(.init(windowTitles: [teams], micInUse: true)), .teams)
        XCTAssertEqual(detect(.init(windowTitles: [teams], micInUse: false)), .inPerson)  // just reading chat
    }

    func testCallAppsNeedTheMic() {
        XCTAssertEqual(detect(.init(runningBundleIDs: ["com.apple.FaceTime"], micInUse: true)), .facetime)
        XCTAssertEqual(detect(.init(runningBundleIDs: ["com.apple.FaceTime"], micInUse: false)), .inPerson)
        XCTAssertEqual(detect(.init(runningBundleIDs: ["com.microsoft.teams2"], micInUse: true)), .teams)
        XCTAssertEqual(detect(.init(runningBundleIDs: ["us.zoom.xos"], micInUse: true)), .zoom)
    }

    func testSlackHuddle() {
        XCTAssertEqual(detect(.init(windowTitles: [W("com.tinyspeck.slackmacgap", "Huddle with Priya")])), .slack)
    }

    func testZoomBeatsAnIdleMeetTab() {
        let s = SystemSnapshot(processNames: ["CptHost"], windowTitles: [W("com.google.Chrome", "Meet – Old call")])
        XCTAssertEqual(detect(s), .zoom)
    }

    func testUnknownMicUserIsACall() {
        let d = MeetingDetector.detect(.init(runningBundleIDs: ["com.google.Chrome"], micInUse: true))
        XCTAssertEqual(d.source, .otherCall)
        XCTAssertTrue(d.source.needsSystemAudio)
    }

    func testNothingIsInPerson() {
        let d = MeetingDetector.detect(.init())
        XCTAssertEqual(d.source, .inPerson)
        XCTAssertFalse(d.source.needsSystemAudio)
        XCTAssertTrue(MeetingSource.zoom.needsSystemAudio)
    }
}

final class LiveMeetingTests: XCTestCase {
    func voice(_ seconds: Double) -> [Float] { (0..<Int(seconds * 16_000)).map { Float(sin(Double($0) * 0.2)) * 0.3 } }
    func quiet(_ seconds: Double) -> [Float] { Array(repeating: 0.0005, count: Int(seconds * 16_000)) }

    func testCutsAtAPause() {
        var s = Segmenter()
        let chunks = s.feed(voice(2) + quiet(1) + voice(1.5))
        XCTAssertEqual(chunks.count, 1)
        XCTAssertEqual(chunks[0].start, 0)
        XCTAssertEqual(Double(chunks[0].samples.count) / 16_000, 2.7, accuracy: 0.05)  // speech + the 0.7 s pause
        let rest = s.flush()
        XCTAssertNotNil(rest)
        XCTAssertEqual(rest!.start, 2.7, accuracy: 0.05)
    }

    func testLongSpeechIsCutAtMax() {
        var s = Segmenter()
        XCTAssertEqual(s.feed(voice(31)).count, 2)
    }

    func testSilenceProducesNothing() {
        var s = Segmenter()
        XCTAssertTrue(s.feed(quiet(10)).isEmpty)
        XCTAssertNil(s.flush())
    }

    func testFeedInSmallPieces() {
        var s = Segmenter()
        var chunks: [(start: Double, samples: [Float])] = []
        let audio = voice(2) + quiet(1)
        for i in stride(from: 0, to: audio.count, by: 1024) { chunks += s.feed(Array(audio[i..<min(i + 1024, audio.count)])) }
        XCTAssertEqual(chunks.count, 1)
    }

    func testWAVHeader() {
        let d = WAV.data([0, 1, -1])
        XCTAssertEqual(d.count, 44 + 6)
        XCTAssertEqual(String(decoding: d.prefix(4), as: UTF8.self), "RIFF")
        XCTAssertEqual(d[22], 1)          // mono
        XCTAssertEqual(d[34], 16)         // bits
        XCTAssertEqual(d[46], 0xFF); XCTAssertEqual(d[47], 0x7F)  // +1.0 -> 32767
    }

    func testTranscriptOrderLabelsAndGroups() {
        var t = LiveTranscript()
        t.add(stream: "them", speaker: 1, offset: 5, text: "Second.")
        t.add(stream: "you", speaker: 0, offset: 1, text: "First.")
        t.add(stream: "them", speaker: 1, offset: 8, text: "Third.")
        t.add(stream: "you", speaker: 0, offset: 9, text: "  ")
        XCTAssertEqual(t.lines.map(\.text), ["First.", "Second.", "Third."])
        XCTAssertEqual(t.groups.map(\.label), ["You", "Person 1"])
        XCTAssertEqual(t.groups[1].lines.count, 2)
        t.add(stream: "them", speaker: 2, offset: 12, text: "Fourth.", voice: "female")
        t.add(stream: "them", speaker: 3, offset: 14, text: "Fifth.", voice: "female")
        t.add(stream: "them", speaker: 4, offset: 16, text: "Sixth.", voice: "male")
        XCTAssertEqual(t.groups.map(\.label), ["You", "Person 1", "Female 1", "Female 2", "Male 1"])
        t.names[2] = "Priya"
        XCTAssertEqual(t.groups[2].label, "Priya")
        XCTAssertEqual(t.engineLines[3], ["speaker": "Priya", "text": "Fourth."])
    }

    func testSavesAsAMeetingTheNotesPageCanRead() throws {
        var t = LiveTranscript()
        t.add(stream: "you", speaker: 0, offset: 0, text: "Hello.")
        t.add(stream: "them", speaker: 1, offset: 2, text: "Hi!")
        let start = Date(timeIntervalSince1970: 1_790_800_000)
        let meeting = t.meeting(id: Meeting.newID(start), title: "", startedAt: start, duration: 65, source: "Zoom",
                                thoughts: "note", summary: nil)
        XCTAssertEqual(meeting.title, "Meeting")
        XCTAssertEqual(meeting.participants.map(\.name), ["You", "Person 1"])
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try meeting.save(in: dir)
        let loaded = MeetingStore.load(from: dir)
        XCTAssertEqual(loaded.count, 1)
        XCTAssertEqual(loaded[0].transcript.map(\.text), ["Hello.", "Hi!"])
        XCTAssertEqual(loaded[0].app, "Zoom")
        XCTAssertEqual(loaded[0].startedAt.timeIntervalSince1970, start.timeIntervalSince1970, accuracy: 0.01)
    }
}

final class PeopleIndexTests: XCTestCase {
    func meeting(_ day: Double, _ people: [String], minutes: Double = 10, lines: [(String, Double, String)] = [],
                 items: [(String, String)] = []) -> Meeting {
        var m = Meeting(id: UUID().uuidString, title: "M\(day)", startedAt: Date(timeIntervalSince1970: 1_790_000_000 + day * 86_400),
                        durationS: minutes * 60,
                        participants: [Meeting.Participant(name: "Max", isMe: true)] + people.map { Meeting.Participant(name: $0, role: "R") },
                        transcript: lines.map { Meeting.Line(speaker: $0.0, startS: $0.1, text: $0.2) })
        if !items.isEmpty {
            m.summary = Meeting.Summary(overview: "", decisions: [], actionItems: items.map { .init(owner: $0.0, task: $0.1, due: nil) },
                                        openQuestions: [])
        }
        return m
    }

    func testPeopleAreCountedAndSorted() {
        let ms = [meeting(1, ["Priya Shah", "Jordan Lee"]), meeting(2, ["Priya Shah"], minutes: 20), meeting(3, ["Rachel Kim"])]
        let people = PeopleIndex.people(ms)
        XCTAssertEqual(people.map(\.name), ["Priya Shah", "Rachel Kim", "Jordan Lee"])  // most meetings, then most recent
        XCTAssertEqual(people[0].meetings, 2)
        XCTAssertEqual(people[0].seconds, 1800)
        XCTAssertEqual(people[0].firstMet, ms[0].startedAt)
        XCTAssertEqual(people[0].lastMet, ms[1].startedAt)
        XCTAssertFalse(people.contains { $0.name == "Max" })  // not you
    }

    func testTogetherNeedsEveryoneSelected() {
        let ms = [meeting(1, ["Priya Shah", "Jordan Lee"]), meeting(2, ["Priya Shah"]), meeting(3, ["Jordan Lee", "Priya Shah", "Sam"])]
        XCTAssertEqual(PeopleIndex.together(ms, names: ["Priya Shah"]).count, 3)
        XCTAssertEqual(PeopleIndex.together(ms, names: ["Priya Shah", "Jordan Lee"]).map(\.title), ["M3.0", "M1.0"])
        XCTAssertEqual(PeopleIndex.together(ms, names: []), [])
    }

    func testActionItemsMatchFullOrFirstName() {
        let ms = [meeting(1, ["Jordan Lee"], items: [("Jordan Lee", "Test installer"), ("Max", "Notes")]),
                  meeting(2, ["Jordan Lee"], items: [("jordan", "Fix undo")])]
        XCTAssertEqual(PeopleIndex.actionItems(ms, for: "Jordan Lee").map(\.item.task), ["Fix undo", "Test installer"])
    }

    func testGroupStats() {
        let ms = [meeting(1, ["Ana", "Bo"], lines: [("Ana", 0, "Release plan?"), ("Bo", 300, "Release friday release")]),
                  meeting(2, ["Ana"], minutes: 30)]
        let g = PeopleIndex.group(ms, names: ["Ana", "Bo"])
        XCTAssertEqual(g.meetings, 1)
        XCTAssertEqual(g.seconds, 600)
        XCTAssertEqual(g.talkShare["Ana"], 50)
        XCTAssertEqual(g.questions["Ana"], 1)
        XCTAssertEqual(g.topics.first, "release")
        XCTAssertEqual(PeopleIndex.group(ms, names: ["Ana"]).meetings, 2)
        XCTAssertEqual(PeopleIndex.group(ms, names: ["Nobody"]).meetings, 0)
    }
}
