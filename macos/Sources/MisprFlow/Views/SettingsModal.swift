import AVFoundation
import MisprCore
import SwiftUI

/// Settings as a panel over the main window, with its own section list (like Wispr Flow).
struct SettingsModal: View {
    @EnvironmentObject var model: AppModel
    @State private var section: Section = .general

    enum Section: String, CaseIterable, Identifiable {
        case general = "General"
        case system = "System"
        case privacy = "Data and Privacy"

        var id: String { rawValue }

        var symbol: String {
            switch self {
            case .general: "slider.horizontal.3"
            case .system: "laptopcomputer"
            case .privacy: "checkmark.shield"
            }
        }
    }

    var body: some View {
        ZStack {
            Color.black.opacity(0.25).ignoresSafeArea()
                .onTapGesture { model.showSettings = false }
            HStack(spacing: 0) {
                sectionList
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        Text(section.rawValue).font(Theme.display(26)).padding(.bottom, 20)
                        switch section {
                        case .general: GeneralSettings()
                        case .system: SystemSettings()
                        case .privacy: PrivacySettings()
                        }
                        if let error = model.settingsError {
                            Text(error).font(.system(size: 12)).foregroundStyle(.red).padding(.top, 12)
                        }
                    }
                    .padding(32)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .background(Theme.content)
            }
            .frame(width: 860, height: 560)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .shadow(color: .black.opacity(0.2), radius: 30, y: 10)
            .overlay(alignment: .topTrailing) {
                Button { model.showSettings = false } label: { Image(systemName: "xmark") }
                    .buttonStyle(.plain).foregroundStyle(Theme.secondary).padding(16)
                    .keyboardShortcut(.cancelAction)
            }
        }
    }

    private var sectionList: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("SETTINGS").font(.system(size: 11, weight: .semibold)).tracking(0.8)
                .foregroundStyle(Theme.secondary).padding(.leading, 10).padding(.bottom, 8)
            ForEach(Section.allCases) { s in
                SidebarItem(title: s.rawValue, symbol: s.symbol, selected: section == s) { section = s }
            }
            Spacer()
            Text("Mispr Flow \(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "dev")")
                .font(.system(size: 11)).foregroundStyle(Theme.secondary).padding(.leading, 10)
        }
        .padding(.vertical, 22).padding(.horizontal, 10)
        .frame(width: 200)
        .background(Theme.sidebar)
    }
}

/// One setting: title, explanation, and a control on the right.
struct SettingRow<Control: View>: View {
    let title: String
    let detail: String
    @ViewBuilder var control: Control

    var body: some View {
        HStack(alignment: .center, spacing: 24) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title).font(.system(size: 13, weight: .semibold))
                Text(detail).font(.system(size: 12)).foregroundStyle(Theme.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer()
            control
        }
        .padding(.vertical, 14)
    }
}

struct SettingsGroup<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        VStack(spacing: 0) { content }
            .padding(.horizontal, 18)
            .background(RoundedRectangle(cornerRadius: 12).fill(Theme.card))
            .padding(.bottom, 16)
    }
}

extension AppModel {
    func binding(_ key: String) -> Binding<Bool> {
        Binding(get: { self.setting(key) }, set: { self.setSetting(key, $0) })
    }
}

struct GeneralSettings: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        SettingsGroup {
            SettingRow(title: "Shortcuts", detail: "Hold fn and speak; double-tap fn for hands-free.") {
                Text("fn").font(.system(size: 13, weight: .semibold))
                    .padding(.horizontal, 10).padding(.vertical, 4)
                    .background(RoundedRectangle(cornerRadius: 6).fill(Theme.content))
            }
            Divider()
            SettingRow(title: "Microphone", detail: microphone) {
                Button("Change…") {
                    NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.Sound-Settings.extension?input")!)
                }
            }
            Divider()
            SettingRow(title: "Dictation language", detail: "English. More languages (including auto-detect) are coming.") {
                Text("English").foregroundStyle(Theme.secondary)
            }
        }
        SettingsGroup {
            SettingRow(title: "Clean up dictation",
                       detail: "Removes um/uh, repeats, and retracted phrases, and fixes punctuation. Never adds words you didn't say. Off pastes exactly what Whisper heard.") {
                Toggle("", isOn: model.binding("cleanup")).toggleStyle(.switch).labelsHidden()
            }
        }
    }

    private var microphone: String {
        let name = AVCaptureDevice.default(for: .audio)?.localizedName ?? "No microphone found"
        return "\(name) (your Mac's default input; change it in Sound settings)."
    }
}

struct SystemSettings: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        SettingsGroup {
            SettingRow(title: "Launch at login", detail: "Start Mispr Flow when you log in, so fn is always ready.") {
                Toggle("", isOn: Binding(get: { model.launchAtLogin }, set: { model.launchAtLogin = $0 }))
                    .toggleStyle(.switch).labelsHidden()
            }
        }
        SettingsGroup {
            SettingRow(title: "Dictation and notification sounds", detail: "Start, stop, paste, and alert cues.") {
                Toggle("", isOn: model.binding("sounds")).toggleStyle(.switch).labelsHidden()
            }
        }
        SettingsGroup {
            SettingRow(title: "Setup guide", detail: "Permissions, model downloads, and the fn walkthrough.") {
                Button("Open…") { model.engine.send(.openSetup) }
            }
        }
    }
}

struct PrivacySettings: View {
    @EnvironmentObject var model: AppModel

    var body: some View {
        SettingsGroup {
            SettingRow(title: "Incognito",
                       detail: "Nothing is written to disk: audio stays in locked memory and is wiped right after transcription. History and Insights stop updating.") {
                Toggle("", isOn: model.binding("incognito")).toggleStyle(.switch).labelsHidden()
            }
        }
        SettingsGroup {
            SettingRow(title: "Saved dictations", detail: model.engine.recordingsDir?.path ?? "Waiting for the engine…") {
                Button("Show in Finder") {
                    if let dir = model.engine.recordingsDir { NSWorkspace.shared.open(dir) }
                }
                .disabled(model.engine.recordingsDir == nil)
            }
        }
        Text("Speech recognition and cleanup run entirely on this Mac. No audio or text is ever sent anywhere.")
            .font(.system(size: 12)).foregroundStyle(Theme.secondary)
    }
}
