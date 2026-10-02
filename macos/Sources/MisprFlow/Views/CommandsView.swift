import MisprCore
import SwiftUI

/// One thing you can say: the words, what happens, and the engine's command kind for it
/// (tests/test_command_catalog.py parses every phrase here and checks the kind, so this page
/// can't drift from what the app really does).
struct Say: Identifiable, Hashable {
    let words: String
    let does: String
    let kind: String
    var id: String { words }
}

struct CommandGroup: Identifiable {
    let title: String
    let symbol: String
    let tint: Color
    let blurb: String
    let phrases: [Say]
    var id: String { title }
}

enum CommandCatalog {
    static let groups: [CommandGroup] = [
        CommandGroup(title: "Click anything", symbol: "cursorarrow.click.2", tint: Color(red: 0.31, green: 0.49, blue: 1.0),
                     blurb: "Buttons, links, fields, tabs and pictures in any app, by the words on them. Several matches get numbers: say one.", phrases: [
            Say(words: "click Sign in", does: "Moves the mouse there and clicks", kind: "click"),
            Say(words: "click the search box", does: "Clicks into the page's search field", kind: "click"),
            Say(words: "double click Budget", does: "Opens it, like a double-click", kind: "click"),
            Say(words: "right click the logo", does: "Opens its menu", kind: "click"),
            Say(words: "click", does: "Clicks wherever the mouse is", kind: "click"),
            Say(words: "move the mouse to Pricing", does: "Points without clicking (menus that open on hover)", kind: "hover"),
            Say(words: "show numbers", does: "Numbers everything clickable on screen", kind: "show_numbers"),
            Say(words: "7", does: "Clicks number 7", kind: "number"),
            Say(words: "never mind", does: "Hides the numbers", kind: "hide_numbers"),
        ]),
        CommandGroup(title: "Keyboard and typing", symbol: "keyboard", tint: Color(red: 0.96, green: 0.42, blue: 0.25),
                     blurb: "Any key or shortcut, and exact text, in whatever app you're in.", phrases: [
            Say(words: "press enter", does: "Return (also escape, tab, delete, space…)", kind: "keys"),
            Say(words: "press command shift t", does: "Any shortcut: command, shift, option, control + a key", kind: "keys"),
            Say(words: "press tab 3 times", does: "A key, several times", kind: "keys"),
            Say(words: "down 3", does: "The down arrow 3 times (up, left, right too)", kind: "keys"),
            Say(words: "type hello@example.com", does: "Types exactly what you say, no cleanup", kind: "type"),
            Say(words: "select all", does: "⌘A", kind: "keys"),
            Say(words: "copy", does: "⌘C (also cut, paste)", kind: "keys"),
            Say(words: "undo", does: "⌘Z (redo too)", kind: "keys"),
            Say(words: "save", does: "⌘S", kind: "keys"),
        ]),
        CommandGroup(title: "Editing text", symbol: "character.cursor.ibeam", tint: Color(red: 0.84, green: 0.31, blue: 0.78),
                     blurb: "“That” is what you just dictated.", phrases: [
            Say(words: "scratch that", does: "Deletes your last dictation", kind: "that"),
            Say(words: "select that", does: "Selects it", kind: "that"),
            Say(words: "capitalize that", does: "Retypes it with a capital (uppercase, lowercase too)", kind: "that"),
            Say(words: "new line", does: "A line break, without sending", kind: "keys"),
            Say(words: "new paragraph", does: "Two line breaks", kind: "keys"),
            Say(words: "delete last word", does: "⌥⌫", kind: "keys"),
            Say(words: "select last word", does: "Selects the word before the cursor", kind: "keys"),
            Say(words: "go to end of line", does: "⌘→ (start of line, end of document…)", kind: "keys"),
        ]),
        CommandGroup(title: "Apps and windows", symbol: "macwindow.on.rectangle", tint: Color(red: 0.55, green: 0.36, blue: 0.96),
                     blurb: "Say an app's name, or a nickname you gave it. It never opens an app on a guess.", phrases: [
            Say(words: "Chrome", does: "Brings Chrome to the front (opens it if needed)", kind: "switch"),
            Say(words: "Chrome beside VS Code", does: "Puts them side by side", kind: "beside"),
            Say(words: "Chrome 80%", does: "Resizes Chrome to 80% of the screen", kind: "size"),
            Say(words: "minimize", does: "Minimizes the window in front", kind: "minimize"),
            Say(words: "expand", does: "Fills the screen with it", kind: "expand"),
            Say(words: "close", does: "Closes the window in front", kind: "close"),
            Say(words: "quit", does: "Quits the app you're in", kind: "quit"),
            Say(words: "window 2", does: "Brings its second window forward", kind: "window"),
            Say(words: "set nickname Scooby to Chrome", does: "Teaches a nickname", kind: "nickname"),
        ]),
        CommandGroup(title: "Window layout and desktops", symbol: "rectangle.split.2x1", tint: Color(red: 0.27, green: 0.55, blue: 0.95),
                     blurb: "Arrange the window in front, and move between desktops.", phrases: [
            Say(words: "left half", does: "Snaps it to the left half (right, top, bottom too)", kind: "snap"),
            Say(words: "left third", does: "Thirds and two thirds", kind: "snap"),
            Say(words: "top left corner", does: "A quarter of the screen", kind: "snap"),
            Say(words: "center", does: "Centered, not full size", kind: "snap"),
            Say(words: "move to the other screen", does: "To your other display", kind: "other_screen"),
            Say(words: "mission control", does: "All your windows", kind: "mission"),
            Say(words: "show desktop", does: "Clears the windows away", kind: "mission"),
            Say(words: "app windows", does: "Every window of the app in front", kind: "mission"),
            Say(words: "next desktop", does: "The next Space (previous too)", kind: "desktop"),
            Say(words: "desktop 2", does: "Space 2 (turn on its ⌃2 shortcut in Keyboard settings)", kind: "desktop"),
        ]),
        CommandGroup(title: "Tabs and the web", symbol: "safari", tint: Color(red: 0.13, green: 0.68, blue: 0.62),
                     blurb: "Works even while you're typing in a box. Misheard sites are matched to the 1,000 most visited.", phrases: [
            Say(words: "YouTube tab", does: "Jumps to your YouTube tab (opens YouTube if none)", kind: "site_tab"),
            Say(words: "GitHub tab 2", does: "The second GitHub tab", kind: "site_tab"),
            Say(words: "new tab", does: "⌘T", kind: "shortcut"),
            Say(words: "close tab", does: "⌘W", kind: "shortcut"),
            Say(words: "reopen tab", does: "Brings back the last closed tab", kind: "shortcut"),
            Say(words: "tab left", does: "The tab to the left (tab right too)", kind: "shortcut"),
            Say(words: "tab 3", does: "The third tab", kind: "shortcut"),
            Say(words: "tabs side by side", does: "Splits two tabs next to each other", kind: "split_tab"),
            Say(words: "reload", does: "Reloads the page", kind: "shortcut"),
            Say(words: "back", does: "Goes back a page", kind: "shortcut"),
            Say(words: "google best pizza near me", does: "Searches Google", kind: "search"),
            Say(words: "search youtube for lofi beats", does: "YouTube, Amazon, Wikipedia, GitHub, Reddit, Maps…", kind: "search"),
            Say(words: "go to apple.com", does: "Opens the site", kind: "go_to"),
            Say(words: "find pricing on the page", does: "⌘F and types it", kind: "find"),
        ]),
        CommandGroup(title: "Scrolling", symbol: "arrow.up.and.down.circle", tint: Color(red: 0.98, green: 0.58, blue: 0.19),
                     blurb: "Scrolls whatever is under the mouse.", phrases: [
            Say(words: "scroll down", does: "Scrolls down", kind: "scroll"),
            Say(words: "scroll up a lot", does: "Scrolls up further", kind: "scroll"),
            Say(words: "page down", does: "One screen at a time", kind: "scroll"),
            Say(words: "scroll to the top", does: "All the way up (or bottom)", kind: "scroll_end"),
            Say(words: "scroll the sidebar down", does: "Scrolls a named part of the window", kind: "scroll_in"),
            Say(words: "show grid", does: "A 3×3 grid: say a square to zoom in, again and again, then “click”", kind: "grid"),
            Say(words: "drag Budget to the Trash", does: "Drags one thing onto another", kind: "drag"),
        ]),
        CommandGroup(title: "Media and sound", symbol: "speaker.wave.2.fill", tint: Color(red: 0.93, green: 0.33, blue: 0.47),
                     blurb: "Whatever is playing, in any app.", phrases: [
            Say(words: "pause", does: "Play or pause", kind: "media"),
            Say(words: "next song", does: "Skips the track", kind: "media"),
            Say(words: "skip forward 30 seconds", does: "Jumps ahead (or back)", kind: "seek"),
            Say(words: "volume up", does: "Louder (or down, or volume 40)", kind: "volume"),
            Say(words: "mute", does: "Mutes the Mac (unmute to undo)", kind: "volume"),
            Say(words: "mute mic", does: "Silences your microphone", kind: "mic"),
            Say(words: "mute tab", does: "Mutes the browser tab", kind: "mute_tab"),
        ]),
        CommandGroup(title: "Your Mac", symbol: "laptopcomputer", tint: Color(red: 0.45, green: 0.5, blue: 0.58),
                     blurb: "Log out, restart and shut down always show macOS's own confirmation first.", phrases: [
            Say(words: "screenshot", does: "The whole screen, saved with your screenshots", kind: "system"),
            Say(words: "screenshot area", does: "Drag to pick an area", kind: "system"),
            Say(words: "screen recording", does: "Starts recording the screen", kind: "system"),
            Say(words: "stop recording", does: "Saves the movie", kind: "system"),
            Say(words: "lock screen", does: "Locks the Mac", kind: "system"),
            Say(words: "sleep", does: "Puts the Mac to sleep", kind: "system"),
            Say(words: "shut down", does: "Asks macOS to shut down (you confirm)", kind: "system"),
            Say(words: "dark mode on", does: "Dark or light mode (off, or just “dark mode” to flip)", kind: "dark_mode"),
            Say(words: "brightness up", does: "Screen brighter (down, dimmer)", kind: "brightness"),
            Say(words: "wifi off", does: "Wi-Fi on or off", kind: "wifi"),
            Say(words: "use AirPods", does: "Plays sound through them (any output, by name)", kind: "output"),
            Say(words: "control center", does: "Opens Control Center (or notification center)", kind: "mission"),
            Say(words: "launchpad", does: "Opens Launchpad", kind: "mission"),
            Say(words: "spotlight budget", does: "Searches with Spotlight", kind: "spotlight"),
        ]),
        CommandGroup(title: "Mispr Flow and power tools", symbol: "bolt.fill", tint: Color(red: 0.95, green: 0.73, blue: 0.15),
                     blurb: "Switch the app's modes, run your Shortcuts, repeat yourself, and make your own commands in Settings.", phrases: [
            Say(words: "auto enter on", does: "Auto-Enter on (off, or “auto enter mode” to flip)", kind: "mode"),
            Say(words: "incognito mode", does: "Incognito on or off", kind: "mode"),
            Say(words: "sounds off", does: "The app's sounds", kind: "mode"),
            Say(words: "run shortcut morning", does: "Runs a shortcut from the Shortcuts app", kind: "run_shortcut"),
            Say(words: "again", does: "Repeats the last command", kind: "again"),
            Say(words: "do that 3 times", does: "Repeats it 3 times", kind: "again"),
        ]),
        CommandGroup(title: "Menus", symbol: "filemenu.and.selection", tint: Color(red: 0.2, green: 0.62, blue: 0.86),
                     blurb: "Any menu item of the app in front, by its name. Never anything that deletes for good.", phrases: [
            Say(words: "export", does: "File › Export (any item, by its name)", kind: "switch"),
            Say(words: "show sidebar", does: "View › Show Sidebar", kind: "switch"),
            Say(words: "file new window", does: "A menu, then its item", kind: "menu"),
            Say(words: "click Export", does: "On screen, or else in the menus", kind: "click"),
        ]),
        CommandGroup(title: "Folders and files", symbol: "folder.fill", tint: Color(red: 0.36, green: 0.66, blue: 0.27),
                     blurb: "Searches your whole Mac (Full Disk Access) and opens it in Finder.", phrases: [
            Say(words: "open folder Projects", does: "Finds and opens it in Finder", kind: "open_folder"),
            Say(words: "open Budget", does: "In Finder: a folder or file in the one you're viewing", kind: "open"),
        ]),
    ]

