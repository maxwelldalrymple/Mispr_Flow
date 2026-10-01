import MisprCore
import SwiftUI

/// Notetaker: your past meeting notes (Notes) and patterns across them (Insights). Clicking a
/// meeting opens its summary, transcript, insights, and your own notes.
struct NotesView: View {
    @EnvironmentObject var model: AppModel
    @State private var tab: Int
    @State private var open: Meeting?
    @State private var query = ""
    // Development: MISPR_PEOPLE="Priya Shah,Jordan Lee" opens People with them selected (screenshots).
    @State private var selectedPeople: Set<String> = Set((ProcessInfo.processInfo.environment["MISPR_PEOPLE"] ?? "")
        .split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty })

    /// `initialTab`: 0 notes, 1 people, 2 insights (tests; MISPR_PEOPLE opens People).
    init(initialTab: Int? = nil, people: Set<String>? = nil) {
        let env = ProcessInfo.processInfo.environment["MISPR_PEOPLE"]
        _tab = State(initialValue: initialTab ?? (env == nil ? 0 : 1))
        if let people { _selectedPeople = State(initialValue: people) }
    }

    var body: some View {
        if let open {
            MeetingDetailView(meeting: open, back: { self.open = nil }, person: showPerson)
        } else {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    HStack {
                        Text("Notetaker").font(.system(size: 24, weight: .semibold))
                        Spacer()
                        Button { model.openNote() } label: {
                            Label("New note", systemImage: "plus").font(.system(size: 13, weight: .medium))
                        }
                        .buttonStyle(OutlineButton())
                    }
                    .padding(.bottom, 22)
                    HStack(spacing: 22) {
                        tabButton("Notes", 0)
                        tabButton("People", 1)
                        tabButton("Insights", 2)
                        Spacer()
                        if tab == 0 {
                            HStack(spacing: 6) {
                                Image(systemName: "magnifyingglass").foregroundStyle(Theme.secondary)
                                TextField("Search notes", text: $query).textFieldStyle(.plain).frame(width: 170)
                            }
                            .font(.system(size: 13)).padding(.bottom, 8)
                        }
                    }
                    Divider().overlay(Theme.cardStroke).padding(.bottom, 22)
                    switch tab {
                    case 0: list
                    case 1: PeopleView(meetings: model.meetings, selected: $selectedPeople) { open = $0 }
                    default: NotesInsights(overview: MeetingsOverview(model.meetings), person: showPerson)
                    }
                }
                .padding(.horizontal, 40).padding(.vertical, 36)
                .frame(maxWidth: 1000, alignment: .leading)
                .frame(maxWidth: .infinity)
            }
        }
    }

    /// Open someone's page from anywhere in Notetaker.
    private func showPerson(_ name: String) {
        (tab, open, selectedPeople) = Self.personPage(name)
    }

    /// Where clicking a person goes: the People tab, with only them selected, no meeting open.
    static func personPage(_ name: String) -> (tab: Int, open: Meeting?, selected: Set<String>) {
        (1, nil, [name])
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

    private var filtered: [Meeting] {
        let q = query.trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else { return model.meetings }
        return model.meetings.filter { m in
            m.title.localizedCaseInsensitiveContains(q)
                || m.participants.contains { $0.name.localizedCaseInsensitiveContains(q) }
                || m.transcript.contains { $0.text.localizedCaseInsensitiveContains(q) }
        }
    }

    @ViewBuilder private var list: some View {
        if model.meetings.isEmpty {
            Card(padding: 28) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Your meeting notes will appear here").font(Theme.display(20))
                    Text("Start one with New note, or the ◉ button on the widget.").font(.system(size: 13)).foregroundStyle(Theme.secondary)
                }
            }
        }
        let calendar = Calendar.current
        let days = Dictionary(grouping: filtered) { calendar.startOfDay(for: $0.startedAt) }
        LazyVStack(alignment: .leading, spacing: 0) {
            ForEach(days.keys.sorted(by: >), id: \.self) { day in
                Text(DayGroup(day: day, records: []).title.uppercased())
                    .font(.system(size: 11, weight: .semibold)).tracking(0.8).foregroundStyle(Theme.secondary)
                    .padding(.top, 14).padding(.bottom, 8)
                ForEach(days[day]!) { meeting in
                    NoteRow(meeting: meeting).onTapGesture { open = meeting }
                }
            }
        }
    }
}

