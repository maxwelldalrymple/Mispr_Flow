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
                IncognitoSwitch()
                Button { model.openProfile() } label: { AvatarView(size: 24) }
                    .buttonStyle(.plain).help("Profile")
            }
            .padding(.top, 9).padding(.trailing, 18)
        }
        .overlay {
            if model.showSettings { SettingsModal() }
        }
        .ignoresSafeArea()
        .foregroundStyle(Theme.text)
    }

    @ViewBuilder private var page: some View {
        switch model.page {
        case .home: HomeView()
        case .insights: InsightsView()
        case .notetaker:
            PlaceholderView(title: "Notetaker", symbol: "record.circle",
                            message: "Record a meeting, get a transcript with speaker labels and a summary, all on your Mac.",
                            detail: "Open a note with the ◉ button on the widget, or here. Live transcription is coming next.")
                .overlay(alignment: .topTrailing) {
                    Button { model.openNote() } label: {
                        Label("New note", systemImage: "plus").font(.system(size: 13, weight: .medium))
                    }
                    .buttonStyle(OutlineButton()).padding(.top, 36).padding(.trailing, 40)
                }
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
                VStack(alignment: .leading, spacing: 6) {
                    Text(on ? "Incognito is on" : "Incognito is off").font(.system(size: 12, weight: .semibold))
                    Text("When it's on, nothing you dictate is saved: the audio stays in locked memory and is wiped right after it's transcribed, and no text or history is written to disk. History and Insights pause until you turn it off.")
                        .font(.system(size: 12)).foregroundStyle(Theme.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                    Text("Dictation works the same either way, and nothing ever leaves your Mac.")
                        .font(.system(size: 12)).foregroundStyle(Theme.secondary)
                        .fixedSize(horizontal: false, vertical: true)
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
        .animation(.easeOut(duration: 0.12), value: showInfo)
        .zIndex(10)
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