    static var all: [Say] { groups.flatMap(\.phrases) }
}

/// The Voice Commands page: everything you can do on your Mac by voice, searchable.
struct CommandsView: View {
    @EnvironmentObject var model: AppModel
    @State private var query = ""
    @State private var picked: String?  // a category, or nil for all

    private var groups: [CommandGroup] {
        let q = query.lowercased().trimmingCharacters(in: .whitespaces)
        return CommandCatalog.groups.compactMap { group in
            if let picked, group.title != picked { return nil }
            guard !q.isEmpty else { return group }
            if group.title.lowercased().contains(q) { return group }
            let hits = group.phrases.filter { $0.words.lowercased().contains(q) || $0.does.lowercased().contains(q) }
            return hits.isEmpty ? nil : CommandGroup(title: group.title, symbol: group.symbol, tint: group.tint, blurb: group.blurb, phrases: hits)
        }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                hero
                controls
                if groups.isEmpty {
                    Text("Nothing matches “\(query)”. Try “tab”, “click” or “volume”.")
                        .font(.system(size: 13)).foregroundStyle(Theme.secondary).padding(.vertical, 30)
                } else {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 380), spacing: 16, alignment: .top)], spacing: 16) {
                        ForEach(groups) { CommandCard(group: $0) }
                    }
                }
                footer
            }
            .padding(.horizontal, 34).padding(.vertical, 30)
        }
    }

    private var hero: some View {
        HStack(alignment: .center, spacing: 24) {
            VStack(alignment: .leading, spacing: 10) {
                Text("Your voice is the mouse").font(Theme.display(34))
                Text("Hold your switch key, say what you want, let go. Apps, tabs, buttons, menus, media and your Mac itself, without touching anything.")
                    .font(.system(size: 14)).foregroundStyle(Theme.secondary).fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 8) {
                    Text("Hold").font(.system(size: 13, weight: .medium)).foregroundStyle(Theme.secondary)
                    if let key = model.switchKey {
                        KeyCap(label: key.label)
                        Text("speak · let go").font(.system(size: 13, weight: .medium)).foregroundStyle(Theme.secondary)
                    } else {
                        Button("Choose a switch key") { model.settingsSection = .general; model.showSettings = true }
                            .buttonStyle(.borderedProminent).controlSize(.small)
                    }
                }
                .padding(.top, 4)
            }
            Spacer(minLength: 0)
            VoiceOrb().frame(width: 132, height: 132)
        }
        .padding(26)
        .background(
            RoundedRectangle(cornerRadius: 20)
                .fill(LinearGradient(colors: [Theme.accent.opacity(0.22), Theme.card], startPoint: .topLeading, endPoint: .bottomTrailing))
        )
        .overlay(RoundedRectangle(cornerRadius: 20).stroke(Theme.accent.opacity(0.25), lineWidth: 1))
    }

    private var controls: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass").foregroundStyle(Theme.secondary)
                TextField("Find a command: “tab”, “click”, “volume”…", text: $query).textFieldStyle(.plain).font(.system(size: 14))
                if !query.isEmpty {
                    Button { query = "" } label: { Image(systemName: "xmark.circle.fill") }.buttonStyle(.plain).foregroundStyle(Theme.secondary)
                }
            }
            .padding(.horizontal, 14).padding(.vertical, 10)
            .background(RoundedRectangle(cornerRadius: 12).fill(Theme.card))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.cardStroke, lineWidth: 1))
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    Chip(title: "All", tint: Theme.accent, on: picked == nil) { picked = nil }
                    ForEach(CommandCatalog.groups) { group in
                        Chip(title: group.title, tint: group.tint, on: picked == group.title) {
                            picked = picked == group.title ? nil : group.title
                        }
                    }
                }
            }
        }
    }

    private var footer: some View {
        HStack(alignment: .top, spacing: 16) {
            InfoTile(symbol: "keyboard", title: "Your keys", lines: [
                "Dictate: hold \(model.dictationKey.label)",
                "Commands: hold \(model.switchKey?.label ?? "a switch key (Settings › General)")",
                "Auto-Enter on/off: \(model.autoEnterKey?.label ?? "off")",
                "Meeting note: ⌥M",
            ])
            InfoTile(symbol: "ear", title: "When it mishears", lines: [
                "Site names are matched to the top 1,000 sites",
                "Apps open only when it's sure",
                "Several matches? It shows numbers",
                "Every command is in Home › Commands",
            ])
            InfoTile(symbol: "lock.shield", title: "Never by voice", lines: [
                "Emptying the Trash or erasing",
                "Shutting down without your OK",
                "Anything over the internet",
                "Opening an app on a guess",
            ])
        }
    }
}

