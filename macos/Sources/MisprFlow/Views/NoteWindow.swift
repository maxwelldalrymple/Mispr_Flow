import AppKit
import Combine
import CoreGraphics
import MisprCore
import SwiftUI

/// The note side window: opened by the widget's ◉ button, it slides in at the right edge of
/// the screen you're on (like Wispr Flow's Notetaker) and runs the meeting from there.
final class NoteWindowController {
    private var window: NSWindow?
    private let model: AppModel
    static let width: CGFloat = 470
    static let margin: CGFloat = 8

    init(model: AppModel) {
        self.model = model
    }

    func show() {
        let screen = NSScreen.screens.first { $0.frame.contains(NSEvent.mouseLocation) } ?? NSScreen.main ?? NSScreen.screens[0]
        let visible = screen.visibleFrame
        let target = NSRect(x: visible.maxX - Self.width - Self.margin, y: visible.minY + Self.margin,
                            width: Self.width, height: visible.height - 2 * Self.margin)
        let window = self.window ?? makeWindow()
        self.window = window
        model.note.refreshPermission()
        model.note.startDetecting()
        if window.isVisible {
            window.setFrame(target, display: true, animate: true)
        } else {
            window.setFrame(target.offsetBy(dx: Self.width + Self.margin * 2, dy: 0), display: false)
            window.alphaValue = 0
            window.orderFrontRegardless()
            NSAnimationContext.runAnimationGroup { context in
                context.duration = 0.28
                context.timingFunction = CAMediaTimingFunction(name: .easeOut)
                window.animator().setFrame(target, display: true)
                window.animator().alphaValue = 1
            }
        }
        window.makeKey()
        NSApp.activate(ignoringOtherApps: true)
    }

    func close() {
        guard let window, window.isVisible else { return }
        let off = window.frame.offsetBy(dx: Self.width + Self.margin * 2, dy: 0)
        NSAnimationContext.runAnimationGroup({ context in
            context.duration = 0.22
            context.timingFunction = CAMediaTimingFunction(name: .easeIn)
            window.animator().setFrame(off, display: true)
            window.animator().alphaValue = 0
        }, completionHandler: { window.orderOut(nil) })
        model.note.stopDetecting()
    }

    private func makeWindow() -> NSWindow {
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: Self.width, height: 700),
                              styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                              backing: .buffered, defer: false)
        window.title = "New note"
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true
        window.isMovableByWindowBackground = true
        window.isReleasedWhenClosed = false
        window.minSize = NSSize(width: 380, height: 480)
        window.collectionBehavior = [.moveToActiveSpace, .fullScreenAuxiliary]
        let host = NSHostingView(rootView: ThemedRoot { NoteView(close: { [weak self] in self?.close() }) }
            .environmentObject(model).environmentObject(model.note))
        // Don't let the window grow to fit its content (a long transcript made it taller than
        // the screen): the window keeps the size we give it and the transcript scrolls.
        host.sizingOptions = []
        window.contentView = host
        return window
    }
}

/// One meeting note being taken: the recording, the live transcript, your notes, the summary
/// and answers, and the Screen & System Audio permission calls need.
final class NoteModel: ObservableObject {
    enum Tab: String, CaseIterable {
        case thoughts = "My thoughts"
        case transcript = "Transcript"
        case summary = "Summary"
    }

    enum Phase: Equatable { case ready, recording, finishing, done }

    @Published var tab: Tab = .transcript
    @Published var thoughts = ""
    @Published var title = ""
    @Published var screenAudioAllowed = CGPreflightScreenCaptureAccess()
    @Published var tipDismissed = false
    @Published private(set) var startedAt: Date?
    @Published private(set) var phase: Phase = .ready
    @Published private(set) var transcript = LiveTranscript()
    @Published private(set) var summary: Meeting.Summary?
    @Published private(set) var summarizing = false
    @Published private(set) var answers: [(question: String, text: String)] = []
    @Published private(set) var asking = false
    @Published private(set) var error: String?
    /// macOS refused system audio (e.g. permission granted to an older build): offer to fix it.
    @Published private(set) var systemAudioBlocked = false
    @Published var search = ""
    /// What the Mac says the meeting is (refreshed until Start), and the user's pick, if any.
    @Published private(set) var detection = MeetingDetection(source: .inPerson, title: nil, evidence: "Checking…")
    @Published var chosenSource: MeetingSource?

