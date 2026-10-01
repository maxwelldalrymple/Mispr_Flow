import MisprCore
import SwiftUI

struct InsightsView: View {
    @EnvironmentObject var model: AppModel
    @State private var tab = 0

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Text("Insights").font(.system(size: 24, weight: .semibold)).padding(.bottom, 22)
                HStack(spacing: 22) {
                    tabButton("Your usage", 0)
                    tabButton("Your voice", 1)
                }
                Divider().overlay(Theme.cardStroke).padding(.bottom, 26)
                if tab == 0 { usage } else { VoiceView(profile: VoiceProfile(model.recordings)) }
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
            LazyVGrid(columns: [GridItem(.flexible(), spacing: 20), GridItem(.flexible())], spacing: 20) {
                tile("Most used words", profile.mostUsedWords.isEmpty ? "Not enough yet" : profile.mostUsedWords.joined(separator: ", "))
                tile("Your peak time & place", peak)
                tile("Average dictation", "\(profile.averageWords) words")
                tile("Longest dictation", "\(profile.longestWords) words")
            }
            Text("Worked out on this Mac from your saved dictations. Nothing is uploaded.")
                .font(.system(size: 12)).foregroundStyle(Theme.secondary).padding(.top, 14)
        }
    }

    private var peak: String {
        let hour = profile.peakHour.map { h -> String in
            var components = DateComponents()
            components.hour = h
            let date = Calendar.current.date(from: components) ?? Date()
            return "Around " + date.formatted(.dateTime.hour())
        } ?? "Anytime"
        return profile.topApp.map { "\(hour), mostly in \($0)" } ?? hour
    }

    private func tile(_ title: String, _ value: String) -> some View {
        Card(padding: 20) {
            VStack(alignment: .leading, spacing: 8) {
                Text(title).font(Theme.display(20))
                Text(value).font(.system(size: 14)).foregroundStyle(Theme.secondary)
            }
        }
    }
}
