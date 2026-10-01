import Charts
import MisprCore
import SwiftUI

struct InsightsView: View {
    @EnvironmentObject var model: AppModel
    @State private var tab = ProcessInfo.processInfo.environment["MISPR_PAGE"] == "Voice" ? 1 : 0  // dev screenshots

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("Insights").font(.system(size: 24, weight: .semibold)).padding(.bottom, 22)
                HStack(spacing: 22) {
                    tabButton("Your usage", 0)
                    tabButton("Your voice", 1)
                }
                Divider().overlay(Theme.cardStroke).padding(.bottom, 26)
                if tab == 0 { usage } else { VoiceView(profile: model.voice) }
            }
            .padding(.horizontal, 40).padding(.vertical, 36)
            .frame(maxWidth: 1100)
            .frame(maxWidth: .infinity)
        }
    }

    private func tabButton(_ title: String, _ index: Int) -> some View {
        Button { tab = index } label: {
            VStack(spacing: 8) {
                Text(title).font(.system(size: 14, weight: tab == index ? .semibold : .regular))
                    .foregroundStyle(tab == index ? Theme.text : Theme.secondary)
                Rectangle().fill(tab == index ? Theme.text : .clear).frame(height: 2)
            }
            .fixedSize()
        }
        .buttonStyle(.plain)
    }

    private var stats: Stats { model.stats }

    private var usage: some View {
        VStack(spacing: 20) {
            HStack(alignment: .top, spacing: 20) {
                Card(padding: 20) {
                    VStack(alignment: .leading, spacing: 4) {
                        big("\(stats.wordsPerMinute)", "Words per minute")
                        SpeedGauge(wpm: stats.wordsPerMinute).frame(height: 88).padding(.top, 8)
                    }
                }
                Card(padding: 20) {
                    VStack(alignment: .leading, spacing: 4) {
                        big("\(stats.cleaned)", "Fixes made by cleanup")
                        Divider().overlay(Theme.cardStroke).padding(.vertical, 10)
                        Text("Dictations where fillers, repeats, or self-corrections were cleaned up. Your words are never added to.")
                            .font(.system(size: 12)).foregroundStyle(Theme.secondary)
                    }
                }
                Card(padding: 20) {
                    VStack(alignment: .leading, spacing: 4) {
                        big(stats.totalWords.formatted(), "Total words dictated")
                        Divider().overlay(Theme.cardStroke).padding(.vertical, 10)
                        Label("\(stats.dictations) dictations on this Mac", systemImage: "desktopcomputer")
                            .font(.system(size: 13))
                    }
                }
            }
            .fixedSize(horizontal: false, vertical: true)
            HStack(alignment: .top, spacing: 20) {
                Card(padding: 20) { categories }
                Card(padding: 20) { StreakView(stats: stats) }
            }
            .fixedSize(horizontal: false, vertical: true)
            MoreInsightsView(more: model.more, totalWords: stats.totalWords)
        }
    }

    private func big(_ value: String, _ label: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value).font(.system(size: 26, weight: .medium))
            Text(label.uppercased()).font(.system(size: 11, weight: .medium)).tracking(0.8).foregroundStyle(Theme.secondary)
        }
    }

    private var categories: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                Text("Desktop usage").font(.system(size: 22, weight: .medium))
                Spacer()
                Text("TOTAL APPS USED | \(stats.appsUsed)").font(.system(size: 11, weight: .medium)).tracking(0.8)
            }
            .padding(.bottom, 6)
            ForEach(stats.categories, id: \.category) { item in
                HStack(spacing: 12) {
                    Image(systemName: symbol(item.category)).frame(width: 18).foregroundStyle(Theme.secondary)
                    Text("\(stats.percent(item.count))%").font(.system(size: 11, weight: .semibold))
                        .foregroundStyle(.white).frame(width: 40).padding(.vertical, 3)
                        .background(RoundedRectangle(cornerRadius: 4).fill(Theme.accent.opacity(item.count > 0 ? 1 : 0.35)))
                    Text("\(item.count) \(item.category.rawValue)".uppercased()).font(.system(size: 11, weight: .medium)).tracking(0.8)
                }
            }
        }
    }

    private func symbol(_ category: UsageCategory) -> String {
        switch category {
        case .aiPrompts: "sparkles"
        case .emails: "envelope"
        case .workMessages: "bubble.left.and.text.bubble.right"
        case .personalMessages: "message"
        case .documents: "doc.text"
        case .coding: "chevron.left.forwardslash.chevron.right"
        case .other: "infinity"
        }
    }
}

