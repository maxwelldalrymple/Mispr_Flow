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
                            detail: "Coming soon. The ◉ button on the widget already opens a meeting pill.")
        case .style:
            PlaceholderView(title: "Style", symbol: "textformat",
                            message: "Choose how your dictation is written in messages, work chat, email, and everything else.",
                            detail: "Coming soon. Today cleanup keeps your words and fixes punctuation everywhere.")
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