    /// Set by AppModel.
    weak var engine: Engine?
    var meetingsDir: () -> URL? = { nil }
    var incognito: () -> Bool = { false }
    var onSaved: () -> Void = {}

    private(set) var meetingID = Meeting.newID()
    private var recorder: MeetingRecorder?
    /// Seconds already recorded before this stretch (Resume continues the same note).
    private var offsetBase = 0.0
    private var stretchStart: Date?
    private var pendingChunks = 0
    private var savedURL: URL?
    private var poll: Timer?
    private var detectTimer: Timer?
    private let chunkDir = FileManager.default.temporaryDirectory.appendingPathComponent("mispr-meeting-chunks")

    var source: MeetingSource { chosenSource ?? detection.source }
    var needsPermission: Bool { source.needsSystemAudio && !screenAudioAllowed }
    var recording: Bool { phase == .recording }

    // MARK: - Permission

    func refreshPermission() {
        screenAudioAllowed = CGPreflightScreenCaptureAccess()
    }

    /// "Turn on": ask macOS (adds Mispr Flow to the list), open the settings pane, and
    /// watch for the switch so the card disappears as soon as it's on.
    func requestPermission() {
        if !CGRequestScreenCaptureAccess() {
            NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture")!)
        }
        poll?.invalidate()
        poll = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] timer in
            guard let self else { return timer.invalidate() }
            self.refreshPermission()
            if self.screenAudioAllowed { timer.invalidate() }
        }
    }

    // MARK: - Detection

    /// Look for a call now and every 3 s while the window is open and not recording.
    func startDetecting() {
        detect()
        detectTimer?.invalidate()
        detectTimer = Timer.scheduledTimer(withTimeInterval: 3, repeats: true) { [weak self] _ in self?.detect() }
    }

    func stopDetecting() {
        detectTimer?.invalidate()
        detectTimer = nil
    }

    private func detect() {
        guard phase == .ready || phase == .done else { return }  // fixed once recording
        DispatchQueue.global(qos: .utility).async {
            let found = MeetingDetector.detect(SystemProbe.snapshot())
            DispatchQueue.main.async {
                guard self.phase == .ready || self.phase == .done else { return }
                self.detection = found
                if self.title.isEmpty, let name = found.title, !name.isEmpty { self.title = name }
            }
        }
    }

    // MARK: - Recording

    /// ⌥M / the widget's ◉: start a new note, or stop the one recording.
    func toggle() {
        if recording { stop() } else { start(resume: false) }
    }

    /// Start (a new note) or Resume (keep adding to this one).
    func start(resume: Bool = false) {
        guard phase != .recording && phase != .finishing else { return }
        refreshPermission()
        guard !needsPermission else { tab = .transcript; return }  // the setup card asks first
        if phase == .done && !resume { resetForNewNote() }
        offsetBase = resume ? (finishedDuration ?? 0) : 0
        // Always try to record the Mac's sound, not only for detected calls: a call in a
        // background browser tab can look "in person", and missing the other side is worse than
        // capturing a quiet stream. If macOS refuses, the mic keeps going and a banner says why.
        let systemAudio = true
        let audioDir = incognito() ? nil : meetingsDir()?.appendingPathComponent(String(meetingID.prefix(10)))
            .appendingPathComponent(meetingID)
        try? FileManager.default.createDirectory(at: chunkDir, withIntermediateDirectories: true)
        let recorder = MeetingRecorder()
        recorder.onChunk = { [weak self] stream, start, samples in self?.chunk(stream, start, samples) }
        recorder.onLevel = { [weak self] level in self?.engine?.send(.meetingLevel, ["level": Double(level)]) }
        recorder.onError = { [weak self] message in DispatchQueue.main.async { self?.error = message } }
        self.recorder = recorder
        error = nil
        phase = .recording
        if startedAt == nil || !resume { startedAt = Date() }
        stretchStart = Date()
        tab = .transcript
        stopDetecting()
        engine?.send(.startMeeting)  // the widget shows its meeting pill
        Task { @MainActor in
            do {
                if let warning = try await recorder.start(systemAudio: systemAudio, saveTo: audioDir) {
                    self.error = warning
                    self.systemAudioBlocked = true
                }
            } catch {
                self.error = "Couldn't start recording: \(error.localizedDescription)"
                self.stop()
            }
        }
    }

    /// Quitting mid-meeting: stop the recorder so its audio files are finished properly.
    func stopForQuit() {
        recorder?.stop()
        recorder = nil
    }

    func stop() {
        guard phase == .recording else { return }
        finishedDuration = offsetBase + Date().timeIntervalSince(stretchStart ?? Date())
        phase = .finishing
        recorder?.stop()  // flushes the last chunks
        recorder = nil
        engine?.send(.stopMeeting)
        finishWhenTranscribed(deadline: Date().addingTimeInterval(30))
    }

    /// The engine reported the meeting stopped (the widget's ■): follow it.
    func meetingChanged(_ active: Bool) {
        if !active && phase == .recording { stop() }
    }

    /// On the audio queue: write the chunk and ask the engine to transcribe it.
    private func chunk(_ stream: String, _ start: Double, _ samples: [Float]) {
        DispatchQueue.main.async {
            let offset = self.offsetBase + start
            let url = self.chunkDir.appendingPathComponent("\(self.meetingID)-\(stream)-\(Int(offset * 1000)).wav")
            guard (try? WAV.data(samples).write(to: url)) != nil else { return }
            self.pendingChunks += 1
            self.engine?.send(.transcribeChunk, ["id": self.meetingID, "path": url.path, "stream": stream, "offset": offset])
        }
    }

    func handle(_ event: EngineEvent) {
        switch event {
        case let .chunkText(id, stream, speaker, offset, text) where id == meetingID:
            pendingChunks = max(0, pendingChunks - 1)
            transcript.add(stream: stream, speaker: speaker, offset: offset, text: text)
        case let .summary(id, summary, suggested) where id == meetingID:
            summarizing = false
            self.summary = summary
            if title.isEmpty && !suggested.isEmpty { title = suggested }
            save()
        case let .answer(id, question, text) where id == meetingID:
            asking = false
            answers.append((question.isEmpty ? "What did I miss?" : question, text))
        default:
            break
        }
    }

    private func finishWhenTranscribed(deadline: Date) {
        if pendingChunks > 0 && Date() < deadline {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { self.finishWhenTranscribed(deadline: deadline) }
            return
        }
        phase = .done
        if transcript.lines.isEmpty { return }  // nothing was said: nothing to keep
        save()
        summarizing = true
        engine?.send(.summarize, ["id": meetingID, "lines": transcript.engineLines])
    }

    var duration: Double {
        recording ? offsetBase + Date().timeIntervalSince(stretchStart ?? Date()) : (finishedDuration ?? 0)
    }

    /// Write the note (unless Incognito); called again when the summary arrives or the title changes.
    func save() {
        guard phase == .done, !transcript.lines.isEmpty, !incognito(), let dir = meetingsDir(), let startedAt else { return }
        let length = finishedDuration ?? Date().timeIntervalSince(startedAt)
        let meeting = transcript.meeting(id: meetingID, title: title, startedAt: startedAt, duration: length,
                                         source: source.rawValue, thoughts: thoughts, summary: summary)
        savedURL = try? meeting.save(in: dir)
        onSaved()
    }

    private var finishedDuration: Double?

    func ask(_ question: String) {
        guard !asking else { return }
        asking = true
        engine?.send(.ask, ["id": meetingID, "question": question, "lines": transcript.engineLines])
    }

    func rename(speaker: Int, to name: String) {
        transcript.names[speaker] = name.trimmingCharacters(in: .whitespaces)
        save()
    }

    private func resetForNewNote() {
        meetingID = Meeting.newID()
        transcript = LiveTranscript()
        summary = nil
        answers = []
        thoughts = ""
        title = ""
        startedAt = nil
        finishedDuration = nil
        savedURL = nil
        chosenSource = nil
    }

    /// The transcript as text, for Copy and Share.
    var plainText: String {
        var out = (title.isEmpty ? "Meeting" : title) + "\n\n"
        if let summary { out += summary.overview + "\n\n" }
        for group in transcript.groups {
            out += group.label + ":\n" + group.lines.map(\.text).joined(separator: " ") + "\n\n"
        }
        return out
    }
}