/// A half-circle gauge of dictation speed against typing (40 wpm).
struct SpeedGauge: View {
    let wpm: Int
    static let maxWPM = 200.0

    var body: some View {
        let fraction = min(Double(wpm) / Self.maxWPM, 1)
        ZStack(alignment: .bottom) {
            Arc(fraction: 1).stroke(Theme.cardStroke, style: StrokeStyle(lineWidth: 12, lineCap: .round))
            Arc(fraction: fraction).stroke(Theme.accent, style: StrokeStyle(lineWidth: 12, lineCap: .round))
            VStack(spacing: 0) {
                Text(wpm > 0 ? String(format: "%.1f×", Double(wpm) / Stats.typingWPM) : "–").font(.system(size: 18, weight: .semibold))
                Text("vs typing").font(.system(size: 11)).foregroundStyle(Theme.secondary)
            }
        }
        .aspectRatio(2, contentMode: .fit)
        .frame(maxWidth: .infinity)
    }

    struct Arc: Shape {
        var fraction: Double

        func path(in rect: CGRect) -> Path {
            var path = Path()
            let radius = min(rect.width / 2, rect.height) - 6
            path.addArc(center: CGPoint(x: rect.midX, y: rect.maxY - 2), radius: radius,
                        startAngle: .degrees(180), endAngle: .degrees(180 + 180 * fraction), clockwise: false)
            return path
        }
    }
}

/// Current streak plus a GitHub-style calendar of the last 20 weeks.
struct StreakView: View {
    let stats: Stats
    static let weeks = 20

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                Text("\(stats.currentStreak) day streak").font(.system(size: 22, weight: .medium))
                Spacer()
                Text("LONGEST STREAK | \(stats.longestStreak) DAYS").font(.system(size: 11, weight: .medium)).tracking(0.8)
            }
            HStack(alignment: .top, spacing: 4) {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(Array(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].enumerated()), id: \.offset) { _, day in
                        Text(day).font(.system(size: 9)).foregroundStyle(Theme.secondary).frame(height: 12)
                    }
                }
                .padding(.trailing, 4)
                ForEach(0..<Self.weeks, id: \.self) { week in
                    VStack(spacing: 4) {
                        ForEach(0..<7, id: \.self) { weekday in
                            RoundedRectangle(cornerRadius: 2).fill(color(for: date(week: week, weekday: weekday)))
                                .frame(width: 12, height: 12)
                        }
                    }
                }
            }
            HStack(spacing: 4) {
                Text("Less").font(.system(size: 10)).foregroundStyle(Theme.secondary)
                ForEach([0, 1, 3, 6], id: \.self) { n in
                    RoundedRectangle(cornerRadius: 2).fill(shade(n)).frame(width: 10, height: 10)
                }
                Text("More").font(.system(size: 10)).foregroundStyle(Theme.secondary)
            }
        }
    }

    private func date(week: Int, weekday: Int) -> Date? {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        let thisWeekStart = calendar.date(byAdding: .day, value: -(calendar.component(.weekday, from: today) - 1), to: today)!
        let day = calendar.date(byAdding: .day, value: (week - (Self.weeks - 1)) * 7 + weekday, to: thisWeekStart)!
        return day > today ? nil : day
    }

    private func color(for day: Date?) -> Color {
        guard let day else { return .clear }
        return shade(stats.perDay[day] ?? 0)
    }

    private func shade(_ count: Int) -> Color {
        switch count {
        case 0: Theme.cardStroke
        case 1...2: Theme.accent.opacity(0.35)
        case 3...5: Theme.accent.opacity(0.65)
        default: Theme.accent
        }
    }
}

struct VoiceView: View {
    let profile: VoiceProfile

