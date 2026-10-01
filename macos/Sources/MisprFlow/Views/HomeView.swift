import AVFoundation
import MisprCore
import SwiftUI

struct HomeView: View {
    @EnvironmentObject var model: AppModel
    @StateObject private var player = Player()
    @State private var query = ""
    @State private var searching = false
    @State private var groups: [DayGroup] = []  // grouped once per change, not on every redraw
    /// History tab: dictation (false) or voice commands (true).
    @State private var showCommands: Bool

    init(showCommands: Bool = false) {
        _showCommands = State(initialValue: showCommands)
    }

    var body: some View {
        // Only the history scrolls (lazily); the greeting and side cards stay put.
        VStack(alignment: .leading, spacing: 22) {
            greeting.padding(.top, 36)
            HStack(alignment: .top, spacing: 20) {
                history.frame(maxWidth: .infinity)
                VStack(spacing: 14) {
                    statsCard
                    tipsCard
                    commandsCard
                }
                .frame(width: 232)
            }
        }
        .padding(.horizontal, 40)
        .frame(maxWidth: 1100, maxHeight: .infinity, alignment: .topLeading)
        .frame(maxWidth: .infinity)
        .onAppear(perform: regroup)
        .onChange(of: model.recordings) { regroup() }
        .onChange(of: query) { regroup() }
        .onChange(of: showCommands) { regroup() }
    }

    private func regroup() {
        groups = DayGroup.group(filtered)
    }

