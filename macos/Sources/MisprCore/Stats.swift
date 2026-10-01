import Foundation

/// What kind of writing a dictation went into, from the app (and page) it was pasted into.
public enum UsageCategory: String, CaseIterable, Identifiable {
    case aiPrompts = "AI prompts"
    case emails = "Emails"
    case workMessages = "Work messages"
    case personalMessages = "Personal messages"
    case documents = "Documents"
    case coding = "Coding"
    case other = "Other tasks"

    public var id: String { rawValue }

    static let bundles: [UsageCategory: Set<String>] = [
        .aiPrompts: ["com.anthropic.claudefordesktop", "com.openai.chat", "com.google.GeminiMacOS", "ai.perplexity.mac"],
        .emails: ["com.apple.mail", "com.microsoft.Outlook", "com.readdle.smartemail-Mac", "com.superhuman.electron", "com.google.Gmail"],
        .workMessages: ["com.tinyspeck.slackmacgap", "com.microsoft.teams2", "com.microsoft.teams", "us.zoom.xos", "com.linear"],
        .personalMessages: ["com.apple.MobileSMS", "net.whatsapp.WhatsApp", "ru.keepcoder.Telegram", "com.hnc.Discord", "org.whispersystems.signal-desktop", "com.facebook.archon"],
        .documents: ["notion.id", "com.microsoft.Word", "com.apple.iWork.Pages", "com.apple.TextEdit", "md.obsidian", "com.apple.Notes"],
        .coding: ["com.microsoft.VSCode", "com.todesktop.230313mzl4w4u92", "com.exafunction.windsurf", "com.apple.dt.Xcode", "com.apple.Terminal", "com.googlecode.iterm2", "dev.warp.Warp-Stable"],
    ]

    static let hosts: [UsageCategory: [String]] = [
        .aiPrompts: ["claude.ai", "chatgpt.com", "chat.openai.com", "gemini.google.com", "perplexity.ai"],
        .emails: ["mail.google.com", "outlook.live.com", "outlook.office.com"],
        .workMessages: ["app.slack.com", "teams.microsoft.com", "linear.app"],
        .personalMessages: ["web.whatsapp.com", "web.telegram.org", "discord.com", "messenger.com", "instagram.com"],
        .documents: ["docs.google.com", "notion.so"],
        .coding: ["github.com"],
    ]

    public static func of(_ app: AppRef?) -> UsageCategory {
        if let url = app?.url, let host = URL(string: url)?.host?.lowercased() {
            for (category, suffixes) in hosts where suffixes.contains(where: { host == $0 || host.hasSuffix("." + $0) }) {
                return category
            }
        }
        if let bundle = app?.bundleId {
            for (category, ids) in bundles where ids.contains(bundle) { return category }
        }
        return .other
    }
}

/// Usage numbers for Home and Insights, computed from saved dictations (all local).
public struct Stats: Equatable {
    public var totalWords = 0
    public var dictations = 0
    public var wordsPerMinute = 0
    public var cleaned = 0
    public var currentStreak = 0
    public var longestStreak = 0
    public var appsUsed = 0
    public var perDay: [Date: Int] = [:]  // start of day -> dictations
    public var categories: [(category: UsageCategory, count: Int)] = []

    /// A typical typing speed, for the "faster than typing" comparison.
    public static let typingWPM = 40.0

    public static func == (a: Stats, b: Stats) -> Bool {
        a.totalWords == b.totalWords && a.dictations == b.dictations && a.wordsPerMinute == b.wordsPerMinute
            && a.cleaned == b.cleaned && a.currentStreak == b.currentStreak && a.longestStreak == b.longestStreak
            && a.appsUsed == b.appsUsed && a.perDay == b.perDay
            && a.categories.map(\.category) == b.categories.map(\.category) && a.categories.map(\.count) == b.categories.map(\.count)
    }

    public init() {}