    var body: some View {
        if profile.averageWords == 0 {
            Card(padding: 28) {
                Text("Dictate a few times and your voice profile appears here.").font(Theme.display(20))
            }
        } else {
            VStack(alignment: .leading, spacing: 20) {
                hero
                LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 20), count: 3), spacing: 20) {
                    tile("text.word.spacing", "\(profile.wordsPerSentence) words", "Per sentence",
                         profile.wordsPerSentence > 20 ? "You build long, flowing sentences." : "Short and punchy.")
                    tile("books.vertical", "\(profile.richness)%", "Vocabulary richness",
                         "Different words, as a share of everything you've said.")
                    tile("questionmark.bubble", "\(profile.questionRate)%", "Curiosity", "Of your dictations ask a question.")
                    tile("exclamationmark.bubble", "\(profile.exclamationRate)%", "Enthusiasm", "Of your dictations end with a bang!")
                    tile("clock", peak, "Peak time & place", "When and where you talk the most.")
                    tile("text.alignleft", "\(profile.averageWords) words", "Average dictation",
                         "Your longest was \(profile.longestWords) words.")
                }
                Card(padding: 20) { cloud }
                Text("Worked out on this Mac from your saved dictations. Nothing is uploaded.")
                    .font(.system(size: 12)).foregroundStyle(Theme.secondary)
            }
        }
    }

    private var hero: some View {
        Card(padding: 24) {
            HStack(alignment: .top, spacing: 18) {
                Image(systemName: profile.style == .fast ? "hare.fill" : profile.style == .steady ? "metronome.fill" : "tortoise.fill")
                    .font(.system(size: 30)).foregroundStyle(Theme.accent).frame(width: 44)
                VStack(alignment: .leading, spacing: 6) {
                    Text("You're a \(profile.style.rawValue.lowercased())").font(Theme.display(28))
                    Text("\(profile.pace) words per minute, with a \(profile.tone.lowercased()) tone" +
                         (profile.openers.isEmpty ? "." : ". You tend to start with " + profile.openers.map { "“\($0.capitalized)”" }.joined(separator: " or ") + "."))
                        .font(.system(size: 14)).foregroundStyle(Theme.secondary)
                    HStack(spacing: 8) {
                        chip(profile.tone, "theatermasks")
                        chip("\(profile.contractionRate)% contractions", "quote.closing")
                        if let first = profile.mostUsedWords.first { chip("Loves “\(first)”", "heart") }
                    }
                    .padding(.top, 6)
                }
                Spacer()
            }
        }
    }

    private var cloud: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Your words").font(Theme.display(22))
            let top = Double(profile.wordCloud.first?.count ?? 1)
            FlowLayout(spacing: 10) {
                ForEach(Array(profile.wordCloud.enumerated()), id: \.offset) { index, item in
                    let weight = Double(item.count) / top
                    Text(item.word)
                        .font(.system(size: 13 + 17 * weight, weight: weight > 0.6 ? .semibold : .regular, design: .serif))
                        .foregroundStyle(index % 3 == 0 ? Theme.accent : Theme.text.opacity(0.55 + 0.45 * weight))
                        .help("Said \(item.count) times")
                }
            }
        }
    }

    private func chip(_ text: String, _ symbol: String) -> some View {
        Label(text, systemImage: symbol).font(.system(size: 12))
            .padding(.horizontal, 10).padding(.vertical, 4)
            .background(Capsule().fill(Theme.accentSoft))
    }

    private var peak: String {
        let hour = profile.peakHour.map { h -> String in
            var components = DateComponents()
            components.hour = h
            return (Calendar.current.date(from: components) ?? Date()).formatted(.dateTime.hour())
        } ?? "Anytime"
        return profile.topApp.map { "\(hour) · \($0)" } ?? hour
    }

    private func tile(_ symbol: String, _ value: String, _ title: String, _ detail: String) -> some View {
        Card(padding: 18) {
            VStack(alignment: .leading, spacing: 6) {
                Image(systemName: symbol).font(.system(size: 15)).foregroundStyle(Theme.accent)
                Text(value).font(.system(size: 22, weight: .medium)).lineLimit(1).minimumScaleFactor(0.7)
                Text(title.uppercased()).font(.system(size: 10.5, weight: .medium)).tracking(0.8).foregroundStyle(Theme.secondary)
                Text(detail).font(.system(size: 12)).foregroundStyle(Theme.secondary).fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

/// Lays children out left to right, wrapping onto new lines (for the word cloud).
struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let rows = arrange(width: proposal.width ?? .infinity, subviews: subviews)
        return CGSize(width: proposal.width ?? rows.map(\.width).max() ?? 0,
                      height: rows.reduce(0) { $0 + $1.height } + spacing * CGFloat(max(0, rows.count - 1)))
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var y = bounds.minY
        for row in arrange(width: bounds.width, subviews: subviews) {
            var x = bounds.minX
            for index in row.items {
                let size = subviews[index].sizeThatFits(.unspecified)
                subviews[index].place(at: CGPoint(x: x, y: y + (row.height - size.height) / 2), proposal: .unspecified)
                x += size.width + spacing
            }
            y += row.height + spacing
        }
    }

    private struct Row { var items: [Int] = []; var width: CGFloat = 0; var height: CGFloat = 0 }

    private func arrange(width: CGFloat, subviews: Subviews) -> [Row] {
        var rows = [Row()]
        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            if !rows[rows.count - 1].items.isEmpty && rows[rows.count - 1].width + spacing + size.width > width {
                rows.append(Row())
            }
            var row = rows[rows.count - 1]
            row.width += (row.items.isEmpty ? 0 : spacing) + size.width
            row.height = max(row.height, size.height)
            row.items.append(index)
            rows[rows.count - 1] = row
        }
        return rows
    }
}