    private var greeting: some View {
        HStack(spacing: 8) {
            Text("Hey \(model.firstName), get back into the flow with").font(.system(size: 24, weight: .semibold))
            Text(model.dictationKey.label).font(.system(size: 20, weight: .semibold, design: .rounded))
                .padding(.horizontal, 7).padding(.vertical, 1)
                .background(RoundedRectangle(cornerRadius: 6).fill(Theme.key.opacity(0.85)))
                .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.black.opacity(0.25)))
                .foregroundStyle(Color.black.opacity(0.8))
        }
    }

    // MARK: - History

    private var filtered: [Recording] {
        let tab = Self.tab(model.recordings, commands: showCommands)
        let q = query.trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else { return tab }
        return tab.filter { $0.transcript.localizedCaseInsensitiveContains(q) }
    }

    /// One history tab: voice commands, or everything else (dictation, including cancelled).
    static func tab(_ records: [Recording], commands: Bool) -> [Recording] {
        records.filter { ($0.status == .command) == commands }
    }

    private var historyTabs: some View {
        HStack(spacing: 18) {
            ForEach([false, true], id: \.self) { commands in
                Button { showCommands = commands } label: {
                    VStack(spacing: 6) {
                        Text(commands ? "Commands" : "Dictation")
                            .font(.system(size: 13, weight: showCommands == commands ? .semibold : .regular))
                            .foregroundStyle(showCommands == commands ? Theme.text : Theme.secondary)
                        Rectangle().fill(showCommands == commands ? Theme.text : .clear).frame(height: 2)
                    }
                    .fixedSize()
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.bottom, 12)
    }

    private var history: some View {
        VStack(alignment: .leading, spacing: 0) {
            historyTabs
            HStack {
                sectionHeader(groups.first?.title ?? (model.recordings.isEmpty ? "History" : "No matches"))
                Spacer()
                searchControl
            }
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    if groups.isEmpty { emptyState }
                    ForEach(Array(groups.enumerated()), id: \.element.id) { index, group in
                        if index > 0 { sectionHeader(group.title).padding(.top, 22) }
                        ForEach(group.records) { record in
                            HistoryRow(record: record, playing: player.playing == record.id) { player.toggle(record) }
                            if record.id != group.records.last?.id { Divider().overlay(Theme.cardStroke) }
                        }
                    }
                }
                .padding(.bottom, 28)
            }
            .scrollIndicators(.automatic)
        }
    }

    private func sectionHeader(_ title: String) -> some View {
        Text(title.uppercased()).font(.system(size: 11, weight: .semibold)).tracking(0.8)
            .foregroundStyle(Theme.secondary).padding(.bottom, 8)
    }

    private var searchControl: some View {
        HStack(spacing: 6) {
            if searching {
                TextField("Search", text: $query).textFieldStyle(.plain).frame(width: 180)
                    .onExitCommand { query = ""; searching = false }
            }
            Button { searching.toggle(); if !searching { query = "" } } label: {
                Image(systemName: searching ? "xmark" : "magnifyingglass")
            }
            .buttonStyle(.plain).foregroundStyle(Theme.secondary).help("Search history")
        }
        .padding(.bottom, 8)
    }

    private var emptyState: some View {
        Card(padding: 28) {
            VStack(alignment: .leading, spacing: 6) {
                let none = Self.tab(model.recordings, commands: showCommands).isEmpty
                Text(none ? (showCommands ? "Your voice commands will appear here" : "Your dictations will appear here")
                     : "Nothing matches “\(query)”")
                    .font(Theme.display(20))
                Text(none
                     ? (showCommands ? "Hold your app switcher key and say “Chrome” or “new tab”."
                        : "Hold fn anywhere and speak. Incognito dictations are never saved.")
                     : "Search looks through the text of every saved \(showCommands ? "command" : "dictation").")
                    .font(.system(size: 13)).foregroundStyle(Theme.secondary)
            }
        }
    }

    // MARK: - Side cards

    private var statsCard: some View {
        Card {
            VStack(alignment: .leading, spacing: 10) {
                stat(model.stats.totalWords.formatted(), "total words")
                stat("\(model.stats.wordsPerMinute)", "wpm")
                stat("\(model.stats.currentStreak)", model.stats.currentStreak == 1 ? "day streak" : "day streak")
            }
        }
    }

    private func stat(_ value: String, _ label: String) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 6) {
            Text(value).font(Theme.display(24))
            Text(label).font(.system(size: 14)).foregroundStyle(Theme.secondary)
        }
    }

    private var tipsCard: some View {
        Card {
            VStack(alignment: .leading, spacing: 8) {
                Text("Shortcuts").font(.system(size: 14, weight: .semibold))
                let key = model.dictationKey.label
                tip("Hold \(key)", "talk, release to paste")
                tip("Double-tap \(key)", "hands-free")
                tip("space", "finish hands-free")
                tip("\(key) / delete", "cancel hands-free")
            }
        }
    }

    /// The most useful voice commands (the full set is in the app switcher's help).
    static let commands: [(say: String, does: String)] = [
        ("Chrome", "switch to an app"),
        ("Chrome beside Code", "side by side"),
        ("new tab / close tab", "in the app in front"),
        ("scroll down", "or page up"),
        ("pause / volume up", "media and sound"),
        ("mute mic", "unmute the same way"),
    ]

    private var commandsCard: some View {
        Card {
            VStack(alignment: .leading, spacing: 8) {
                Text("Voice commands").font(.system(size: 14, weight: .semibold))
                if let key = model.switchKey {
                    Text("Hold \(key.label), say it, let go").font(.system(size: 12)).foregroundStyle(Theme.secondary)
                    ForEach(Self.commands, id: \.say) { tip($0.say, $0.does) }
                } else {
                    Button("Set an app switcher key") {
                        model.settingsSection = .general
                        model.showSettings = true
                    }
                    .buttonStyle(.link).font(.system(size: 12))
                }
            }
        }
    }

    private func tip(_ key: String, _ what: String) -> some View {
        HStack(spacing: 6) {
            Text(key).font(.system(size: 12, weight: .medium))
                .padding(.horizontal, 6).padding(.vertical, 2)
                .background(RoundedRectangle(cornerRadius: 5).fill(Theme.content))
            Text(what).font(.system(size: 12)).foregroundStyle(Theme.secondary)
        }
    }
}

/// Recordings for one calendar day.
struct DayGroup: Identifiable {
    let day: Date
    let records: [Recording]
    var id: Date { day }

    var title: String {
        let calendar = Calendar.current
        if calendar.isDateInToday(day) { return "Today" }
        if calendar.isDateInYesterday(day) { return "Yesterday" }
        return day.formatted(.dateTime.weekday(.wide).month(.abbreviated).day())
    }

    static func group(_ records: [Recording]) -> [DayGroup] {
        let calendar = Calendar.current
        let byDay = Dictionary(grouping: records) { calendar.startOfDay(for: $0.startedAt) }
        return byDay.keys.sorted(by: >).map { DayGroup(day: $0, records: byDay[$0]!) }
    }
}

