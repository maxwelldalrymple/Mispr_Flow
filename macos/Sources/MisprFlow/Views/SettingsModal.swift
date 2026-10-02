import AVFoundation
import MisprCore
import SwiftUI

/// Settings as a panel over the main window, with its own section list (like Wispr Flow).
struct SettingsModal: View {
    @EnvironmentObject var model: AppModel
    private var section: Section { model.settingsSection }

    enum Section: String, CaseIterable, Identifiable {
        case profile = "Profile"
        case general = "General"
        case system = "System"
        case privacy = "Data and Privacy"

        var id: String { rawValue }

        var symbol: String {
            switch self {
            case .profile: "person.crop.circle"
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
                        case .profile: ProfileSettings()
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
                SidebarItem(title: s.rawValue, symbol: s.symbol, selected: section == s) { model.settingsSection = s }
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
            SettingRow(title: "Dictation key",
                       detail: "Hold \(model.dictationKey.label) and speak; double-tap it for hands-free. Click the key to change it.") {
                KeyRecorder()
            }
            Divider()
            SettingRow(title: "App switcher key",
                       detail: model.switchKey.map { "Hold \($0.label), say an app like “Chrome” or a nickname, and let go: it comes to the front. Say “set nickname C to Chrome” to add one." }
                        ?? "Off. Choose a key or combo (like ⌃⌥) to switch apps by voice: hold it, say the app, let go.") {
                KeyRecorder(slot: .appSwitch)
            }
            if model.switchKey != nil {
                NicknameList().padding(.bottom, 12)
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
            Divider()
            SettingRow(title: "Tutorial", detail: "A quick tour of every page, in 8 steps.") {
                Button("Show") { model.startTour() }
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

struct ProfileSettings: View {
    @EnvironmentObject var model: AppModel
    private var profile: Profile { model.profile }

    var body: some View {
        SettingsGroup {
            HStack(spacing: 18) {
                AvatarView(size: 64)
                VStack(alignment: .leading, spacing: 8) {
                    Text("Hey \(model.firstName)!").font(Theme.display(22))
                    HStack(spacing: 8) {
                        Button("Choose photo…") { profile.choosePhoto() }
                        if profile.photo != nil { Button("Remove") { profile.removePhoto() } }
                    }
                    if profile.photo == nil {
                        HStack(spacing: 6) {
                            ForEach(Profile.avatarColors, id: \.self) { hex in
                                Circle().fill(Color(nsColor: Theme.nsColor(hex: hex))).frame(width: 18, height: 18)
                                    .overlay(Circle().stroke(Theme.text, lineWidth: profile.avatarColor == hex ? 2 : 0).padding(-3))
                                    .onTapGesture { profile.avatarColor = hex }
                                    .help("Avatar color")
                            }
                        }
                        .padding(.leading, 3)
                    }
                }
                Spacer()
            }
            .padding(.vertical, 16)
        }
        SettingsGroup {
            field("Name", "Your full name", text: Binding(get: { profile.name }, set: { profile.name = $0 }))
            Divider()
            field("Nickname", "What Mispr Flow calls you (\"Hey Max\")", text: Binding(get: { profile.nickname }, set: { profile.nickname = $0 }))
            Divider()
            field("What you do", "e.g. engineer, student, founder. Saved for personalization later.", text: Binding(get: { profile.role }, set: { profile.role = $0 }))
        }
        SettingsGroup {
            SettingRow(title: "Appearance", detail: "Follow macOS, or always light or dark.") {
                Picker("", selection: Binding(get: { profile.appearance }, set: { profile.appearance = $0 })) {
                    ForEach(Profile.Appearance.allCases) { Text($0.rawValue).tag($0) }
                }
                .pickerStyle(.segmented).labelsHidden().frame(width: 210)
            }
        }
        Text("THEME").font(.system(size: 11, weight: .semibold)).tracking(0.8).foregroundStyle(Theme.secondary)
            .padding(.bottom, 10)
        LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 12), count: 3), spacing: 12) {
            ForEach(Palette.all) { palette in
                ThemeCard(palette: palette, selected: profile.themeID == palette.id) { profile.themeID = palette.id }
            }
        }
        Text("Your profile stays on this Mac.").font(.system(size: 12)).foregroundStyle(Theme.secondary).padding(.top, 14)
    }

    private func field(_ title: String, _ detail: String, text: Binding<String>) -> some View {
        SettingRow(title: title, detail: detail) {
            TextField(title, text: text).textFieldStyle(.roundedBorder).frame(width: 220)
        }
    }
}

/// A theme preview: a mini window in the palette's light and dark colors.
struct ThemeCard: View {
    let palette: Palette
    let selected: Bool
    let choose: () -> Void

    var body: some View {
        Button(action: choose) {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 0) {
                    preview(palette.light)
                    preview(palette.dark)
                }
                .frame(height: 64)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                HStack {
                    Text(palette.name).font(.system(size: 13, weight: .medium))
                    Spacer()
                    if selected { Image(systemName: "checkmark.circle.fill").foregroundStyle(Theme.accent) }
                }
            }
            .padding(10)
            .background(RoundedRectangle(cornerRadius: 12).fill(Theme.card))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(selected ? Theme.accent : Theme.cardStroke, lineWidth: selected ? 2 : 1))
        }
        .buttonStyle(.plain)
    }

