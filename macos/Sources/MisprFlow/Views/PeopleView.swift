import MisprCore
import SwiftUI

/// Everyone from your meetings. Click a person to see them; ⌘-click (or the checkmarks) to
/// pick several and see only the meetings you were all in.
struct PeopleView: View {
    let meetings: [Meeting]
    @Binding var selected: Set<String>
    let open: (Meeting) -> Void
    @State private var query = ""

    private var people: [PeopleIndex.Person] {
        let all = PeopleIndex.people(meetings)
        let q = query.trimmingCharacters(in: .whitespaces)
        return q.isEmpty ? all : all.filter { $0.name.localizedCaseInsensitiveContains(q) || ($0.role ?? "").localizedCaseInsensitiveContains(q) }
    }

    var body: some View {
        HStack(alignment: .top, spacing: 24) {
            list.frame(width: 300)
            detail.frame(maxWidth: .infinity, alignment: .topLeading)
        }
    }

    // MARK: - List

    private var list: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: "magnifyingglass").foregroundStyle(Theme.secondary)
                TextField("Search people", text: $query).textFieldStyle(.plain)
            }
            .font(.system(size: 13)).padding(10)
            .background(RoundedRectangle(cornerRadius: 10).fill(Theme.card))
            HStack {
                Text(selected.count > 1 ? "\(selected.count) selected" : "Tip: ⌘-click to pick several")
                    .font(.system(size: 11)).foregroundStyle(Theme.secondary)
                Spacer()
                if !selected.isEmpty {
                    Button("Clear") { selected = [] }.buttonStyle(.link).font(.system(size: 11))
                }
            }
            LazyVStack(spacing: 4) {
                ForEach(people) { person in
                    PersonRow(person: person, selected: selected.contains(person.name)) { additive in
                        if additive || NSEvent.modifierFlags.contains(.command) {
                            if selected.contains(person.name) { selected.remove(person.name) } else { selected.insert(person.name) }
                        } else {
                            selected = selected == [person.name] ? [] : [person.name]
                        }
                    }
                }
            }
            if people.isEmpty {
                Text(meetings.isEmpty ? "People appear after your first meeting." : "No one matches.")
                    .font(.system(size: 13)).foregroundStyle(Theme.secondary).padding(.top, 8)
            }
        }
    }

    // MARK: - Detail

    @ViewBuilder private var detail: some View {
        if selected.isEmpty {
            Card(padding: 28) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Pick someone").font(Theme.display(22))
                    Text("See every meeting you've had with them, what you talk about, and what they owe you. ⌘-click several people to see only the meetings you were all in.")
                        .font(.system(size: 13)).foregroundStyle(Theme.secondary).fixedSize(horizontal: false, vertical: true)
                }
            }
        } else {
            let names = selected
            let group = PeopleIndex.group(meetings, names: names)
            let shared = PeopleIndex.together(meetings, names: names)
            VStack(alignment: .leading, spacing: 18) {
                header(names, group)
                HStack(alignment: .top, spacing: 14) {
                    stat("\(group.meetings)", group.meetings == 1 ? "Meeting together" : "Meetings together")
                    stat(minutes(group.seconds), "Time together")
                    stat(minutes(group.averageSeconds), "Average meeting")
                    stat(group.lastMet.map { $0.formatted(.relative(presentation: .named)) } ?? "–", "Last met")
                }
                .fixedSize(horizontal: false, vertical: true)
                if group.meetings > 0 { talk(names, group) }
                if !group.topics.isEmpty {
                    Card(padding: 18) {
                        VStack(alignment: .leading, spacing: 10) {
                            Text(names.count == 1 ? "What you talk about" : "What you all talk about").font(.system(size: 16, weight: .semibold))
                            FlowLayout(spacing: 8) {
                                ForEach(group.topics, id: \.self) { topic in
                                    Text(topic).font(.system(size: 13)).padding(.horizontal, 10).padding(.vertical, 5)
                                        .background(Capsule().fill(Theme.accentSoft))
                                }
                            }
                        }
                    }
                }
                actionItems(names)
                VStack(alignment: .leading, spacing: 6) {
                    Text(names.count == 1 ? "MEETINGS TOGETHER" : "MEETINGS YOU WERE ALL IN")
                        .font(.system(size: 11, weight: .semibold)).tracking(0.8).foregroundStyle(Theme.secondary)
                    if shared.isEmpty {
                        Text("These people haven't all been in the same meeting yet.").font(.system(size: 13)).foregroundStyle(Theme.secondary)
                    }
                    ForEach(shared) { meeting in
                        NoteRow(meeting: meeting).onTapGesture { open(meeting) }
                    }
                }
            }
        }
    }

    private func header(_ names: Set<String>, _ group: PeopleIndex.Group) -> some View {
        let sorted = names.sorted()
        let person = PeopleIndex.people(meetings).first { $0.name == sorted.first }
        return HStack(spacing: 14) {
            PeopleStack(names: sorted, size: 44)
            VStack(alignment: .leading, spacing: 3) {
                Text(sorted.count == 1 ? sorted[0] : sorted.joined(separator: ", ")).font(Theme.display(26)).lineLimit(2)
                if sorted.count == 1, let person {
                    Text([person.role, "First met \(person.firstMet.formatted(.dateTime.month(.abbreviated).day()))"]
                            .compactMap { $0 }.joined(separator: " · "))
                        .font(.system(size: 13)).foregroundStyle(Theme.secondary)
                } else {
                    Text("Meetings where all \(sorted.count) of them were present")
                        .font(.system(size: 13)).foregroundStyle(Theme.secondary)
                }
            }
        }
    }

    private func talk(_ names: Set<String>, _ group: PeopleIndex.Group) -> some View {
        Card(padding: 18) {
            VStack(alignment: .leading, spacing: 10) {
                Text("How much they talk").font(.system(size: 16, weight: .semibold))
                ForEach(names.sorted(), id: \.self) { name in
                    HStack(spacing: 10) {
                        Initials(name: name, size: 24)
                        Text(name).font(.system(size: 13)).frame(width: 130, alignment: .leading)
                        GeometryReader { geo in
                            ZStack(alignment: .leading) {
                                Capsule().fill(Theme.cardStroke)
                                Capsule().fill(Theme.accent).frame(width: geo.size.width * CGFloat(group.talkShare[name] ?? 0) / 100)
                            }
                        }
                        .frame(height: 8)
                        let asked = group.questions[name] ?? 0
                        Text("\(group.talkShare[name] ?? 0)% · \(asked) question\(asked == 1 ? "" : "s")")
                            .font(.system(size: 12)).monospacedDigit().foregroundStyle(Theme.secondary).frame(width: 120, alignment: .trailing)
                    }
                }
                Text("Average share of talk time in the meetings above.").font(.system(size: 11)).foregroundStyle(Theme.secondary)
            }
        }
    }

    @ViewBuilder private func actionItems(_ names: Set<String>) -> some View {
        let items = names.sorted().flatMap { name in PeopleIndex.actionItems(meetings, for: name).map { (name, $0.meeting, $0.item) } }
        if !items.isEmpty {
            Card(padding: 18) {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Their action items").font(.system(size: 16, weight: .semibold))
                    ForEach(Array(items.enumerated()), id: \.offset) { _, entry in
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: "circle").font(.system(size: 12)).foregroundStyle(Theme.secondary).padding(.top, 2)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(entry.2.task).font(.system(size: 13))
                                Text([names.count > 1 ? entry.0 : nil, entry.2.due, "from “\(entry.1.title)”"].compactMap { $0 }.joined(separator: " · "))
                                    .font(.system(size: 11)).foregroundStyle(Theme.secondary)
                            }
                            Spacer()
                        }
                        .contentShape(Rectangle())
                        .onTapGesture { open(entry.1) }
                    }
                }
            }
        }
    }

    private func stat(_ value: String, _ label: String) -> some View {
        Card(padding: 14) {
            VStack(alignment: .leading, spacing: 4) {
                Text(value).font(.system(size: 20, weight: .medium)).lineLimit(1).minimumScaleFactor(0.7)
                Text(label.uppercased()).font(.system(size: 10, weight: .medium)).tracking(0.7).foregroundStyle(Theme.secondary)
            }
        }
    }

    private func minutes(_ seconds: Double) -> String {
        let m = Int((seconds / 60).rounded())
        return m >= 60 ? "\(m / 60) h \(m % 60) m" : "\(m) min"
    }
}

struct PersonRow: View {
    let person: PeopleIndex.Person
    let selected: Bool
    let tap: (_ additive: Bool) -> Void
    @State private var hovering = false

    var body: some View {
        HStack(spacing: 10) {
            Initials(name: person.name, size: 32)
            VStack(alignment: .leading, spacing: 2) {
                Text(person.name).font(.system(size: 13, weight: .medium))
                Text("\(person.meetings) meeting\(person.meetings == 1 ? "" : "s") · last \(person.lastMet.formatted(.dateTime.month(.abbreviated).day()))")
                    .font(.system(size: 11)).foregroundStyle(Theme.secondary)
            }
            Spacer()
            Button { tap(true) } label: {
                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(selected ? Theme.accent : Theme.secondary.opacity(hovering ? 1 : 0.4))
            }
            .buttonStyle(.plain).help("Add to selection")
        }
        .padding(8)
        .background(RoundedRectangle(cornerRadius: 10).fill(selected ? Theme.selection : hovering ? Theme.card : .clear))
        .contentShape(Rectangle())
        .onTapGesture { tap(false) }
        .onHover { hovering = $0 }
    }
}