struct CommandCard: View {
    let group: CommandGroup

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                Image(systemName: group.symbol)
                    .font(.system(size: 17, weight: .semibold)).foregroundStyle(.white)
                    .frame(width: 38, height: 38)
                    .background(RoundedRectangle(cornerRadius: 11).fill(LinearGradient(colors: [group.tint, group.tint.opacity(0.7)],
                                                                                         startPoint: .top, endPoint: .bottom)))
                VStack(alignment: .leading, spacing: 2) {
                    Text(group.title).font(.system(size: 16, weight: .semibold))
                    Text(group.blurb).font(.system(size: 12)).foregroundStyle(Theme.secondary).fixedSize(horizontal: false, vertical: true)
                }
            }
            VStack(alignment: .leading, spacing: 7) {
                ForEach(group.phrases) { say in
                    HStack(alignment: .firstTextBaseline, spacing: 10) {
                        SpeechBubble(text: say.words, tint: group.tint)
                        Text(say.does).font(.system(size: 12.5)).foregroundStyle(Theme.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                        Spacer(minLength: 0)
                    }
                }
            }
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 16).fill(Theme.card))
        .overlay(alignment: .top) {
            Rectangle().fill(group.tint).frame(height: 3).clipShape(RoundedRectangle(cornerRadius: 2)).padding(.horizontal, 18)
        }
    }
}

