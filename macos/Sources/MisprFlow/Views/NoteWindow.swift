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
        window.contentView = NSHostingView(rootView: ThemedRoot { NoteView(close: { [weak self] in self?.close() }) }
            .environmentObject(model).environmentObject(model.note))
        return window
    }
}

/// The note being taken: notes typed during the meeting, the meeting's state, and the
/// Screen & System Audio permission it needs.
final class NoteModel: ObservableObject {
    enum Tab: String, CaseIterable {
        case thoughts = "My thoughts"
        case transcript = "Transcript"
        case summary = "Summary"
    }

    @Published var tab: Tab = .transcript
    @Published var thoughts = ""
    @Published var title = ""
    @Published var screenAudioAllowed = CGPreflightScreenCaptureAccess()
    @Published var tipDismissed = false
    @Published private(set) var startedAt: Date?
    private var poll: Timer?

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

    func meetingChanged(_ active: Bool) {
        startedAt = active ? (startedAt ?? Date()) : nil
    }
}

struct NoteView: View {
    @EnvironmentObject var model: AppModel
    let close: () -> Void
    @State private var setupDismissed = false

    @EnvironmentObject var note: NoteModel
    private var recording: Bool { model.engine.meetingActive }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            toolbar
            TextField("New note", text: Binding(get: { note.title }, set: { note.title = $0 }))
                .textFieldStyle(.plain).font(Theme.display(34))
                .padding(.horizontal, 26).padding(.top, 14)
            tabs.padding(.top, 18)
            Divider().overlay(Theme.cardStroke)
            ZStack {
                content.frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                if !note.screenAudioAllowed && !setupDismissed {
                    Color.black.opacity(0.18).ignoresSafeArea()
                    SetupCard(back: { setupDismissed = true }, turnOn: note.requestPermission)
                        .padding(.horizontal, 18).padding(.top, 2)
                        .frame(maxHeight: .infinity, alignment: .top)
                }
            }
            bottomBar
        }
        .background(Theme.content)
        .foregroundStyle(Theme.text)
        .ignoresSafeArea()
    }

    private var toolbar: some View {
        HStack(spacing: 10) {
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
            } label: {
                Image(systemName: "sidebar.right").font(.system(size: 14))
            }
            .buttonStyle(.plain).foregroundStyle(Theme.secondary).help("Open in Mispr Flow")
        }
        .padding(.top, 14).padding(.horizontal, 14)
        .frame(height: 44)
    }

    private var tabs: some View {
        HStack(spacing: 22) {
            ForEach(NoteModel.Tab.allCases, id: \.self) { tab in
                Button { note.tab = tab } label: {
                    VStack(spacing: 8) {
                        HStack(spacing: 4) {
                            if tab == .summary { Image(systemName: "plus").font(.system(size: 12, weight: .medium)) }
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
            TextEditor(text: Binding(get: { note.thoughts }, set: { note.thoughts = $0 }))
                .font(.system(size: 14)).scrollContentBackground(.hidden)
                .padding(.horizontal, 22).padding(.top, 14)
                .overlay(alignment: .topLeading) {
                    if note.thoughts.isEmpty {
                        Text("Jot down your own notes. They're kept with the meeting.")
                            .font(.system(size: 14)).foregroundStyle(Theme.secondary)
                            .padding(.horizontal, 27).padding(.top, 14).allowsHitTesting(false)
                    }
                }
        case .transcript:
            VStack(alignment: .leading, spacing: 0) {
                VStack(spacing: 0) {
                    HStack {
                        Text("TRANSCRIPT").font(.system(size: 11, weight: .semibold)).tracking(0.8).foregroundStyle(Theme.secondary)
                        Spacer()
                        Image(systemName: "magnifyingglass")
                        Image(systemName: "doc.on.doc")
                    }
                    .font(.system(size: 12)).foregroundStyle(Theme.secondary)
                    .padding(.horizontal, 14).padding(.vertical, 10)
                    if !note.tipDismissed {
                        HStack {
                            Text("After the meeting, Mispr Flow cleans up the transcript and labels speakers.")
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
                Spacer()
                VStack(spacing: 8) {
                    if recording {
                        Image(systemName: "waveform").font(.system(size: 22)).foregroundStyle(Theme.accent)
                            .symbolEffect(.variableColor.iterative)
                        Text("Listening…").font(.system(size: 15))
                        Text("The live transcript is the next piece being built; the meeting is being timed for now.")
                            .font(.system(size: 12)).foregroundStyle(Theme.secondary).multilineTextAlignment(.center)
                    } else {
                        Text("Welcome to Notetaker!").font(.system(size: 15)).foregroundStyle(Theme.secondary)
                        Text("Press Start when your meeting begins").font(.system(size: 20, weight: .medium))
                    }
                }
                .frame(maxWidth: .infinity).padding(.horizontal, 30)
                Spacer()
                Spacer()
            }
        case .summary:
            VStack(spacing: 8) {
                Spacer()
                Image(systemName: "sparkles").font(.system(size: 22)).foregroundStyle(Theme.secondary)
                Text("A summary is written after the meeting").font(.system(size: 15, weight: .medium))
                Text("Overview, decisions, and action items, generated on this Mac.")
                    .font(.system(size: 12)).foregroundStyle(Theme.secondary)
                Spacer()
                Spacer()
            }
            .frame(maxWidth: .infinity)
        }
    }

    private var bottomBar: some View {
        HStack(spacing: 10) {
            Button {
                model.engine.send(recording ? .stopMeeting : .startMeeting)
            } label: {
                HStack(spacing: 8) {
                    if recording {
                        RoundedRectangle(cornerRadius: 2).fill(Color.red).frame(width: 10, height: 10)
                        TimelineView(.periodic(from: .now, by: 1)) { context in
                            Text(elapsed(at: context.date)).font(.system(size: 14, weight: .medium)).monospacedDigit()
                        }
                    } else {
                        ZStack {
                            Circle().stroke(Color.green.opacity(0.6), lineWidth: 1.5).frame(width: 16, height: 16)
                            Circle().fill(Color.green).frame(width: 8, height: 8)
                        }
                        Text("Start").font(.system(size: 15, weight: .medium))
                    }
                }
                .padding(.horizontal, 16).frame(height: 40)
                .background(Capsule().fill(Theme.content))
                .overlay(Capsule().stroke(Theme.cardStroke))
            }
            .buttonStyle(.plain)
            .disabled(!note.screenAudioAllowed && !recording)
            .opacity(!note.screenAudioAllowed && !recording ? 0.5 : 1)
            .help(recording ? "Stop the meeting" : "Start recording the meeting")
            HStack {
                Text("Ask anything").font(.system(size: 14)).foregroundStyle(Theme.secondary)
                Spacer()
            }
            .padding(.horizontal, 16).frame(height: 40)
            .background(Capsule().fill(Theme.content))
            .overlay(Capsule().stroke(Theme.cardStroke))
            .help("Ask questions about the meeting once it has a transcript (coming soon)")
        }
        .padding(.horizontal, 18).padding(.vertical, 16)
        .background(Theme.content)
    }

    private func elapsed(at now: Date) -> String {
        let seconds = Int(now.timeIntervalSince(note.startedAt ?? now))
        return String(format: "%d:%02d", seconds / 60, seconds % 60)
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