struct NoteView: View {
    @EnvironmentObject var model: AppModel
    @EnvironmentObject var note: NoteModel
    let close: () -> Void
    @State private var setupDismissed = false
    @State private var question = ""
    @State private var searching = false
    @State private var renaming: Int?
    @State private var newName = ""
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            toolbar
            TextField("New note", text: $note.title)
                .textFieldStyle(.plain).font(Theme.display(34))
                .padding(.horizontal, 26).padding(.top, 14)
                .onSubmit { note.save() }
            Text((note.startedAt ?? Date()).formatted(.dateTime.month(.abbreviated).day().hour().minute()))
                .font(.system(size: 12)).foregroundStyle(Theme.secondary).padding(.horizontal, 26).padding(.top, 2)
            SourceChip().padding(.horizontal, 26).padding(.top, 8)
            tabs.padding(.top, 14)
            Divider().overlay(Theme.cardStroke)
            ZStack {
                content.frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                if note.needsPermission && !setupDismissed && note.phase != .recording {
                    Color.black.opacity(0.18).ignoresSafeArea()
                    SetupCard(back: { setupDismissed = true }, turnOn: note.requestPermission)
                        .padding(.horizontal, 18).padding(.top, 2)
                        .frame(maxHeight: .infinity, alignment: .top)
                }
            }
            if let error = note.error {
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange)
                    Text(error).font(.system(size: 12)).fixedSize(horizontal: false, vertical: true)
                    if note.systemAudioBlocked {
                        Button("Turn on") { note.requestPermission() }.buttonStyle(DarkButton())
                    }
                }
                .padding(10).background(RoundedRectangle(cornerRadius: 10).fill(Color.orange.opacity(0.12)))
                .padding(.horizontal, 18).padding(.bottom, 4)
            }
            bottomBar
        }
        .background(Theme.content)
        .foregroundStyle(Theme.text)
        .ignoresSafeArea()
        .alert("Rename speaker", isPresented: Binding(get: { renaming != nil }, set: { if !$0 { renaming = nil } })) {
            TextField("Name", text: $newName)
            Button("Rename") { if let r = renaming { note.rename(speaker: r, to: newName) }; renaming = nil }
            Button("Cancel", role: .cancel) { renaming = nil }
        }
    }

    private var toolbar: some View {
        HStack(spacing: 8) {
            Spacer().frame(width: 70)  // traffic lights
            Button(action: close) {
                Image(systemName: "chevron.left").font(.system(size: 12, weight: .semibold))
                    .frame(width: 26, height: 24)
                    .background(RoundedRectangle(cornerRadius: 6).fill(Theme.card))
            }
            .buttonStyle(.plain).help("Close")
            Spacer()
            Button {
                model.page = .notetaker
                (NSApp.delegate as? AppDelegate)?.showMainWindow()
            } label: { Image(systemName: "macwindow").font(.system(size: 13)) }
            .buttonStyle(.plain).foregroundStyle(Theme.secondary).help("Open in Mispr Flow")
            Button {
                if let call = note.detection.window, let window = NSApp.windows.first(where: { $0.title == "New note" }) {
                    WindowArranger.split(meeting: call, note: window)
                }
            } label: {
                Image(systemName: "rectangle.split.2x1").font(.system(size: 14))
                    .frame(width: 30, height: 24)
                    .background(RoundedRectangle(cornerRadius: 6).fill(Theme.card))
            }
            .buttonStyle(.plain)
            .disabled(note.detection.window == nil)
            .help(note.detection.window == nil ? "Split screen works when a call window is found (Meet, Zoom, Teams…)"
                  : "Split screen with \(note.detection.source.rawValue)")
            Button {
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(note.plainText, forType: .string)
                copied = true
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { copied = false }
            } label: {
                Label(copied ? "Copied" : "Share", systemImage: copied ? "checkmark" : "square.and.arrow.up")
                    .font(.system(size: 13)).padding(.horizontal, 10).padding(.vertical, 4)
                    .background(RoundedRectangle(cornerRadius: 7).fill(Theme.card))
            }
            .buttonStyle(.plain).help("Copy the summary and transcript")
        }
        .padding(.top, 14).padding(.horizontal, 14)
        .frame(height: 44)
    }

    private var tabs: some View {
        HStack(spacing: 22) {
            ForEach(NoteModel.Tab.allCases, id: \.self) { tab in
                Button { note.tab = tab } label: {
                    VStack(spacing: 8) {
                        HStack(spacing: 5) {
                            if tab == .summary { Image(systemName: "plus").font(.system(size: 12, weight: .medium)) }
                            if tab == .transcript && note.recording {
                                Image(systemName: "waveform").font(.system(size: 12)).foregroundStyle(Theme.accent)
                                    .symbolEffect(.variableColor.iterative)
                            }
                            Text(tab.rawValue).font(.system(size: 15, weight: note.tab == tab ? .semibold : .regular))
                        }
                        .foregroundStyle(note.tab == tab ? Theme.text : Theme.secondary)
                        Rectangle().fill(note.tab == tab ? Theme.text : .clear).frame(height: 2)
                    }
                    .fixedSize()
                }
                .buttonStyle(.plain)
            }
            Spacer()
        }
        .padding(.horizontal, 26)
    }

    @ViewBuilder private var content: some View {
        switch note.tab {
        case .thoughts:
            TextEditor(text: $note.thoughts)
                .font(.system(size: 14)).scrollContentBackground(.hidden)
                .padding(.horizontal, 22).padding(.top, 14)
                .overlay(alignment: .topLeading) {
                    if note.thoughts.isEmpty {
                        Text("Take your own notes here. They're saved with the meeting.")
                            .font(.system(size: 14)).foregroundStyle(Theme.secondary)
                            .padding(.horizontal, 27).padding(.top, 14).allowsHitTesting(false)
                    }
                }
        case .transcript: transcriptTab
        case .summary: summaryTab
        }
    }

    // MARK: - Transcript

    private var transcriptTab: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(spacing: 0) {
                HStack(spacing: 10) {
                    Image(systemName: "clock").font(.system(size: 12))
                    TimelineView(.periodic(from: .now, by: 1)) { _ in
                        Text(elapsed).font(.system(size: 13, weight: .medium)).monospacedDigit()
                    }
                    if searching {
                        TextField("Search transcript", text: $note.search).textFieldStyle(.plain).font(.system(size: 13))
                        Text("\(matchCount)").font(.system(size: 11)).foregroundStyle(Theme.secondary)
                    }
                    Spacer()
                    Button { searching.toggle(); if !searching { note.search = "" } } label: {
                        Image(systemName: searching ? "xmark" : "magnifyingglass")
                    }
                    .buttonStyle(.plain).help("Search")
                    Button {
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(note.plainText, forType: .string)
                    } label: { Image(systemName: "doc.on.doc") }
                    .buttonStyle(.plain).help("Copy transcript")
                }
                .font(.system(size: 12)).foregroundStyle(Theme.secondary)
                .padding(.horizontal, 14).padding(.vertical, 10)
                if !note.tipDismissed {
                    HStack {
                        Text("After the meeting, Mispr Flow writes a summary. Click a speaker's name to rename them.")
                            .font(.system(size: 12)).foregroundStyle(Theme.secondary)
                        Spacer()
                        Button { note.tipDismissed = true } label: { Image(systemName: "xmark").font(.system(size: 10)) }
                            .buttonStyle(.plain).foregroundStyle(Theme.secondary)
                    }
                    .padding(.horizontal, 14).padding(.vertical, 10)
                    .background(Theme.card.opacity(0.6))
                }
            }
            .background(RoundedRectangle(cornerRadius: 10).fill(Theme.card))
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .padding(.horizontal, 18).padding(.top, 14)

            if note.transcript.lines.isEmpty {
                Spacer()
                VStack(spacing: 8) {
                    if note.recording {
                        Text("Listening…").font(.system(size: 15)).foregroundStyle(Theme.secondary)
                        Text("Lines appear a few seconds after someone speaks.").font(.system(size: 13)).foregroundStyle(Theme.secondary)
                    } else {
                        Text("Welcome to Notetaker!").font(.system(size: 15)).foregroundStyle(Theme.secondary)
                        Text("Press Start or ⌥M when your meeting begins").font(.system(size: 19, weight: .medium))
                            .multilineTextAlignment(.center)
                    }
                }
                .frame(maxWidth: .infinity).padding(.horizontal, 30)
                Spacer(); Spacer()
            } else {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 12) {
                            ForEach(Array(note.transcript.groups.enumerated()), id: \.offset) { index, group in
                                VStack(alignment: .leading, spacing: 5) {
                                    Button {
                                        if group.speaker > 0 { renaming = group.speaker; newName = "" }
                                    } label: {
                                        HStack(spacing: 6) {
                                            Circle().fill(SpeakerColors.color(group.speaker)).frame(width: 8, height: 8)
                                            Text(group.label).font(.system(size: 13, weight: .semibold))
                                                .foregroundStyle(SpeakerColors.color(group.speaker))
                                        }
                                    }
                                    .buttonStyle(.plain).help(group.speaker > 0 ? "Rename this speaker" : "")
                                    ForEach(group.lines) { line in
                                        highlighted(line.text)
                                            .font(.system(size: 14)).textSelection(.enabled)
                                            .padding(.horizontal, 12).padding(.vertical, 8)
                                            .background(RoundedRectangle(cornerRadius: 10).fill(SpeakerColors.color(group.speaker).opacity(0.12)))
                                    }
                                }
                                .id(index)
                            }
                            Color.clear.frame(height: 1).id("end")
                        }
                        .padding(.horizontal, 22).padding(.vertical, 14)
                    }
                    .onChange(of: note.transcript.lines.count) { withAnimation { proxy.scrollTo("end") } }
                }
            }
        }
    }

    private var elapsed: String {
        let s = Int(note.duration)
        return s >= 3600 ? String(format: "%d:%02d:%02d", s / 3600, s / 60 % 60, s % 60) : String(format: "%d:%02d", s / 60, s % 60)
    }

    private var matchCount: Int {
        let q = note.search.trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else { return 0 }
        return note.transcript.lines.reduce(0) { $0 + $1.text.lowercased().components(separatedBy: q.lowercased()).count - 1 }
    }

    /// The text with search matches highlighted.
    private func highlighted(_ text: String) -> Text {
        let q = note.search.trimmingCharacters(in: .whitespaces)
        var attributed = AttributedString(text)
        if !q.isEmpty {
            var searchRange = attributed.startIndex..<attributed.endIndex
            while let range = attributed[searchRange].range(of: q, options: .caseInsensitive) {
                attributed[range].backgroundColor = .orange.opacity(0.55)
                searchRange = range.upperBound..<attributed.endIndex
            }
        }
        return Text(attributed)
    }

    // MARK: - Summary

    @ViewBuilder private var summaryTab: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                if note.summarizing {
                    HStack(spacing: 8) { ProgressView().controlSize(.small); Text("Writing the summary…") }
                        .font(.system(size: 13)).foregroundStyle(Theme.secondary)
                } else if let s = note.summary {
                    Text(s.overview).font(.system(size: 14)).fixedSize(horizontal: false, vertical: true)
                    section("Action items", s.actionItems.map { "\($0.task) — \($0.owner)" + ($0.due.map { ", \($0)" } ?? "") })
                    section("Decisions", s.decisions)
                    section("Open questions", s.openQuestions)
                } else {
                    Label(note.phase == .done && !note.transcript.lines.isEmpty ? "The summary couldn't be written."
                          : "Summary generated when you stop", systemImage: "sparkles")
                        .font(.system(size: 12, weight: .medium)).foregroundStyle(Theme.secondary)
                        .padding(10).frame(maxWidth: .infinity, alignment: .leading)
                        .background(RoundedRectangle(cornerRadius: 10).fill(Theme.card))
                }
            }
            .padding(.horizontal, 22).padding(.vertical, 16)
        }
    }

    @ViewBuilder private func section(_ title: String, _ items: [String]) -> some View {
        if !items.isEmpty {
            VStack(alignment: .leading, spacing: 6) {
                Text(title).font(.system(size: 13, weight: .semibold))
                ForEach(items, id: \.self) { Text("• " + $0).font(.system(size: 13)).fixedSize(horizontal: false, vertical: true) }
            }
        }
    }

    // MARK: - Bottom

    private var bottomBar: some View {
        VStack(spacing: 10) {
            if !note.answers.isEmpty || note.asking {
                ScrollView {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(Array(note.answers.enumerated()), id: \.offset) { _, a in
                            VStack(alignment: .leading, spacing: 3) {
                                Text(a.question).font(.system(size: 12, weight: .semibold)).foregroundStyle(Theme.secondary)
                                Text(a.text).font(.system(size: 13)).textSelection(.enabled)
                            }
                        }
                        if note.asking { HStack { ProgressView().controlSize(.small); Text("Thinking…").font(.system(size: 12)) } }
                    }
                    .padding(12).frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(maxHeight: 150)
                .background(RoundedRectangle(cornerRadius: 10).fill(Theme.card))
            }
            Text("Always let people know when you're transcribing them.")
                .font(.system(size: 11)).foregroundStyle(Theme.secondary)
            HStack(spacing: 10) {
                Button { note.recording ? note.stop() : note.start(resume: note.phase == .done) } label: {
                    HStack(spacing: 8) {
                        if note.recording {
                            RoundedRectangle(cornerRadius: 3).fill(Color.green).frame(width: 12, height: 12)
                            Text("Stop").font(.system(size: 15, weight: .medium))
                        } else if note.phase == .finishing {
                            ProgressView().controlSize(.small)
                            Text("Finishing").font(.system(size: 15, weight: .medium))
                        } else {
                            ZStack {
                                Circle().stroke(Color.green.opacity(0.6), lineWidth: 1.5).frame(width: 16, height: 16)
                                Circle().fill(Color.green).frame(width: 8, height: 8)
                            }
                            Text(note.phase == .done ? "Resume" : "Start").font(.system(size: 15, weight: .medium))
                        }
                    }
                    .padding(.horizontal, 16).frame(height: 40)
                    .background(Capsule().fill(Theme.content))
                    .overlay(Capsule().stroke(Theme.cardStroke))
                }
                .buttonStyle(.plain)
                .disabled(note.phase == .finishing || (note.needsPermission && !note.recording))
                .opacity(note.needsPermission && !note.recording ? 0.5 : 1)
                .help(note.recording ? "Stop (⌥M)" : note.phase == .done ? "Keep recording into this note" : "Start recording (⌥M)")
                HStack(spacing: 6) {
                    TextField("Ask anything", text: $question).textFieldStyle(.plain).font(.system(size: 14))
                        .onSubmit { send() }
                    Button("What did I miss?") { note.ask("") }
                        .buttonStyle(.plain).font(.system(size: 12, weight: .medium))
                        .padding(.horizontal, 10).padding(.vertical, 5)
                        .background(Capsule().fill(Theme.card))
                        .disabled(note.transcript.lines.isEmpty || note.asking)
                }
                .padding(.leading, 16).padding(.trailing, 6).frame(height: 40)
                .background(Capsule().fill(Theme.content))
                .overlay(Capsule().stroke(Theme.cardStroke))
            }
        }
        .padding(.horizontal, 18).padding(.vertical, 14)
        .background(Theme.content)
    }

    private func send() {
        let q = question.trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else { return }
        note.ask(q)
        question = ""
    }
}