struct NoteRow: View {
    let meeting: Meeting
    @State private var hovering = false

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: "doc.text").font(.system(size: 15)).foregroundStyle(Theme.secondary)
                .frame(width: 36, height: 36).background(RoundedRectangle(cornerRadius: 9).fill(Theme.card))
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(meeting.title).font(.system(size: 14, weight: .medium))
                    if meeting.sample == true { Badge(text: "Sample") }
                }
                Text([meeting.startedAt.formatted(.dateTime.hour().minute()), meeting.durationText, meeting.app]
                        .compactMap { $0 }.joined(separator: " · "))
                    .font(.system(size: 12)).foregroundStyle(Theme.secondary)
            }
            Spacer()
            PeopleStack(names: meeting.participants.map(\.name))
            Image(systemName: "chevron.right").font(.system(size: 11)).foregroundStyle(Theme.secondary)
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 12).fill(hovering ? Theme.card : Color.clear))
        .contentShape(Rectangle())
        .onHover { hovering = $0 }
    }
}

struct Badge: View {
    let text: String

    var body: some View {
        Text(text).font(.system(size: 10, weight: .semibold))
            .padding(.horizontal, 6).padding(.vertical, 2)
            .background(Capsule().fill(Theme.accentSoft)).foregroundStyle(Theme.accent)
    }
}

/// Overlapping initials for a meeting's participants.
struct PeopleStack: View {
    let names: [String]
    var size: CGFloat = 26

    var body: some View {
        HStack(spacing: -8) {
            ForEach(Array(names.prefix(4).enumerated()), id: \.offset) { _, name in
                Initials(name: name, size: size).overlay(Circle().stroke(Theme.content, lineWidth: 2))
            }
            if names.count > 4 {
                Text("+\(names.count - 4)").font(.system(size: 11)).foregroundStyle(Theme.secondary).padding(.leading, 12)
            }
        }
    }
}

struct Initials: View {
    let name: String
    var size: CGFloat = 26
    static let colors: [UInt32] = [0x1F5C4A, 0x1E6FB8, 0x6B4FC4, 0xD4572A, 0xC2185B, 0x34477F, 0x8D6E63]

    var body: some View {
        let letters = name.split(separator: " ").prefix(2).compactMap(\.first).map { String($0).uppercased() }.joined()
        let hue = Self.colors[abs(name.unicodeScalars.reduce(0) { $0 &+ Int($1.value) }) % Self.colors.count]
        Text(letters).font(.system(size: size * 0.38, weight: .semibold)).foregroundStyle(.white)
            .frame(width: size, height: size)
            .background(Circle().fill(Color(nsColor: Theme.nsColor(hex: hue))))
            .help(name)
    }
}

/// Patterns across all your meetings.
struct NotesInsights: View {
    let overview: MeetingsOverview
    var person: (String) -> Void = { _ in }

    var body: some View {
        if overview.count == 0 {
            Card(padding: 28) { Text("Insights appear after your first meeting.").font(Theme.display(20)) }
        } else {
            VStack(spacing: 20) {
                HStack(alignment: .top, spacing: 20) {
                    stat("calendar", "\(overview.count)", "Meetings", "Recorded on this Mac.")
                    stat("clock", minutes(overview.totalSeconds), "In meetings", "Average \(minutes(overview.averageSeconds)) each.")
                    stat("person.wave.2", overview.myShare.map { "\($0)%" } ?? "–", "You talked",
                         "Your average share of talk time.")
                    stat("checklist", "\(overview.openActionItems)", "Action items", "Across all summaries.")
                }
                .fixedSize(horizontal: false, vertical: true)
                Card(padding: 20) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Who you meet with most").font(.system(size: 20, weight: .medium))
                        ForEach(overview.people, id: \.name) { person in
                            HStack(spacing: 10) {
                                Initials(name: person.name, size: 28)
                                Text(person.name).font(.system(size: 14))
                                Spacer()
                                Text("\(person.meetings) meeting\(person.meetings == 1 ? "" : "s")")
                                    .font(.system(size: 12)).foregroundStyle(Theme.secondary)
                                Image(systemName: "chevron.right").font(.system(size: 11)).foregroundStyle(Theme.secondary)
                            }
                            .contentShape(Rectangle())
                            .onTapGesture { self.person(person.name) }
                        }
                        if let day = overview.busiestWeekday {
                            Text("Your busiest meeting day is \(Calendar.current.weekdaySymbols[day - 1]).")
                                .font(.system(size: 12)).foregroundStyle(Theme.secondary).padding(.top, 4)
                        }
                    }
                }
            }
        }
    }

    private func minutes(_ seconds: Double) -> String {
        let m = Int((seconds / 60).rounded())
        return m >= 60 ? "\(m / 60) h \(m % 60) m" : "\(m) min"
    }

    private func stat(_ symbol: String, _ value: String, _ label: String, _ detail: String) -> some View {
        Card(padding: 18) {
            VStack(alignment: .leading, spacing: 6) {
                Image(systemName: symbol).font(.system(size: 15)).foregroundStyle(Theme.accent)
                Text(value).font(.system(size: 24, weight: .medium))
                Text(label.uppercased()).font(.system(size: 10.5, weight: .medium)).tracking(0.8).foregroundStyle(Theme.secondary)
                Text(detail).font(.system(size: 12)).foregroundStyle(Theme.secondary)
            }
        }
    }
}