/// A phrase to say, drawn as a small speech bubble.
struct SpeechBubble: View {
    let text: String
    let tint: Color

    var body: some View {
        HStack(spacing: 5) {
            Image(systemName: "quote.opening").font(.system(size: 8, weight: .bold)).foregroundStyle(tint)
            Text(text).font(.system(size: 12.5, weight: .semibold))
        }
        .padding(.horizontal, 10).padding(.vertical, 5)
        .background(RoundedRectangle(cornerRadius: 9).fill(tint.opacity(0.14)))
        .overlay(RoundedRectangle(cornerRadius: 9).stroke(tint.opacity(0.3), lineWidth: 1))
        .fixedSize()
    }
}

struct KeyCap: View {
    let label: String

    var body: some View {
        Text(label).font(.system(size: 14, weight: .bold, design: .rounded))
            .padding(.horizontal, 10).padding(.vertical, 4)
            .background(RoundedRectangle(cornerRadius: 7).fill(Theme.content))
            .overlay(RoundedRectangle(cornerRadius: 7).stroke(Theme.cardStroke, lineWidth: 1))
            .shadow(color: .black.opacity(0.15), radius: 0, y: 2)
    }
}

struct Chip: View {
    let title: String
    let tint: Color
    let on: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title).font(.system(size: 12.5, weight: .medium))
                .padding(.horizontal, 12).padding(.vertical, 6)
                .foregroundStyle(on ? Color.white : Theme.text)
                .background(Capsule().fill(on ? tint : Theme.card))
                .overlay(Capsule().stroke(on ? tint : Theme.cardStroke, lineWidth: 1))
        }
        .buttonStyle(.plain)
    }
}

