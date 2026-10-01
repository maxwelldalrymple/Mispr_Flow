import Foundation

/// One recorded meeting: the JSON the notetaker writes to meeting-recordings/<day>/.
public struct Meeting: Codable, Identifiable, Hashable {
    public struct Participant: Codable, Hashable {
        public var name: String
        public var role: String?
        public var isMe: Bool?

        enum CodingKeys: String, CodingKey { case name, role, isMe = "is_me" }

        public init(name: String, role: String? = nil, isMe: Bool? = nil) {
            self.name = name
            self.role = role
            self.isMe = isMe
        }
    }

    public struct Line: Codable, Hashable {
        public var speaker: String
        public var startS: Double
        public var text: String

        enum CodingKeys: String, CodingKey { case speaker, text, startS = "start_s" }

        public init(speaker: String, startS: Double, text: String) {
            self.speaker = speaker
            self.startS = startS
            self.text = text
        }
    }

    public struct ActionItem: Codable, Hashable {
        public var owner: String
        public var task: String
        public var due: String?

        public init(owner: String, task: String, due: String?) {
            self.owner = owner
            self.task = task
            self.due = due
        }
    }

    public struct Summary: Codable, Hashable {
        public var overview: String
        public var decisions: [String]
        public var actionItems: [ActionItem]
        public var openQuestions: [String]

        enum CodingKeys: String, CodingKey {
            case overview, decisions
            case actionItems = "action_items"
            case openQuestions = "open_questions"
        }

        public init(overview: String, decisions: [String], actionItems: [ActionItem], openQuestions: [String]) {
            self.overview = overview
            self.decisions = decisions
            self.actionItems = actionItems
            self.openQuestions = openQuestions
        }

        /// From the engine's summary event.
        public init?(json: Any?) {
            guard let d = json as? [String: Any] else { return nil }
            overview = d["overview"] as? String ?? ""
            decisions = d["decisions"] as? [String] ?? []
            openQuestions = d["open_questions"] as? [String] ?? []
            actionItems = (d["action_items"] as? [[String: Any]] ?? []).compactMap { item in
                guard let task = item["task"] as? String else { return nil }
                let due = (item["due"] as? String).flatMap { $0.isEmpty ? nil : $0 }
                return ActionItem(owner: item["owner"] as? String ?? "You", task: task, due: due)
            }
        }
    }

    public var id: String
    public var title: String
    public var sample: Bool?
    public var startedAt: Date
    public var endedAt: Date
    public var durationS: Double
    public var app: String?
    public var participants: [Participant]
    public var transcript: [Line]
    public var summary: Summary?
    public var myThoughts: String?
    public var fileURL: URL?

    enum CodingKeys: String, CodingKey {
        case id, title, sample, app, participants, transcript, summary
        case startedAt = "started_at"
        case endedAt = "ended_at"
        case durationS = "duration_s"
        case myThoughts = "my_thoughts"
    }

    public init(id: String, title: String, startedAt: Date, durationS: Double, app: String? = nil,
                participants: [Participant], transcript: [Line], summary: Summary? = nil, myThoughts: String? = nil) {
        self.id = id
        self.title = title
        self.startedAt = startedAt
        self.endedAt = startedAt.addingTimeInterval(durationS)
        self.durationS = durationS
        self.app = app
        self.participants = participants
        self.transcript = transcript
        self.summary = summary
        self.myThoughts = myThoughts
    }

    /// "12 min", "1 h 5 min".
    public var durationText: String {
        let minutes = Int((durationS / 60).rounded())
        return minutes >= 60 ? "\(minutes / 60) h \(minutes % 60) min" : "\(max(minutes, 1)) min"
    }
}

public enum MeetingStore {
    /// Every meeting under `dir` (one folder per day), newest first.
    public static func load(from dir: URL, fileManager: FileManager = .default) -> [Meeting] {
        guard let days = try? fileManager.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil) else { return [] }
        let decoder = RecordingStore.makeDecoder()
        var meetings: [Meeting] = []
        for day in days where day.hasDirectoryPath {
            for file in (try? fileManager.contentsOfDirectory(at: day, includingPropertiesForKeys: nil)) ?? []
            where file.pathExtension == "json" {
                guard let data = try? Data(contentsOf: file), var meeting = try? decoder.decode(Meeting.self, from: data) else { continue }
                meeting.fileURL = file
                meetings.append(meeting)
            }
        }
        return meetings.sorted { $0.startedAt > $1.startedAt }
    }
}