/// A distinct color per speaker: you in the theme accent, the others in a fixed palette.
enum SpeakerColors {
    static let palette: [UInt32] = [0x3D8BFD, 0xE8833A, 0xB65CE0, 0xE0518A, 0x2FB3A4, 0xD4A72C, 0x8C7AE6, 0x6B9E3A]

    static func color(_ speaker: Int) -> Color {
        speaker == 0 ? Theme.accent : Color(nsColor: Theme.nsColor(hex: palette[(speaker - 1) % palette.count]))
    }
}

/// "Complete setup to start Notetaker": the Screen & System Audio permission, with a
/// drawing of where to switch it on.
struct SetupCard: View {
    let back: () -> Void
    let turnOn: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Complete setup to start Notetaker").font(.system(size: 18, weight: .semibold))
                    Text("These are required settings").font(.system(size: 13)).foregroundStyle(Theme.secondary)
                }
                Spacer()
                Button("Back", action: back).buttonStyle(OutlineButton())
            }
            VStack(alignment: .leading, spacing: 14) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 4) {
                        HStack(spacing: 6) {
                            Text("Enable System Audio").font(.system(size: 14, weight: .medium))
                            Image(systemName: "waveform").font(.system(size: 12))
                        }
                        Text("Capture what others say").font(.system(size: 13)).foregroundStyle(Theme.secondary)
                    }
                    Spacer()
                    Button("Turn on", action: turnOn).buttonStyle(DarkButton())
                }
                SettingsIllustration()
            }
            .padding(14)
            .background(RoundedRectangle(cornerRadius: 12).stroke(Theme.cardStroke))
            .padding(.top, 18)
            Text("Mispr Flow records only after you press Start, and everything stays on this Mac. Let others know you're taking notes.")
                .font(.system(size: 12)).foregroundStyle(Theme.secondary).padding(.top, 14)
        }
        .padding(18)
        .background(RoundedRectangle(cornerRadius: 14).fill(Theme.content))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.cardStroke))
        .shadow(color: .black.opacity(0.08), radius: 12, y: 4)
    }
}