struct InfoTile: View {
    let symbol: String
    let title: String
    let lines: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(title, systemImage: symbol).font(.system(size: 13, weight: .semibold))
            ForEach(lines, id: \.self) { line in
                Text(line).font(.system(size: 12)).foregroundStyle(Theme.secondary).fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .background(RoundedRectangle(cornerRadius: 14).fill(Theme.card))
    }
}

/// The hero's glow: concentric rings around a waveform, gently breathing.
struct VoiceOrb: View {
    @State private var breathe = false

    var body: some View {
        ZStack {
            ForEach(0..<3) { ring in
                Circle()
                    .stroke(Theme.accent.opacity(0.35 - Double(ring) * 0.1), lineWidth: 1.5)
                    .scaleEffect(breathe ? 1.0 - Double(ring) * 0.14 : 0.9 - Double(ring) * 0.14)
            }
            Circle().fill(RadialGradient(colors: [Theme.accent.opacity(0.9), Theme.accent.opacity(0.55)],
                                         center: .center, startRadius: 2, endRadius: 46))
                .frame(width: 74, height: 74)
                .shadow(color: Theme.accent.opacity(0.5), radius: breathe ? 18 : 8)
            Image(systemName: "waveform").font(.system(size: 30, weight: .semibold)).foregroundStyle(.white)
        }
        .onAppear {
            withAnimation(.easeInOut(duration: 2.2).repeatForever(autoreverses: true)) { breathe = true }
        }
    }
}