/// Time saved, week over week, fillers, vocabulary, when and where you dictate, and pace.
struct MoreInsightsView: View {
    let more: MoreInsights
    let totalWords: Int
    @Environment(\.colorScheme) private var scheme
    private var chartColor: Color { Theme.resolved(\.accent, scheme) }

    var body: some View {
        VStack(spacing: 20) {
            HStack(alignment: .top, spacing: 20) {
                fact("clock.arrow.circlepath", "\(more.minutesSaved) min", "Saved vs typing",
                     "At a typical 40 wpm, minus the time you spent talking.")
                fact("calendar", more.thisWeekWords.formatted(), "Words this week", weekDetail)
                fact("scissors", "\(more.fillersRemoved)", "Filler words cleaned up",
                     more.topFillers.isEmpty ? "None yet." : "Mostly " + more.topFillers.map { "“\($0)”" }.joined(separator: ", ") + ".")
                fact("character.book.closed", more.uniqueWords.formatted(), "Different words used",
                     "That's " + MoreInsights.equivalent(words: totalWords) + " in total.")
            }
            .fixedSize(horizontal: false, vertical: true)
            HStack(alignment: .top, spacing: 20) {
                Card(padding: 20) { hours }
                Card(padding: 20) { apps }
            }
            .fixedSize(horizontal: false, vertical: true)
            HStack(alignment: .top, spacing: 20) {
                Card(padding: 20) { weekdays }
                if more.dailyPace.count >= 2 { Card(padding: 20) { pace } }
            }
            .fixedSize(horizontal: false, vertical: true)
            funFacts
        }
    }

    private var weekDetail: String {
        guard let change = more.weekChange else { return "Nothing last week to compare with." }
        if change == 0 { return "Same as last week." }
        return "\(abs(change))% \(change > 0 ? "more" : "less") than last week (\(more.lastWeekWords.formatted()))."
    }

    private func fact(_ symbol: String, _ value: String, _ label: String, _ detail: String) -> some View {
        Card(padding: 18) {
            VStack(alignment: .leading, spacing: 6) {
                Image(systemName: symbol).font(.system(size: 15)).foregroundStyle(Theme.accent)
                Text(value).font(.system(size: 24, weight: .medium))
                Text(label.uppercased()).font(.system(size: 10.5, weight: .medium)).tracking(0.8).foregroundStyle(Theme.secondary)
                Text(detail).font(.system(size: 12)).foregroundStyle(Theme.secondary).fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var hours: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                Image(systemName: more.persona.symbol).font(.system(size: 20)).foregroundStyle(Theme.accent)
                VStack(alignment: .leading, spacing: 2) {
                    Text(more.persona.rawValue).font(.system(size: 20, weight: .medium))
                    Text(more.persona.detail).font(.system(size: 12)).foregroundStyle(Theme.secondary)
                }
            }
            Bars(values: more.byHour, labels: [0: "12a", 6: "6a", 12: "12p", 18: "6p"], color: chartColor)
                .frame(height: 110)
            Text("When you dictate, by hour of day").font(.system(size: 11)).foregroundStyle(Theme.secondary)
        }
    }