/// Who talked how much in one meeting, and its shape.
public struct MeetingInsights: Equatable {
    public struct Speaker: Equatable, Identifiable {
        public var name: String
        public var seconds: Double
        public var words: Int
        public var turns: Int
        public var questions: Int
        public var share: Int  // % of talk time
        public var id: String { name }
        public var wpm: Int { seconds > 0 ? Int((Double(words) / seconds * 60).rounded()) : 0 }
    }

    public var speakers: [Speaker] = []
    public var longestMonologue: (speaker: String, seconds: Double)?
    public var turnsPerMinute = 0.0
    public var topics: [String] = []
    public var questions = 0

    public static func == (a: MeetingInsights, b: MeetingInsights) -> Bool {
        a.speakers == b.speakers && a.longestMonologue?.speaker == b.longestMonologue?.speaker
            && a.longestMonologue?.seconds == b.longestMonologue?.seconds && a.turnsPerMinute == b.turnsPerMinute
            && a.topics == b.topics && a.questions == b.questions
    }

    public init() {}

    /// A line lasts until the next one starts (the last one until the meeting ends).
    public init(_ meeting: Meeting) {
        let lines = meeting.transcript.sorted { $0.startS < $1.startS }
        guard !lines.isEmpty else { return }
        var seconds: [String: Double] = [:], words: [String: Int] = [:], turns: [String: Int] = [:], asks: [String: Int] = [:]
        var previous: String?
        var run = (speaker: "", seconds: 0.0)
        for (i, line) in lines.enumerated() {
            let end = i + 1 < lines.count ? lines[i + 1].startS : meeting.durationS
            let duration = max(0, end - line.startS)
            seconds[line.speaker, default: 0] += duration
            words[line.speaker, default: 0] += line.text.split(separator: " ").count
            asks[line.speaker, default: 0] += line.text.filter { $0 == "?" }.count
            if line.speaker != previous { turns[line.speaker, default: 0] += 1 }
            run = line.speaker == previous ? (line.speaker, run.seconds + duration) : (line.speaker, duration)
            if run.seconds > (longestMonologue?.seconds ?? 0) { longestMonologue = run }
            previous = line.speaker
        }
        let total = seconds.values.reduce(0, +)
        speakers = seconds.keys.map { name in
            Speaker(name: name, seconds: seconds[name]!, words: words[name] ?? 0, turns: turns[name] ?? 0,
                    questions: asks[name] ?? 0, share: total > 0 ? Int((seconds[name]! * 100 / total).rounded()) : 0)
        }
        .sorted { $0.seconds != $1.seconds ? $0.seconds > $1.seconds : $0.name < $1.name }
        turnsPerMinute = meeting.durationS > 0 ? (Double(turns.values.reduce(0, +)) / (meeting.durationS / 60) * 10).rounded() / 10 : 0
        questions = asks.values.reduce(0, +)
        var counts: [String: Int] = [:]
        for line in lines {
            for word in MoreInsights.tokens(line.text) where word.count > 3 && !VoiceProfile.stopwords.contains(word) {
                counts[word, default: 0] += 1
            }
        }
        topics = counts.filter { $0.value >= 2 }
            .sorted { $0.value != $1.value ? $0.value > $1.value : $0.key < $1.key }.prefix(6).map(\.key)
    }
}

/// Across all meetings: time spent, who you meet with, and how much you talk.
public struct MeetingsOverview: Equatable {
    public var count = 0
    public var totalSeconds = 0.0
    public var averageSeconds = 0.0
    public var people: [(name: String, meetings: Int)] = []
    public var myShare: Int?        // average % of talk time that was you
    public var openActionItems = 0
    public var busiestWeekday: Int?  // 1 = Sunday

    public static func == (a: MeetingsOverview, b: MeetingsOverview) -> Bool {
        a.count == b.count && a.totalSeconds == b.totalSeconds && a.averageSeconds == b.averageSeconds
            && a.people.map(\.name) == b.people.map(\.name) && a.people.map(\.meetings) == b.people.map(\.meetings)
            && a.myShare == b.myShare && a.openActionItems == b.openActionItems && a.busiestWeekday == b.busiestWeekday
    }

    public init() {}