struct HistoryRow: View {
    @EnvironmentObject var model: AppModel
    let record: Recording
    let playing: Bool  // a plain value: rows don't redraw when another row starts playing
    let onPlay: () -> Void
    @State private var hovering = false
    @State private var copied = false
    @State private var confirmDelete = false

    var body: some View {
        HStack(alignment: .top, spacing: 18) {
            Text(record.startedAt.formatted(.dateTime.hour().minute()).lowercased().replacingOccurrences(of: " ", with: ""))
                .font(.system(size: 12)).foregroundStyle(Theme.secondary)
                .frame(width: 62, alignment: .leading).padding(.top, 1)
            VStack(alignment: .leading, spacing: 4) {
                if record.status == .cancelled {
                    Text("Cancelled recording · \(Int(record.durationS.rounded()))s")
                        .font(.system(size: 13)).italic().foregroundStyle(Theme.secondary)
                } else {
                    Text(record.transcript).font(.system(size: 13))
                        .fixedSize(horizontal: false, vertical: true)
                }
                if record.status == .copied {
                    Text("No text box · copied to clipboard").font(.system(size: 11)).foregroundStyle(Theme.secondary)
                }
                if record.status == .command {
                    Label("Voice command", systemImage: "command").font(.system(size: 11)).foregroundStyle(Theme.accent)
                }
                if hovering, let app = record.app?.app {
                    Text(app + (record.app?.pageTitle.map { " · \($0)" } ?? ""))
                        .font(.system(size: 11)).foregroundStyle(Theme.secondary).lineLimit(1)
                }
            }
            Spacer(minLength: 8)
            actions.opacity(hovering ? 1 : 0)
        }
        .padding(.horizontal, 14).padding(.vertical, 12)
        .background(RoundedRectangle(cornerRadius: 8).fill(hovering ? Theme.card : Color.clear))
        .contentShape(Rectangle())
        .onHover { hovering = $0 }
        .confirmationDialog("Delete this dictation?", isPresented: $confirmDelete) {
            Button("Delete", role: .destructive) { model.delete(record) }
        } message: {
            Text("Its text and audio are removed from your Mac.")
        }
    }

    private var actions: some View {
        HStack(spacing: 10) {
            if record.audioURL != nil {
                iconButton(playing ? "stop.fill" : "play.fill", playing ? "Stop" : "Play recording", action: onPlay)
            }
            if record.status != .cancelled {
                iconButton(copied ? "checkmark" : "doc.on.doc", "Copy text") {
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(record.transcript, forType: .string)
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) { copied = false }
                }
            }
            Menu {
                if let url = record.fileURL {
                    Button("Show in Finder") { NSWorkspace.shared.activateFileViewerSelecting([url]) }
                }
                if record.wasCleaned, let raw = record.rawTranscript {
                    Button("Copy original (before cleanup)") {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(raw, forType: .string)
                    }
                }
                Divider()
                Button("Delete…", role: .destructive) { confirmDelete = true }
            } label: {
                Image(systemName: "ellipsis")
            }
            .menuStyle(.borderlessButton).menuIndicator(.hidden).fixedSize()
        }
        .foregroundStyle(Theme.secondary)
    }

    private func iconButton(_ symbol: String, _ help: String, action: @escaping () -> Void) -> some View {
        Button(action: action) { Image(systemName: symbol).font(.system(size: 12)) }
            .buttonStyle(.plain).help(help)
    }
}

/// Plays one saved recording at a time.
final class Player: NSObject, ObservableObject, AVAudioPlayerDelegate {
    @Published private(set) var playing: String?
    private var audio: AVAudioPlayer?

    func toggle(_ record: Recording) {
        if playing == record.id { stop(); return }
        stop()
        guard let url = record.audioURL, let audio = try? AVAudioPlayer(contentsOf: url) else { return }
        audio.delegate = self
        audio.play()
        self.audio = audio
        playing = record.id
    }

    func stop() {
        audio?.stop()
        audio = nil
        playing = nil
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        DispatchQueue.main.async { self.stop() }
    }
}