/// A small drawing of System Settings > Screen & System Audio Recording, with Mispr Flow's
/// switch highlighted.
struct SettingsIllustration: View {
    var body: some View {
        ZStack {
            LinearGradient(colors: [Color(red: 0.55, green: 0.72, blue: 0.95), Color(red: 0.16, green: 0.36, blue: 0.75)],
                           startPoint: .topLeading, endPoint: .bottomTrailing)
            HStack(spacing: 0) {
                VStack(alignment: .leading, spacing: 7) {
                    HStack(spacing: 4) { ForEach([Color.red, .yellow, .green], id: \.self) { Circle().fill($0).frame(width: 6, height: 6) } }
                        .padding(.bottom, 4)
                    ForEach(["Wi-Fi", "Bluetooth", "General", "Accessibility", "Privacy & Security"], id: \.self) { item in
                        HStack(spacing: 5) {
                            RoundedRectangle(cornerRadius: 2).fill(Color.blue.opacity(0.8)).frame(width: 9, height: 9)
                            Text(item).font(.system(size: 8))
                        }
                    }
                    Spacer()
                }
                .padding(10).frame(width: 110, alignment: .leading)
                .background(Color(white: 0.16))
                VStack(alignment: .leading, spacing: 6) {
                    Text("Screen & System Audio Recording").font(.system(size: 8.5, weight: .semibold))
                    row("Zoom", on: true)
                    row("Slack", on: true)
                    Text("System Audio Recording Only").font(.system(size: 7.5, weight: .semibold)).padding(.top, 4)
                    row("Mispr Flow", on: false, highlight: true)
                    Spacer()
                }
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(white: 0.12))
            }
            .foregroundStyle(.white)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .padding(.horizontal, 22).padding(.top, 14)
            .frame(maxHeight: .infinity, alignment: .top)
        }
        .frame(height: 170)
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private func row(_ app: String, on: Bool, highlight: Bool = false) -> some View {
        HStack(spacing: 5) {
            RoundedRectangle(cornerRadius: 2).fill(highlight ? Color.white : Color.gray).frame(width: 9, height: 9)
            Text(app).font(.system(size: 8))
            Spacer()
            Capsule().fill(on ? Color.blue : Color.gray.opacity(0.6)).frame(width: 18, height: 10)
                .overlay(Circle().fill(.white).frame(width: 8).offset(x: on ? 4 : -4))
        }
        .padding(.horizontal, 5).padding(.vertical, 3)
        .background(RoundedRectangle(cornerRadius: 3).fill(highlight ? Color.white.opacity(0.14) : .clear))
    }
}