/// One meeting: who was there, the summary, the transcript, its insights, and your notes.
struct MeetingDetailView: View {
    let meeting: Meeting
    let back: () -> Void
    var person: (String) -> Void = { _ in }
    @State private var tab: String

    init(meeting: Meeting, back: @escaping () -> Void, person: @escaping (String) -> Void = { _ in }, initialTab: String = "Summary") {
        self.meeting = meeting
        self.back = back
        self.person = person
        _tab = State(initialValue: initialTab)
    }
    private var insights: MeetingInsights { MeetingInsights(meeting) }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                Button(action: back) {
                    Label("All notes", systemImage: "chevron.left").font(.system(size: 13))
                }
                .buttonStyle(.plain).foregroundStyle(Theme.secondary).padding(.bottom, 16)
                HStack(spacing: 8) {
                    Text(meeting.title).font(Theme.display(30))
                    if meeting.sample == true { Badge(text: "Sample") }
                }
                Text([meeting.startedAt.formatted(.dateTime.weekday(.wide).month(.abbreviated).day().hour().minute()),
                      meeting.durationText, meeting.app].compactMap { $0 }.joined(separator: " · "))
                    .font(.system(size: 13)).foregroundStyle(Theme.secondary).padding(.top, 6)
                people.padding(.top, 18)
                HStack(spacing: 22) {
                    ForEach(["Summary", "Transcript", "Insights", "My thoughts"], id: \.self) { name in
                        Button { tab = name } label: {
                            VStack(spacing: 8) {
                                Text(name).font(.system(size: 14, weight: tab == name ? .semibold : .regular))
                                    .foregroundStyle(tab == name ? Theme.text : Theme.secondary)
                                Rectangle().fill(tab == name ? Theme.text : .clear).frame(height: 2)
                            }
                            .fixedSize()
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.top, 26)
                Divider().overlay(Theme.cardStroke).padding(.bottom, 22)
                switch tab {
                case "Transcript": transcript
                case "Insights": insightsTab
                case "My thoughts": thoughts
                default: summary
                }
            }
            .padding(.horizontal, 40).padding(.vertical, 30)
            .frame(maxWidth: 1000, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
    }

    private var people: some View {
        HStack(spacing: 10) {
            ForEach(meeting.participants, id: \.name) { p in
                HStack(spacing: 8) {
                    Initials(name: p.name, size: 28)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(p.name + (p.isMe == true ? " (you)" : "")).font(.system(size: 13, weight: .medium))
                        if let role = p.role { Text(role).font(.system(size: 11)).foregroundStyle(Theme.secondary) }
                    }
                }
                .padding(.vertical, 6).padding(.leading, 6).padding(.trailing, 12)
                .background(Capsule().fill(Theme.card))
                .contentShape(Capsule())
                .onTapGesture { if p.isMe != true { person(p.name) } }
                .help(p.isMe == true ? "" : "See all your meetings with \(p.name)")
            }
        }
    }