    /// Only dictations whose words were delivered (pasted or copied) count; cancelled ones don't.
    public init(_ records: [Recording], now: Date = Date(), calendar: Calendar = .current) {
        let used = records.filter { $0.status != .cancelled && $0.words > 0 }
        dictations = used.count
        totalWords = used.reduce(0) { $0 + $1.words }
        let minutes = used.reduce(0.0) { $0 + $1.durationS } / 60
        wordsPerMinute = minutes > 0 ? Int((Double(totalWords) / minutes).rounded()) : 0
        cleaned = used.filter(\.wasCleaned).count
        appsUsed = Set(used.compactMap { $0.app?.bundleId }).count

        for record in used {
            perDay[calendar.startOfDay(for: record.startedAt), default: 0] += 1
        }
        (currentStreak, longestStreak) = Self.streaks(days: Set(perDay.keys), now: now, calendar: calendar)

        var counts: [UsageCategory: Int] = [:]
        for record in used { counts[UsageCategory.of(record.app), default: 0] += 1 }
        categories = UsageCategory.allCases.map { ($0, counts[$0] ?? 0) }
            .sorted { $0.count != $1.count ? $0.count > $1.count : $0.category.rawValue < $1.category.rawValue }
    }

    /// Current streak: consecutive days with a dictation ending today, or yesterday if today
    /// has none yet (a streak isn't broken until a whole day passes).
    static func streaks(days: Set<Date>, now: Date, calendar: Calendar) -> (current: Int, longest: Int) {
        let sorted = days.sorted()
        var longest = 0, run = 0
        var previous: Date?
        for day in sorted {
            if let previous, calendar.date(byAdding: .day, value: 1, to: previous) == day { run += 1 } else { run = 1 }
            longest = max(longest, run)
            previous = day
        }
        let today = calendar.startOfDay(for: now)
        var day = days.contains(today) ? today : calendar.date(byAdding: .day, value: -1, to: today)!
        var current = 0
        while days.contains(day) {
            current += 1
            day = calendar.date(byAdding: .day, value: -1, to: day)!
        }
        return (current, longest)
    }

    /// Share of dictations in a category, 0-100.
    public func percent(_ count: Int) -> Int {
        dictations > 0 ? Int((Double(count) * 100 / Double(dictations)).rounded()) : 0
    }

    /// How many times faster than typing.
    public var speedup: Double { Double(wordsPerMinute) / Self.typingWPM }
}

/// "Your voice": patterns in how you dictate, computed on-device from saved dictations.
public struct VoiceProfile: Equatable {
    public var mostUsedWords: [String] = []
    public var peakHour: Int?          // 0-23
    public var topApp: String?
    public var averageWords = 0
    public var longestWords = 0
    public var wordCloud: [(word: String, count: Int)] = []  // top words for the cloud
    public var openers: [String] = []       // most common first words ("so", "okay")
    public var wordsPerSentence = 0
    public var richness = 0                 // different words as a % of all words
    public var contractionRate = 0          // % of dictations using contractions (I'm, don't)
    public var exclamationRate = 0          // % of dictations with an exclamation mark
    public var questionRate = 0             // % of dictations asking something
    public var pace = 0                     // words per minute overall

    public enum Style: String {
        case fast = "Fast talker", steady = "Steady speaker", deliberate = "Deliberate speaker"
    }

    public var style: Style { pace >= 150 ? .fast : pace >= 110 ? .steady : .deliberate }

    /// Casual vs formal, from how often you use contractions.
    public var tone: String { contractionRate >= 40 ? "Casual" : contractionRate >= 15 ? "Balanced" : "Formal" }

    public static func == (a: VoiceProfile, b: VoiceProfile) -> Bool {
        a.mostUsedWords == b.mostUsedWords && a.peakHour == b.peakHour && a.topApp == b.topApp
            && a.averageWords == b.averageWords && a.longestWords == b.longestWords
            && a.wordCloud.map(\.word) == b.wordCloud.map(\.word) && a.wordCloud.map(\.count) == b.wordCloud.map(\.count)
            && a.openers == b.openers && a.wordsPerSentence == b.wordsPerSentence && a.richness == b.richness
            && a.contractionRate == b.contractionRate && a.exclamationRate == b.exclamationRate
            && a.questionRate == b.questionRate && a.pace == b.pace
    }

