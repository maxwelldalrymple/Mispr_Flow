import MisprCore
import SwiftUI

struct RootView: View {
    @EnvironmentObject var model: AppModel
    @State private var sidebarVisible = true

    var body: some View {
        HStack(spacing: 0) {
            if sidebarVisible {
                Sidebar().frame(width: 212).transition(.move(edge: .leading))
            }
            page
                .tourSpot(.page)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(RoundedRectangle(cornerRadius: 16).fill(Theme.content))
                .overlay {
                    // Incognito: a purple frame around the page, like the widget's outline.
                    if model.setting("incognito") {
                        RoundedRectangle(cornerRadius: 16).strokeBorder(Theme.incognito, lineWidth: 2)
                            .overlay(alignment: .top) {
                                Label("Incognito · nothing is saved", systemImage: "eye.slash.fill")
                                    .font(.system(size: 11, weight: .semibold)).foregroundStyle(.white)
                                    .padding(.horizontal, 10).padding(.vertical, 4)
                                    .background(Capsule().fill(Theme.incognito))
                                    .offset(y: -11)
                            }
                            .allowsHitTesting(false)
                    }
                }
                .padding(.top, 44)
                .padding([.trailing, .bottom], 10)
                .padding(.leading, sidebarVisible ? 0 : 10)
        }
        .background(Theme.sidebar)
        .overlay(alignment: .topLeading) {
            Button { withAnimation(.easeInOut(duration: 0.2)) { sidebarVisible.toggle() } } label: {
                Image(systemName: "sidebar.left").font(.system(size: 14))
            }
            .buttonStyle(.plain).foregroundStyle(Theme.secondary)
            .padding(.leading, 84).padding(.top, 14)
            .help(sidebarVisible ? "Hide sidebar" : "Show sidebar")
        }
        .overlay(alignment: .top) { EngineBanner() }
        .overlay(alignment: .topTrailing) {
            HStack(spacing: 12) {
                HStack(spacing: 12) {
                    AutoEnterButton()
                    IncognitoSwitch()
                }
                .tourSpot(.topBar)
                Button { model.openProfile() } label: { AvatarView(size: 24) }
                    .buttonStyle(.plain).help("Profile")
            }
            .padding(.top, 9).padding(.trailing, 18)
        }
        .overlay {
            if model.showSettings { SettingsModal() }
        }
        .overlayPreferenceValue(TourAnchors.self) { anchors in TourOverlay(anchors: anchors) }
        .onAppear { model.startTourIfNew() }
        .ignoresSafeArea()
        .foregroundStyle(Theme.text)
    }

    @ViewBuilder private var page: some View {
        switch model.page {
        case .home: HomeView()
        case .insights: InsightsView()
        case .notetaker: NotesView()
        case .prompts: PromptsView()
        }
    }
}

/// Shown only when the engine isn't running normally.
struct EngineBanner: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        switch model.engine.state {
        case let .failed(message):
            HStack(spacing: 8) {
                Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange)
                Text(message).font(.system(size: 12))
                Button("Retry") { model.engine.start() }.controlSize(.small)
            }
            .padding(.horizontal, 12).padding(.vertical, 6)
            .background(Capsule().fill(Theme.card))
            .padding(.top, 10)
        case .starting:
            Text("Starting dictation engine…").font(.system(size: 12)).foregroundStyle(Theme.secondary).padding(.top, 14)
        default:
            EmptyView()
        }
    }
}

struct Sidebar: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 8) {
                Logo(size: 22)
                Text("Mispr Flow").font(.system(size: 17, weight: .semibold))
            }
            .padding(.leading, 12).padding(.top, 52).padding(.bottom, 18)

            ForEach(Page.allCases) { page in
                SidebarItem(title: page.rawValue, symbol: page.symbol, selected: model.page == page) {
                    model.page = page
                }
            }
            Spacer()
            SidebarItem(title: "Settings", symbol: "gearshape", selected: false) { model.showSettings = true }
                .tourSpot(.settings)
            SidebarItem(title: "Help", symbol: "questionmark.circle", selected: false) {
                NSWorkspace.shared.open(URL(string: "https://github.com/maxwelldalrymple/Mispr_Flow#readme")!)
            }
            .padding(.bottom, 14)
        }
        .padding(.horizontal, 10)
    }
}

struct SidebarItem: View {
    let title: String
    let symbol: String
    let selected: Bool
    let action: () -> Void
    @State private var hovering = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                Image(systemName: symbol).font(.system(size: 14)).frame(width: 18)
                Text(title).font(.system(size: 14))
                Spacer()
            }
            .padding(.horizontal, 10).padding(.vertical, 7)
            .background(RoundedRectangle(cornerRadius: 8).fill(selected ? Theme.selection : hovering ? Theme.selection.opacity(0.5) : .clear))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hovering = $0 }
    }
}