    private func preview(_ c: Palette.Colors) -> some View {
        HStack(spacing: 0) {
            Rectangle().fill(color(c.sidebar)).frame(width: 18)
            VStack(alignment: .leading, spacing: 5) {
                RoundedRectangle(cornerRadius: 2).fill(color(c.text)).frame(width: 30, height: 4)
                RoundedRectangle(cornerRadius: 2).fill(color(c.secondary)).frame(width: 40, height: 3)
                RoundedRectangle(cornerRadius: 3).fill(color(c.accent)).frame(width: 22, height: 10)
            }
            .padding(8)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(color(c.content))
        }
    }

    private func color(_ hex: UInt32) -> Color { Color(nsColor: Theme.nsColor(hex: hex)) }
}

/// Click, then press the key you want to dictate with (fn, one side of a modifier, or any
/// other key). Esc cancels. Keys hands-free needs are refused.
struct KeyRecorder: View {
    /// Which shortcut this picks: the dictation key, or the app switcher key (which can also
    /// be a combo like ⌃⌥ or ⌥S, and can be off).
    enum Slot { case dictation, appSwitch }

    @EnvironmentObject var model: AppModel
    var slot: Slot = .dictation
    @State private var listening = false
    @State private var monitor: Any?
    @State private var message: String?
    @State private var combo = ComboPicker()

    private var current: String {
        slot == .dictation ? model.dictationKey.label : model.switchKey?.label ?? "Off"
    }

    var body: some View {
        VStack(alignment: .trailing, spacing: 6) {
            HStack(spacing: 8) {
                if slot == .dictation && model.dictationKey != .fn && !listening {
                    Button("Use fn") { model.setDictationKey(.fn); message = nil }.buttonStyle(.link).font(.system(size: 12))
                }
                if slot == .appSwitch && model.switchKey != nil && !listening {
                    Button("Turn off") { model.setSwitchKey(nil); message = nil }.buttonStyle(.link).font(.system(size: 12))
                }
                Button(action: toggle) {
                    Text(listening ? (slot == .appSwitch ? "Press a key or combo…" : "Press a key…") : current)
                        .font(.system(size: 13, weight: .semibold))
                        .frame(minWidth: 60)
                        .padding(.horizontal, 12).padding(.vertical, 5)
                        .background(RoundedRectangle(cornerRadius: 7).fill(listening ? Theme.accentSoft : Theme.content))
                        .overlay(RoundedRectangle(cornerRadius: 7).stroke(listening ? Theme.accent : Theme.cardStroke, lineWidth: listening ? 2 : 1))
                }
                .buttonStyle(.plain)
                .help(listening ? "Press the key you want, or Esc to cancel"
                      : slot == .dictation ? "Click to change the dictation key" : "Click to choose the app switcher key or combo")
            }
            if let message {
                Text(message).font(.system(size: 11)).foregroundStyle(Theme.secondary)
                    .multilineTextAlignment(.trailing).frame(maxWidth: 260, alignment: .trailing)
            }
        }
        .onDisappear(perform: stop)
    }