    static let stopwords: Set<String> = [
        "the", "a", "an", "and", "or", "but", "so", "to", "of", "in", "on", "at", "for", "with", "is", "it", "its",
        "i", "im", "you", "we", "they", "he", "she", "that", "this", "these", "those", "be", "are", "was", "were",
        "do", "dont", "does", "did", "have", "has", "had", "not", "no", "yes", "if", "then", "just", "like", "can",
        "will", "would", "should", "could", "my", "your", "our", "me", "us", "them", "what", "when", "how", "all",
        "there", "here", "as", "by", "from", "up", "out", "about", "into", "also", "any", "one", "get", "make", "go",
        "want", "need", "know", "okay", "ok", "hello", "hi", "thats", "its", "ill", "youre", "lets", "going", "some",
    ]

    public init() {}

    public init(_ records: [Recording], calendar: Calendar = .current, top: Int = 3) {
        let used = records.filter { $0.status != .cancelled && $0.words > 0 }
        guard !used.isEmpty else { return }
        var counts: [String: Int] = [:]
        for record in used {
            for word in record.transcript.lowercased().split(whereSeparator: { !$0.isLetter && $0 != "'" }) {
                let w = word.replacingOccurrences(of: "'", with: "")
                if w.count > 2, !Self.stopwords.contains(w) { counts[w, default: 0] += 1 }
            }
        }
        mostUsedWords = counts.filter { $0.value > 1 }
            .sorted { $0.value != $1.value ? $0.value > $1.value : $0.key < $1.key }
            .prefix(top).map(\.key)
        var hours: [Int: Int] = [:]
        for record in used { hours[calendar.component(.hour, from: record.startedAt), default: 0] += 1 }
        peakHour = hours.max { $0.value != $1.value ? $0.value < $1.value : $0.key > $1.key }?.key
        var apps: [String: Int] = [:]
        for record in used { if let app = record.app?.app { apps[app, default: 0] += 1 } }
        topApp = apps.max { $0.value != $1.value ? $0.value < $1.value : $0.key > $1.key }?.key
        let words = used.map(\.words)
        averageWords = Int((Double(words.reduce(0, +)) / Double(words.count)).rounded())
        longestWords = words.max() ?? 0

        wordCloud = counts.sorted { $0.value != $1.value ? $0.value > $1.value : $0.key < $1.key }
            .prefix(18).map { ($0.key, $0.value) }
        var firsts: [String: Int] = [:]
        for record in used {
            if let first = MoreInsights.tokens(record.transcript).first { firsts[first, default: 0] += 1 }
        }
        openers = firsts.filter { $0.value > 1 }
            .sorted { $0.value != $1.value ? $0.value > $1.value : $0.key < $1.key }.prefix(2).map(\.key)
        let sentences = used.reduce(0) { total, r in
            total + max(1, r.transcript.split(whereSeparator: { ".!?".contains($0) })
                .filter { !$0.trimmingCharacters(in: .whitespaces).isEmpty }.count)
        }
        let totalWords = words.reduce(0, +)
        wordsPerSentence = Int((Double(totalWords) / Double(sentences)).rounded())
        let allTokens = used.flatMap { MoreInsights.tokens($0.transcript) }
        richness = allTokens.isEmpty ? 0 : Int((Double(Set(allTokens).count) * 100 / Double(allTokens.count)).rounded())
        let n = Double(used.count)
        let percent = { (match: (Recording) -> Bool) in Int((Double(used.filter(match).count) * 100 / n).rounded()) }
        contractionRate = percent { $0.transcript.range(of: #"\b\w+['’](m|re|s|ve|ll|d|t)\b"#, options: [.regularExpression, .caseInsensitive]) != nil }
        exclamationRate = percent { $0.transcript.contains("!") }
        questionRate = percent { $0.transcript.contains("?") }
        let minutes = used.reduce(0.0) { $0 + $1.durationS } / 60
        pace = minutes > 0 ? Int((Double(totalWords) / minutes).rounded()) : 0
    }
}

/// The fun extras on Insights, all computed on-device from saved dictations.
public struct MoreInsights: Equatable {
    public var minutesSaved = 0          // typing time (at 40 wpm) minus speaking time
    public var thisWeekWords = 0
    public var lastWeekWords = 0
    public var fillersRemoved = 0        // filler words in the raw transcript that cleanup took out
    public var topFillers: [String] = []
    public var uniqueWords = 0
    public var byHour: [Int] = Array(repeating: 0, count: 24)  // dictations per hour of day
    public var topApps: [AppWords] = []
    public var dailyPace: [DayPace] = []  // words per minute, last 14 days with dictation
    public var persona: Persona = .newcomer
    // Fun facts
    public var keystrokesSaved = 0         // characters you didn't have to type
    public var talkSeconds = 0.0
    public var byWeekday: [Int] = Array(repeating: 0, count: 7)  // words, Sunday first
    public var biggestDay: DayWords?
    public var fastest: Highlight?         // highest pace, dictations of 10+ words
    public var longest: Highlight?
    public var catchphrase: String?        // most repeated 2-3 word phrase
    public var questions = 0
    public var politeness = 0              // "please" and "thank(s/ you)"
    public var selfCorrections = 0         // "no wait", "sorry", "I mean", "scratch that"

    public struct DayWords: Equatable {
        public var day: Date
        public var words: Int
    }

    public struct Highlight: Equatable {
        public var words: Int
        public var seconds: Double
        public var text: String
        public var wpm: Int { seconds > 0 ? Int((Double(words) / seconds * 60).rounded()) : 0 }
    }

    public struct AppWords: Equatable, Identifiable {
        public var app: String
        public var words: Int
        public var id: String { app }
    }

    public struct DayPace: Equatable, Identifiable {
        public var day: Date
        public var wpm: Int
        public var id: Date { day }
    }

    public enum Persona: String {
        case newcomer = "Just getting started"
        case earlyBird = "Early bird"
        case nineToFiver = "Nine-to-fiver"
        case nightOwl = "Night owl"
        case marathoner = "Marathon talker"

        public var detail: String {
            switch self {
            case .newcomer: "Dictate a few more times to find your rhythm."
            case .earlyBird: "Most of your dictating happens before 9 am."
            case .nineToFiver: "You talk to your Mac most during working hours."
            case .nightOwl: "Most of your dictating happens after 9 pm."
            case .marathoner: "Your dictations run long: over 60 words on average."
            }
        }

        public var symbol: String {
            switch self {
            case .newcomer: "sparkles"
            case .earlyBird: "sunrise"
            case .nineToFiver: "briefcase"
            case .nightOwl: "moon.stars"
            case .marathoner: "figure.run"
            }
        }
    }

    /// Fillers counted for "fillers removed": the clear-cut ones only, so "like" in
    /// "I like it" isn't counted unless cleanup actually removed a "like".
    static let fillers = ["um", "uh", "er", "erm", "ah", "hmm", "like", "basically", "actually", "literally"]

    public init() {}

    public init(_ records: [Recording], now: Date = Date(), calendar: Calendar = .current) {
        let used = records.filter { $0.status != .cancelled && $0.words > 0 }
        guard !used.isEmpty else { return }

        let words = used.reduce(0) { $0 + $1.words }
        let speaking = used.reduce(0.0) { $0 + $1.durationS } / 60
        minutesSaved = max(0, Int((Double(words) / Stats.typingWPM - speaking).rounded()))

        let startOfWeek = calendar.dateInterval(of: .weekOfYear, for: now)?.start ?? now
        let startOfLast = calendar.date(byAdding: .day, value: -7, to: startOfWeek) ?? startOfWeek
        for r in used {
            if r.startedAt >= startOfWeek { thisWeekWords += r.words }
            else if r.startedAt >= startOfLast { lastWeekWords += r.words }
        }

        var removed: [String: Int] = [:]
        for r in used {
            guard let raw = r.rawTranscript else { continue }
            let before = Self.tokens(raw), after = Self.tokens(r.transcript)
            for f in Self.fillers {
                let n = before.filter { $0 == f }.count - after.filter { $0 == f }.count
                if n > 0 { removed[f, default: 0] += n }
            }
        }
        fillersRemoved = removed.values.reduce(0, +)
        topFillers = removed.sorted { $0.value != $1.value ? $0.value > $1.value : $0.key < $1.key }.prefix(3).map(\.key)

        uniqueWords = Set(used.flatMap { Self.tokens($0.transcript) }).count

        for r in used { byHour[calendar.component(.hour, from: r.startedAt)] += 1 }

        var apps: [String: Int] = [:]
        for r in used { apps[r.app?.app ?? "Unknown", default: 0] += r.words }
        topApps = apps.map { AppWords(app: $0.key, words: $0.value) }
            .sorted { $0.words != $1.words ? $0.words > $1.words : $0.app < $1.app }
            .prefix(5).map { $0 }

        let byDay = Dictionary(grouping: used) { calendar.startOfDay(for: $0.startedAt) }
        dailyPace = byDay.keys.sorted().suffix(14).compactMap { day in
            let rs = byDay[day]!
            let minutes = rs.reduce(0.0) { $0 + $1.durationS } / 60
            guard minutes > 0 else { return nil }
            return DayPace(day: day, wpm: Int((Double(rs.reduce(0) { $0 + $1.words }) / minutes).rounded()))
        }

        persona = Self.persona(used: used, byHour: byHour, words: words)

        keystrokesSaved = used.reduce(0) { $0 + $1.transcript.count }
        talkSeconds = used.reduce(0.0) { $0 + $1.durationS }
        for r in used { byWeekday[calendar.component(.weekday, from: r.startedAt) - 1] += r.words }
        biggestDay = byDay.map { DayWords(day: $0.key, words: $0.value.reduce(0) { $0 + $1.words }) }
            .max { $0.words != $1.words ? $0.words < $1.words : $0.day > $1.day }
        let highlight = { (r: Recording) in Highlight(words: r.words, seconds: r.durationS, text: r.transcript) }
        fastest = used.filter { $0.words >= 10 && $0.durationS > 0 }.map(highlight).max { $0.wpm < $1.wpm }
        longest = used.map(highlight).max { $0.words < $1.words }
        catchphrase = Self.catchphrase(used.map(\.transcript))
        questions = used.reduce(0) { $0 + $1.transcript.filter { $0 == "?" }.count }
        for r in used {
            let text = r.transcript.lowercased()
            politeness += Self.count(["please", "thank you", "thanks"], in: text)
            selfCorrections += Self.count(["no wait", "no, wait", "scratch that", "sorry,", "i mean"], in: (r.rawTranscript ?? r.transcript).lowercased())
        }
    }

    static func count(_ needles: [String], in text: String) -> Int {
        needles.reduce(0) { $0 + text.components(separatedBy: $1).count - 1 }
    }

    /// The most repeated 3-word (else 2-word) phrase that isn't all filler, said at least twice.
    static func catchphrase(_ texts: [String]) -> String? {
        for n in [3, 2] {
            var counts: [String: Int] = [:]
            for text in texts {
                let words = tokens(text)
                guard words.count >= n else { continue }
                for i in 0...(words.count - n) {
                    let gram = Array(words[i..<i + n])
                    if gram.allSatisfy({ VoiceProfile.stopwords.contains($0) }) { continue }
                    counts[gram.joined(separator: " "), default: 0] += 1
                }
            }
            if let best = counts.filter({ $0.value >= 2 })
                .max(by: { $0.value != $1.value ? $0.value < $1.value : $0.key > $1.key }) {
                return best.key
            }
        }
        return nil
    }

    static func persona(used: [Recording], byHour: [Int], words: Int) -> Persona {
        guard used.count >= 5 else { return .newcomer }
        if Double(words) / Double(used.count) > 60 { return .marathoner }
        let total = Double(used.count)
        let early = Double(byHour[0..<9].reduce(0, +)), late = Double(byHour[21..<24].reduce(0, +))
        if late / total > 0.4 { return .nightOwl }
        if early / total > 0.4 { return .earlyBird }
        return .nineToFiver
    }

    static func tokens(_ text: String) -> [String] {
        text.lowercased().split { !$0.isLetter && $0 != "'" }.map { $0.replacingOccurrences(of: "'", with: "") }
    }

    /// Change from last week, as a whole percent (nil when there's no last week to compare).
    public var weekChange: Int? {
        lastWeekWords > 0 ? Int((Double(thisWeekWords - lastWeekWords) * 100 / Double(lastWeekWords)).rounded()) : nil
    }

    /// A playful comparison for a word count.
    public static func equivalent(words: Int) -> String {
        switch words {
        case ..<280: return "about \(max(1, words / 40)) tweet\(words / 40 == 1 ? "" : "s")"
        case ..<5_000: return String(format: "about %.0f pages of a book", (Double(words) / 300).rounded())
        case ..<50_000: return String(format: "about %.0f chapters of a novel", (Double(words) / 4_000).rounded())
        default: return String(format: "about %.1f novels", Double(words) / 80_000)
        }
    }
}