    @ViewBuilder private var summary: some View {
        if let s = meeting.summary {
            VStack(alignment: .leading, spacing: 18) {
                Card(padding: 20) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Overview").font(.system(size: 15, weight: .semibold))
                        Text(s.overview).font(.system(size: 14)).fixedSize(horizontal: false, vertical: true)
                    }
                }
                if !s.actionItems.isEmpty {
                    Card(padding: 20) {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Action items").font(.system(size: 15, weight: .semibold))
                            ForEach(s.actionItems, id: \.self) { item in
                                HStack(alignment: .top, spacing: 10) {
                                    Image(systemName: "circle").font(.system(size: 13)).foregroundStyle(Theme.secondary).padding(.top, 2)
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(item.task).font(.system(size: 14))
                                        Text([item.owner, item.due].compactMap { $0 }.joined(separator: " · "))
                                            .font(.system(size: 12)).foregroundStyle(Theme.secondary)
                                    }
                                }
                            }
                        }
                    }
                }
                HStack(alignment: .top, spacing: 18) {
                    bullets("Decisions", "checkmark.seal", s.decisions)
                    bullets("Open questions", "questionmark.circle", s.openQuestions)
                }
                .fixedSize(horizontal: false, vertical: true)
            }
        } else {
            Card { Text("No summary yet.").foregroundStyle(Theme.secondary) }
        }
    }

    private func bullets(_ title: String, _ symbol: String, _ items: [String]) -> some View {
        Card(padding: 20) {
            VStack(alignment: .leading, spacing: 10) {
                Label(title, systemImage: symbol).font(.system(size: 15, weight: .semibold))
                if items.isEmpty { Text("None").font(.system(size: 13)).foregroundStyle(Theme.secondary) }
                ForEach(items, id: \.self) { Text("• " + $0).font(.system(size: 14)).fixedSize(horizontal: false, vertical: true) }
            }
        }
    }

    private var transcript: some View {
        LazyVStack(alignment: .leading, spacing: 16) {
            ForEach(Array(meeting.transcript.enumerated()), id: \.offset) { _, line in
                HStack(alignment: .top, spacing: 12) {
                    Initials(name: line.speaker, size: 26)
                    VStack(alignment: .leading, spacing: 3) {
                        HStack(spacing: 8) {
                            Text(line.speaker).font(.system(size: 13, weight: .semibold))
                            Text(String(format: "%d:%02d", Int(line.startS) / 60, Int(line.startS) % 60))
                                .font(.system(size: 11)).monospacedDigit().foregroundStyle(Theme.secondary)
                        }
                        Text(line.text).font(.system(size: 14)).textSelection(.enabled).fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
    }

    private var insightsTab: some View {
        let i = insights
        return VStack(spacing: 20) {
            Card(padding: 20) {
                VStack(alignment: .leading, spacing: 14) {
                    Text("Talk time").font(.system(size: 20, weight: .medium))
                    GeometryReader { geo in
                        HStack(spacing: 2) {
                            ForEach(i.speakers) { s in
                                Rectangle().fill(color(for: s.name)).frame(width: max(2, geo.size.width * CGFloat(s.share) / 100))
                            }
                        }
                        .clipShape(Capsule())
                    }
                    .frame(height: 12)
                    ForEach(i.speakers) { s in
                        HStack(spacing: 10) {
                            Circle().fill(color(for: s.name)).frame(width: 10, height: 10)
                            Text(s.name).font(.system(size: 14))
                            Spacer()
                            Text("\(s.share)% · \(Int(s.seconds / 60)):\(String(format: "%02d", Int(s.seconds) % 60)) · \(s.words) words · \(s.wpm) wpm · \(s.questions) questions")
                                .font(.system(size: 12)).monospacedDigit().foregroundStyle(Theme.secondary)
                        }
                    }
                }
            }
            HStack(alignment: .top, spacing: 20) {
                fact("timer", i.longestMonologue.map { "\(Int($0.seconds / 60))m \(Int($0.seconds) % 60)s" } ?? "–", "Longest stretch",
                     i.longestMonologue.map { "\($0.speaker) talked without a break." } ?? "")
                fact("arrow.left.arrow.right", String(format: "%.1f", i.turnsPerMinute), "Turns per minute",
                     i.turnsPerMinute > 2.5 ? "A lively back-and-forth." : "Longer turns, fewer handoffs.")
                fact("questionmark.bubble", "\(i.questions)", "Questions asked", "Across everyone in the call.")
            }
            .fixedSize(horizontal: false, vertical: true)
            if !i.topics.isEmpty {
                Card(padding: 20) {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("What came up most").font(.system(size: 20, weight: .medium))
                        FlowLayout(spacing: 8) {
                            ForEach(i.topics, id: \.self) { topic in
                                Text(topic).font(.system(size: 13))
                                    .padding(.horizontal, 10).padding(.vertical, 5)
                                    .background(Capsule().fill(Theme.accentSoft))
                            }
                        }
                    }
                }
            }
        }
    }

    private func color(for name: String) -> Color {
        let index = meeting.participants.firstIndex { $0.name == name } ?? 0
        return Color(nsColor: Theme.nsColor(hex: Initials.colors[index % Initials.colors.count]))
    }

    private func fact(_ symbol: String, _ value: String, _ label: String, _ detail: String) -> some View {
        Card(padding: 18) {
            VStack(alignment: .leading, spacing: 6) {
                Image(systemName: symbol).font(.system(size: 15)).foregroundStyle(Theme.accent)
                Text(value).font(.system(size: 24, weight: .medium))
                Text(label.uppercased()).font(.system(size: 10.5, weight: .medium)).tracking(0.8).foregroundStyle(Theme.secondary)
                Text(detail).font(.system(size: 12)).foregroundStyle(Theme.secondary)
            }
        }
    }

    @ViewBuilder private var thoughts: some View {
        let text = meeting.myThoughts ?? ""
        Card(padding: 20) {
            Text(text.isEmpty ? "You didn't write any notes during this meeting." : text)
                .font(.system(size: 14)).foregroundStyle(text.isEmpty ? Theme.secondary : Theme.text)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