struct OutlineButton: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(.system(size: 13))
            .padding(.horizontal, 12).padding(.vertical, 6)
            .background(RoundedRectangle(cornerRadius: 8).fill(Theme.content))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.cardStroke))
            .opacity(configuration.isPressed ? 0.7 : 1)
    }
}

struct DarkButton: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(.system(size: 14, weight: .medium)).foregroundStyle(Theme.content)
            .padding(.horizontal, 14).padding(.vertical, 7)
            .background(RoundedRectangle(cornerRadius: 8).fill(Theme.text))
            .opacity(configuration.isPressed ? 0.75 : 1)
    }
}

/// "Google Meet · detected": what kind of meeting this is. Click to pick another.
struct SourceChip: View {
    @EnvironmentObject var note: NoteModel
    @EnvironmentObject var model: AppModel

    var body: some View {
        let recording = model.engine.meetingActive
        Menu {
            Button("Detect automatically") { note.chosenSource = nil }
            Divider()
            ForEach(MeetingSource.allCases) { source in
                Button { note.chosenSource = source } label: {
                    Label(source.rawValue, systemImage: source.symbol)
                }
            }
        } label: {
            HStack(spacing: 6) {
                Image(systemName: note.source.symbol).font(.system(size: 11))
                Text(note.source.rawValue).font(.system(size: 12, weight: .medium))
                Text(note.chosenSource == nil ? "· detected" : "· chosen").font(.system(size: 12)).foregroundStyle(Theme.secondary)
                if !note.source.needsSystemAudio {
                    Text("· mic only").font(.system(size: 12)).foregroundStyle(Theme.secondary)
                }
                Image(systemName: "chevron.down").font(.system(size: 9)).foregroundStyle(Theme.secondary)
            }
            .padding(.horizontal, 10).padding(.vertical, 5)
            .background(Capsule().fill(Theme.card))
        }
        .menuStyle(.borderlessButton).menuIndicator(.hidden).fixedSize()
        .disabled(recording)
        .help(helpText)
    }

    private var helpText: String {
        note.chosenSource == nil ? note.detection.evidence : "You chose this. Pick Detect automatically to go back."
    }
}