    private var weekdays: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Your week").font(.system(size: 20, weight: .medium))
            Bars(values: more.byWeekday, labels: [0: "S", 1: "M", 2: "T", 3: "W", 4: "T", 5: "F", 6: "S"],
                 color: chartColor, labelEvery: true)
                .frame(height: 110)
            Text("Words by day of the week").font(.system(size: 11)).foregroundStyle(Theme.secondary)
        }
    }

    private var funFacts: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("FUN FACTS").font(.system(size: 11, weight: .semibold)).tracking(0.8).foregroundStyle(Theme.secondary)
            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 20), count: 3), spacing: 20) {
                fact("keyboard", more.keystrokesSaved.formatted(), "Keystrokes skipped", "Every character you didn't have to type.")
                fact("waveform", talkTime, "Spent talking", "Total time your Mac listened.")
                fact("trophy", more.biggestDay.map { $0.words.formatted() } ?? "–", "Biggest day",
                     more.biggestDay.map { $0.day.formatted(.dateTime.weekday(.wide).month(.abbreviated).day()) } ?? "No dictations yet.")
                fact("hare", more.fastest.map { "\($0.wpm) wpm" } ?? "–", "Fastest dictation",
                     more.fastest.map { "“\(snippet($0.text))”" } ?? "Needs a dictation of 10+ words.")
                fact("text.alignleft", more.longest.map { "\($0.words) words" } ?? "–", "Longest dictation",
                     more.longest.map { "\(Int($0.seconds.rounded())) seconds without stopping." } ?? "No dictations yet.")
                fact("quote.bubble", more.catchphrase.map { "“\($0)”" } ?? "–", "Your catchphrase",
                     more.catchphrase == nil ? "Nothing repeated yet." : "The phrase you say most.")
                fact("questionmark.bubble", "\(more.questions)", "Questions asked", "Count of question marks in your dictation.")
                fact("hand.wave", "\(more.politeness)", "Pleases & thank-yous", more.politeness > 5 ? "Your Mac appreciates it." : "Manners are free.")
                fact("arrow.uturn.backward", "\(more.selfCorrections)", "Changed your mind",
                     "“No wait”, “sorry” and “I mean” that cleanup handled.")
            }
        }
    }

    private var talkTime: String {
        let minutes = Int(more.talkSeconds / 60)
        return minutes >= 60 ? "\(minutes / 60)h \(minutes % 60)m" : minutes > 0 ? "\(minutes) min" : "\(Int(more.talkSeconds)) s"
    }

    private func snippet(_ text: String) -> String {
        text.count > 60 ? String(text.prefix(57)) + "…" : text
    }

    private var apps: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Where your words go").font(.system(size: 20, weight: .medium))
            if more.topApps.isEmpty {
                Text("No dictations yet.").font(.system(size: 12)).foregroundStyle(Theme.secondary)
            }
            let top = Double(more.topApps.first?.words ?? 1)
            ForEach(more.topApps) { app in
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(app.app).font(.system(size: 13))
                        Spacer()
                        Text("\(app.words.formatted()) words").font(.system(size: 12)).foregroundStyle(Theme.secondary)
                    }
                    GeometryReader { geo in
                        Capsule().fill(Theme.accent.opacity(0.8))
                            .frame(width: max(6, geo.size.width * Double(app.words) / top), height: 6)
                    }
                    .frame(height: 6)
                }
            }
        }
    }

    private var pace: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                Text("Your pace").font(.system(size: 20, weight: .medium))
                Spacer()
                Text("WORDS PER MINUTE, BY DAY").font(.system(size: 11, weight: .medium)).tracking(0.8).foregroundStyle(Theme.secondary)
            }
            Chart(more.dailyPace) { day in
                AreaMark(x: .value("Day", day.day, unit: .day), y: .value("WPM", day.wpm))
                    .foregroundStyle(LinearGradient(colors: [chartColor.opacity(0.35), chartColor.opacity(0.02)],
                                                    startPoint: .top, endPoint: .bottom))
                    .interpolationMethod(.catmullRom)
                LineMark(x: .value("Day", day.day, unit: .day), y: .value("WPM", day.wpm))
                    .foregroundStyle(chartColor).interpolationMethod(.catmullRom)
                PointMark(x: .value("Day", day.day, unit: .day), y: .value("WPM", day.wpm))
                    .foregroundStyle(chartColor).symbolSize(24)
            }
            .chartXAxis { AxisMarks(values: .stride(by: .day)) { _ in AxisValueLabel(format: .dateTime.month(.abbreviated).day()) } }
            .frame(height: 140)
        }
    }
}

/// Simple bar chart drawn with shapes (themed colors, highlights the tallest bar).
struct Bars: View {
    let values: [Int]
    let labels: [Int: String]
    let color: Color
    var labelEvery = false

    var body: some View {
        let top = max(values.max() ?? 0, 1)
        VStack(spacing: 6) {
            GeometryReader { geo in
                HStack(alignment: .bottom, spacing: labelEvery ? 10 : 3) {
                    ForEach(Array(values.enumerated()), id: \.offset) { index, value in
                        RoundedRectangle(cornerRadius: 2)
                            .fill(color.opacity(value == top && value > 0 ? 1 : value > 0 ? 0.55 : 0.12))
                            .frame(height: max(3, geo.size.height * CGFloat(value) / CGFloat(top)))
                            .frame(maxWidth: .infinity)
                            .help("\(labels[index] ?? "\(index)"): \(value)")
                    }
                }
            }
            HStack(spacing: labelEvery ? 10 : 3) {
                ForEach(Array(values.indices), id: \.self) { index in
                    Text(labels[index] ?? "").font(.system(size: 10)).foregroundStyle(Theme.secondary)
                        .fixedSize().frame(maxWidth: .infinity, alignment: labelEvery ? .center : .leading)
                }
            }
        }
    }
}