struct PlaceholderView: View {
    let title: String
    let symbol: String
    let message: String
    let detail: String

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(title).font(.system(size: 24, weight: .semibold)).padding(.bottom, 28)
            Card(padding: 32) {
                VStack(alignment: .leading, spacing: 10) {
                    Image(systemName: symbol).font(.system(size: 28)).foregroundStyle(Theme.secondary)
                    Text(message).font(Theme.display(24))
                    Text(detail).font(.system(size: 13)).foregroundStyle(Theme.secondary)
                }
            }
            Spacer()
        }
        .padding(.horizontal, 40).padding(.top, 36)
        .frame(maxWidth: 900, alignment: .leading)
        .frame(maxWidth: .infinity)
    }
}

/// Incognito in the window's top-right corner, with an explanation on hover.
struct IncognitoSwitch: View {
    @EnvironmentObject var model: AppModel
    @State private var showInfo = false

    var body: some View {
        let on = model.setting("incognito")
        HStack(spacing: 7) {
            Image(systemName: on ? "eye.slash.fill" : "eye.slash").font(.system(size: 12))
                .foregroundStyle(on ? Theme.incognito : Theme.secondary)
            Text("Incognito").font(.system(size: 12, weight: on ? .semibold : .regular))
                .foregroundStyle(on ? Theme.incognito : Theme.text)
            Toggle("", isOn: model.binding("incognito")).toggleStyle(.switch).labelsHidden().controlSize(.mini)
                .tint(Theme.incognito)
            Image(systemName: "info.circle").font(.system(size: 12)).foregroundStyle(Theme.secondary)
                .onHover { showInfo = $0 }
        }
        .padding(.horizontal, 10).padding(.vertical, 5)
        .background(Capsule().fill(on ? Theme.incognito.opacity(0.16) : Color.clear))
        .overlay(alignment: .topTrailing) {
            if showInfo {
                InfoCard(title: on ? "Incognito is on" : "Incognito is off", lines: [
                    "When it's on, nothing you dictate is saved: the audio stays in locked memory and is wiped right after it's transcribed, and no text or history is written to disk. History and Insights pause until you turn it off.",
                    "Dictation works the same either way, and nothing ever leaves your Mac.",
                ])
            }
        }
        .animation(.easeOut(duration: 0.12), value: showInfo)
        .zIndex(10)
    }
}

/// Auto-Enter in the top bar, beside Incognito: when it's on, Mispr Flow presses Return
/// after your words land in a text box, so a chat message sends itself and you can just talk.
/// It's only ever turned on here, by hand, and stays on until you click it again.
struct AutoEnterButton: View {
    @EnvironmentObject var model: AppModel
    @State private var showInfo = false

    var body: some View {
        let on = model.setting("auto_enter")
        Button { model.setSetting("auto_enter", !on) } label: {
            HStack(spacing: 5) {
                Image(systemName: "return").font(.system(size: 12, weight: on ? .semibold : .regular))
                if on { Text("Auto-Enter").font(.system(size: 12, weight: .semibold)) }
            }
            .foregroundStyle(on ? Theme.accent : Theme.secondary)
            .padding(.horizontal, 8).padding(.vertical, 5)
            .background(Capsule().fill(on ? Theme.accent.opacity(0.16) : Color.clear))
            .contentShape(Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(on ? "Auto-Enter is on" : "Auto-Enter is off")
        .onHover { showInfo = $0 }
        .overlay(alignment: .topTrailing) {
            if showInfo {
                InfoCard(title: on ? "Auto-Enter is on" : "Auto-Enter is off", lines: [
                    "When it's on, Mispr Flow presses Enter for you right after your words go into a text box, so chat messages send themselves and you can just talk.",
                    "It only presses Enter when the text was put into a text box, never when it was copied instead. Click to turn it \(on ? "off" : "on").",
                ])
            }
        }
        .animation(.easeOut(duration: 0.12), value: showInfo)
        .zIndex(10)
    }
}

/// The hover explanation under a top-bar control.
struct InfoCard: View {
    let title: String
    let lines: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.system(size: 12, weight: .semibold))
            ForEach(lines, id: \.self) { line in
                Text(line).font(.system(size: 12)).foregroundStyle(Theme.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(12)
        .frame(width: 280, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 10).fill(Theme.content))
        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.cardStroke))
        .shadow(color: .black.opacity(0.15), radius: 10, y: 4)
        .offset(y: 34)
        .transition(.opacity)
        .allowsHitTesting(false)
    }
}

/// Rebuilds its content when the theme or appearance changes, so every color is re-read.
struct ThemedRoot<Content: View>: View {
    @EnvironmentObject var model: AppModel
    @ViewBuilder var content: Content

    var body: some View {
        content.id(model.profile.lookID)
    }
}