    public init(_ meetings: [Meeting], calendar: Calendar = .current) {
        guard !meetings.isEmpty else { return }
        count = meetings.count
        totalSeconds = meetings.reduce(0) { $0 + $1.durationS }
        averageSeconds = totalSeconds / Double(count)
        var seen: [String: Int] = [:]
        for m in meetings { for p in m.participants where p.isMe != true { seen[p.name, default: 0] += 1 } }
        people = seen.sorted { $0.value != $1.value ? $0.value > $1.value : $0.key < $1.key }.prefix(6).map { ($0.key, $0.value) }
        let shares = meetings.compactMap { m -> Int? in
            guard let me = m.participants.first(where: { $0.isMe == true })?.name else { return nil }
            return MeetingInsights(m).speakers.first { $0.name == me }?.share ?? 0
        }
        myShare = shares.isEmpty ? nil : shares.reduce(0, +) / shares.count
        openActionItems = meetings.reduce(0) { $0 + ($1.summary?.actionItems.count ?? 0) }
        var days: [Int: Int] = [:]
        for m in meetings { days[calendar.component(.weekday, from: m.startedAt), default: 0] += 1 }
        busiestWeekday = days.max { $0.value != $1.value ? $0.value < $1.value : $0.key > $1.key }?.key
    }
}

/// People across your meetings: who you meet with, and what you share with them.
public enum PeopleIndex {
    public struct Person: Equatable, Identifiable {
        public var name: String
        public var role: String?
        public var meetings: Int
        public var seconds: Double
        public var firstMet: Date
        public var lastMet: Date
        public var id: String { name }
    }

    /// Everyone except you, most-met first (then most recent).
    public static func people(_ meetings: [Meeting]) -> [Person] {
        var byName: [String: Person] = [:]
        for m in meetings.sorted(by: { $0.startedAt < $1.startedAt }) {
            for p in m.participants where p.isMe != true {
                if var person = byName[p.name] {
                    person.meetings += 1
                    person.seconds += m.durationS
                    person.lastMet = m.startedAt
                    person.role = p.role ?? person.role
                    byName[p.name] = person
                } else {
                    byName[p.name] = Person(name: p.name, role: p.role, meetings: 1, seconds: m.durationS,
                                            firstMet: m.startedAt, lastMet: m.startedAt)
                }
            }
        }
        return byName.values.sorted { $0.meetings != $1.meetings ? $0.meetings > $1.meetings : $0.lastMet > $1.lastMet }
    }

    /// Meetings where every one of `names` was present, newest first.
    public static func together(_ meetings: [Meeting], names: Set<String>) -> [Meeting] {
        guard !names.isEmpty else { return [] }
        return meetings.filter { m in names.isSubset(of: Set(m.participants.map(\.name))) }
            .sorted { $0.startedAt > $1.startedAt }
    }

    /// Action items owned by this person (full name or first name), with their meeting.
    public static func actionItems(_ meetings: [Meeting], for name: String) -> [(meeting: Meeting, item: Meeting.ActionItem)] {
        let first = name.split(separator: " ").first.map(String.init)?.lowercased() ?? ""
        return meetings.sorted { $0.startedAt > $1.startedAt }.flatMap { m in
            (m.summary?.actionItems ?? []).filter { item in
                let owner = item.owner.lowercased()
                return owner == name.lowercased() || owner == first
            }.map { (m, $0) }
        }
    }

    /// What a group of people (one or more) looks like across the meetings they shared.
    public struct Group: Equatable {
        public var meetings = 0
        public var seconds = 0.0
        public var talkShare: [String: Int] = [:]   // average % of talk time per person
        public var questions: [String: Int] = [:]   // questions asked per person
        public var topics: [String] = []
        public var lastMet: Date?
        public var averageSeconds: Double { meetings > 0 ? seconds / Double(meetings) : 0 }
    }

    public static func group(_ meetings: [Meeting], names: Set<String>) -> Group {
        let shared = together(meetings, names: names)
        var g = Group()
        g.meetings = shared.count
        g.seconds = shared.reduce(0) { $0 + $1.durationS }
        g.lastMet = shared.first?.startedAt
        var shares: [String: [Int]] = [:]
        var topicCounts: [String: Int] = [:]
        for m in shared {
            let insights = MeetingInsights(m)
            for name in names {
                let speaker = insights.speakers.first { $0.name == name }
                shares[name, default: []].append(speaker?.share ?? 0)
                g.questions[name, default: 0] += speaker?.questions ?? 0
            }
            for (i, topic) in insights.topics.enumerated() { topicCounts[topic, default: 0] += insights.topics.count - i }
        }
        g.talkShare = shares.mapValues { $0.isEmpty ? 0 : $0.reduce(0, +) / $0.count }
        g.topics = topicCounts.sorted { $0.value != $1.value ? $0.value > $1.value : $0.key < $1.key }.prefix(8).map(\.key)
        return g
    }
}
