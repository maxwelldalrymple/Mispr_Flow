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
    }
}