    private func toggle() {
        listening ? stop() : start()
    }

    private func start() {
        listening = true
        combo = ComboPicker()
        message = slot == .appSwitch ? "Press one key, hold a combo like ⌃⌥ and let go, or press ⌥ plus a letter. Esc cancels."
            : model.dictationKey == .fn ? "To keep fn, press Esc. fn itself can't be picked here while it's the dictation key." : nil
        monitor = NSEvent.addLocalMonitorForEvents(matching: [.keyDown, .flagsChanged]) { event in
            handle(event)
            return nil  // don't let the key do anything else while picking
        }
    }

    private func stop() {
        if let monitor { NSEvent.removeMonitor(monitor) }
        monitor = nil
        listening = false
    }

    private func handle(_ event: NSEvent) {
        let keyDown = event.type == .keyDown, code = Int(event.keyCode)
        let characters = keyDown ? event.charactersIgnoringModifiers : nil
        let pick = slot == .appSwitch
            ? combo.feed(keyDown: keyDown, keyCode: code, characters: characters, flags: event.modifierFlags, dictation: model.dictationKey)
            : Self.pick(keyDown: keyDown, keyCode: code, characters: characters, flags: event.modifierFlags)
        switch pick {
        case .cancel:
            stop()
            message = nil
        case let .refuse(reason):
            message = reason
        case let .choose(key, warning):
            choose(key)
            message = warning
        case .ignore:
            break
        }
    }

    enum Pick: Equatable {
        case cancel, ignore
        case refuse(String)
        case choose(DictationKey, warning: String?)
    }

    /// What a key event means while picking: Esc cancels, blocked keys are refused, a modifier
    /// counts on press (flagsChanged also fires on release), and a typing key comes with a warning.
    static func pick(keyDown: Bool, keyCode: Int, characters: String?, flags: NSEvent.ModifierFlags) -> Pick {
        if keyDown {
            if keyCode == 53 { return .cancel }
            guard let key = DictationKey.key(keycode: keyCode, characters: characters) else {
                return .refuse("That key is needed for hands-free or by macOS. Pick another.")
            }
            return .choose(key, warning: key.typesCharacters ? "“\(key.label)” won't type while Mispr Flow is running." : nil)
        }
        guard let key = DictationKey.modifier(keycode: keyCode), flags.contains(modifierFlag(keyCode)) else { return .ignore }
        return .choose(key, warning: nil)
    }

    static func modifierFlag(_ keyCode: Int) -> NSEvent.ModifierFlags {
        switch keyCode {
        case 59, 62: .control
        case 56, 60: .shift
        case 58, 61: .option
        case 54, 55: .command
        default: .function
        }
    }

    private func choose(_ key: DictationKey) {
        if slot == .dictation { model.setDictationKey(key) } else { model.setSwitchKey(key) }
        message = nil
        stop()
    }
}

/// Picks the app switcher shortcut from key events while listening: a key on its own, one
/// side of a modifier (pressed and released alone), a combo of modifiers (held together, then
/// let go), or modifiers plus a key.
struct ComboPicker {
    private var peak: Set<String> = []  // most modifiers held at once in this press
    private var onlySide: Int?  // the first modifier pressed (left/right matters when it's the only one)

    static func names(_ flags: NSEvent.ModifierFlags) -> Set<String> {
        var out: Set<String> = []
        if flags.contains(.control) { out.insert("control") }
        if flags.contains(.option) { out.insert("option") }
        if flags.contains(.shift) { out.insert("shift") }
        if flags.contains(.command) { out.insert("command") }
        return out
    }

