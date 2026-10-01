import AVFoundation
import MisprCore
import SwiftUI

struct HomeView: View {
    @EnvironmentObject var model: AppModel
    @StateObject private var player = Player()
    @State private var query = ""
    @State private var searching = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                greeting
                HStack(alignment: .top, spacing: 20) {
                    history.frame(maxWidth: .infinity)
                    VStack(spacing: 14) {
                        statsCard
                        tipsCard
                    }
                    .frame(width: 232)
                }
            }
            .padding(.horizontal, 40).padding(.vertical, 36)
            .frame(maxWidth: 1100)
            .frame(maxWidth: .infinity)
        }
    }

    private var greeting: some View {
        HStack(spacing: 8) {
            Text("Hey \(model.firstName), get back into the flow with").font(.system(size: 24, weight: .semibold))
            Text("fn").font(.system(size: 20, weight: .semibold, design: .rounded))
                .padding(.horizontal, 7).padding(.vertical, 1)
                .background(RoundedRectangle(cornerRadius: 6).fill(Theme.key.opacity(0.85)))
                .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.black.opacity(0.25)))
                .foregroundStyle(Color.black.opacity(0.8))
        }
    }

    // MARK: - History

    private var filtered: [Recording] {
        let q = query.trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else { return model.recordings }
        return model.recordings.filter { $0.transcript.localizedCaseInsensitiveContains(q) }
    }

    private var history: some View {
        VStack(alignment: .leading, spacing: 0) {
            let groups = DayGroup.group(filtered)
            if groups.isEmpty {
                HStack { sectionHeader(model.recordings.isEmpty ? "History" : "No matches"); Spacer(); searchControl }
                emptyState
            }
            ForEach(Array(groups.enumerated()), id: \.element.id) { index, group in
                HStack {
                    sectionHeader(group.title)
                    Spacer()
                    if index == 0 { searchControl }
                }
                .padding(.top, index == 0 ? 0 : 22)
                VStack(spacing: 0) {
                    ForEach(group.records) { record in
                        HistoryRow(record: record, player: player)
                        if record.id != group.records.last?.id { Divider().overlay(Theme.cardStroke) }
                    }
                }
                .background(RoundedRectangle(cornerRadius: 12).stroke(Theme.cardStroke))
            }
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
                Text(model.recordings.isEmpty ? "Your dictations will appear here" : "Nothing matches “\(query)”")
                    .font(Theme.display(20))
                Text(model.recordings.isEmpty
                     ? "Hold fn anywhere and speak. Incognito dictations are never saved."
                     : "Search looks through the text of every saved dictation.")
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
                tip("Hold fn", "talk, release to paste")
                tip("Double-tap fn", "hands-free")
                tip("space", "finish hands-free")
                tip("fn / delete", "cancel hands-free")
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
    @ObservedObject var player: Player
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
                    Text(record.transcript).font(.system(size: 13)).textSelection(.enabled)
                        .fixedSize(horizontal: false, vertical: true)
                }
                if record.status == .copied {
                    Text("No text box · copied to clipboard").font(.system(size: 11)).foregroundStyle(Theme.secondary)
                }
                if hovering, let app = record.app?.app {
                    Text(app + (record.app?.pageTitle.map { " · \($0)" } ?? ""))
                        .font(.system(size: 11)).foregroundStyle(Theme.secondary).lineLimit(1)
                }
            }
            Spacer(minLength: 8)
            actions.opacity(hovering ? 1 : 0)
        }
        .padding(.horizontal, 16).padding(.vertical, 12)
        .background(hovering ? Theme.card.opacity(0.6) : Color.clear)
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
                iconButton(player.playing == record.id ? "stop.fill" : "play.fill", player.playing == record.id ? "Stop" : "Play recording") {
                    player.toggle(record)
                }
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