    mutating func feed(keyDown: Bool, keyCode: Int, characters: String?, flags: NSEvent.ModifierFlags,
                       dictation: DictationKey) -> KeyRecorder.Pick {
        let held = Self.names(flags)
        if keyDown {
            if keyCode == 53 && held.isEmpty { return .cancel }
            guard let key = DictationKey.key(keycode: keyCode, characters: characters) else {
                return .refuse("That key is needed for hands-free or by macOS. Pick another.")
            }
            reset()
            if held.isEmpty { return Self.unlessDictation(key, dictation) }
            return DictationKey.combo(mods: held, key: key).map { .choose($0, warning: nil) } ?? .ignore
        }
        if keyCode == 63 {
            return flags.contains(.function) ? .refuse("fn can't be the app switcher key. Try ⌃⌥, Right ⌘ or F5.") : .ignore
        }
        if !held.isEmpty {  // pressing (or still holding) modifiers: decide when all are let go
            if peak.isEmpty { onlySide = keyCode }
            peak.formUnion(held)
            return .ignore
        }
        guard !peak.isEmpty else { return .ignore }
        defer { reset() }
        if peak.count >= 2, let combo = DictationKey.combo(mods: peak) { return .choose(combo, warning: nil) }
        if let side = onlySide, let key = DictationKey.modifier(keycode: side) { return Self.unlessDictation(key, dictation) }
        return .ignore
    }

    private mutating func reset() {
        peak = []
        onlySide = nil
    }

    private static func unlessDictation(_ key: DictationKey, _ dictation: DictationKey) -> KeyRecorder.Pick {
        if key.kind == dictation.kind && key.keycode == dictation.keycode {
            return .refuse("That's your dictation key. Pick a different one.")
        }
        return .choose(key, warning: key.typesCharacters ? "“\(key.label)” won't type while Mispr Flow is running." : nil)
    }
}

/// Spoken nicknames for apps (also added by voice: “set nickname C to Chrome”).
struct NicknameList: View {
    @EnvironmentObject var model: AppModel
    @State private var nickname = ""
    @State private var app = ""
    @State private var apps: [String] = []

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("NICKNAMES").font(.system(size: 10.5, weight: .semibold)).tracking(0.8).foregroundStyle(Theme.secondary)
            ForEach(model.nicknames.sorted(by: { $0.key < $1.key }), id: \.key) { nick, target in
                HStack(spacing: 8) {
                    Text("“\(nick)”").font(.system(size: 13, weight: .medium))
                    Image(systemName: "arrow.right").font(.system(size: 10)).foregroundStyle(Theme.secondary)
                    Text(target).font(.system(size: 13))
                    Spacer()
                    Button { model.setNickname(nick, app: nil) } label: { Image(systemName: "xmark.circle.fill") }
                        .buttonStyle(.plain).foregroundStyle(Theme.secondary).help("Remove this nickname")
                }
                .padding(.horizontal, 10).padding(.vertical, 6)
                .background(RoundedRectangle(cornerRadius: 8).fill(Theme.content))
            }
            HStack(spacing: 8) {
                TextField("Nickname, e.g. C", text: $nickname).textFieldStyle(.roundedBorder).frame(width: 150)
                Picker("", selection: $app) {
                    Text("Choose an app").tag("")
                    ForEach(apps, id: \.self) { Text($0).tag($0) }
                }
                .labelsHidden().frame(maxWidth: 220)
                Button("Add") {
                    model.setNickname(nickname, app: app)
                    nickname = ""
                    app = ""
                }
                .disabled(nickname.trimmingCharacters(in: .whitespaces).isEmpty || app.isEmpty)
            }
        }
        .onAppear { if apps.isEmpty { apps = Self.installedApps() } }
    }

    /// App names in the usual folders, like the engine finds them (mispr/apps.py).
    static func installedApps(in dirs: [String] = ["/Applications", "/Applications/Utilities", "/System/Applications",
                                                   "/System/Applications/Utilities", NSHomeDirectory() + "/Applications"]) -> [String] {
        var names = Set<String>()
        for dir in dirs {
            for name in (try? FileManager.default.contentsOfDirectory(atPath: dir)) ?? [] where name.hasSuffix(".app") {
                names.insert(String(name.dropLast(4)))
            }
        }
        return names.sorted { $0.localizedCaseInsensitiveCompare($1) == .orderedAscending }
    }
}
