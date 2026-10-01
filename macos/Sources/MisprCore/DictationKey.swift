import Foundation

/// A shortcut key (the dictation key, the app switcher key), stored in settings.json as
/// {"kind": "fn" | "modifier" | "key" | "combo", "keycode": Int?, "label": String, "mods": [..]};
/// see mispr/hotkey.py. A combo is modifiers held together ("control", "option", "shift",
/// "command"), with one key or (two or more modifiers) on their own; its keycode is -1 then.
public struct DictationKey: Equatable {
    public enum Kind: String { case fn, modifier, key, combo }

    public var kind: Kind
    public var keycode: Int
    public var label: String
    public var mods: [String] = []

    /// Modifier names in the order macOS shows them, with their symbols.
    public static let comboOrder: [(name: String, symbol: String)] = [("control", "⌃"), ("option", "⌥"), ("shift", "⇧"), ("command", "⌘")]

    /// A combo (nil if it isn't one: a key needs a modifier; modifiers alone need two).
    public static func combo(mods: Set<String>, key: DictationKey? = nil) -> DictationKey? {
        let ordered = comboOrder.filter { mods.contains($0.name) }
        guard ordered.count == mods.count, !ordered.isEmpty, key != nil || ordered.count >= 2 else { return nil }
        let label = ordered.map(\.symbol).joined() + (key?.label ?? "")
        return DictationKey(kind: .combo, keycode: key?.keycode ?? -1, label: label, mods: ordered.map(\.name))
    }

    public static let fn = DictationKey(kind: .fn, keycode: 63, label: "fn")

    /// One side of a modifier key, by keycode (must match hotkey.MODIFIER_MASKS).
    public static let modifiers: [Int: String] = [
        59: "Left ⌃", 62: "Right ⌃", 56: "Left ⇧", 60: "Right ⇧",
        58: "Left ⌥", 61: "Right ⌥", 55: "Left ⌘", 54: "Right ⌘",
    ]

    /// Keys that can't be the dictation key: hands-free uses space/return/enter/delete,
    /// Esc cancels picking a key, Caps Lock toggles, and 179 is the globe key.
    public static let blocked: Set<Int> = [49, 36, 76, 51, 117, 53, 57, 179]

    static let named: [Int: String] = [
        122: "F1", 120: "F2", 99: "F3", 118: "F4", 96: "F5", 97: "F6", 98: "F7", 100: "F8",
        101: "F9", 109: "F10", 103: "F11", 111: "F12", 105: "F13", 107: "F14", 113: "F15",
        106: "F16", 64: "F17", 79: "F18", 80: "F19", 90: "F20",
        48: "Tab", 115: "Home", 119: "End", 116: "Page Up", 121: "Page Down",
        123: "←", 124: "→", 125: "↓", 126: "↑", 50: "`", 10: "§",
    ]

    public init(kind: Kind, keycode: Int, label: String, mods: [String] = []) {
        self.kind = kind
        self.keycode = keycode
        self.label = label
        self.mods = mods
    }

    /// The key for a modifier press (flagsChanged), or nil if it isn't one we support.
    public static func modifier(keycode: Int) -> DictationKey? {
        if keycode == 63 { return .fn }
        return modifiers[keycode].map { DictationKey(kind: .modifier, keycode: keycode, label: $0) }
    }

    /// The key for a regular key press, or nil if it's blocked.
    public static func key(keycode: Int, characters: String?) -> DictationKey? {
        guard !blocked.contains(keycode) else { return nil }
        let label = named[keycode] ?? characters?.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        guard let label, !label.isEmpty else { return DictationKey(kind: .key, keycode: keycode, label: "Key \(keycode)") }
        return DictationKey(kind: .key, keycode: keycode, label: label)
    }

    /// True for keys that also type something (letters, digits, punctuation): using one as
    /// the dictation key means it no longer types.
    public var typesCharacters: Bool {
        kind == .key && Self.named[keycode] == nil
    }

    public var json: [String: Any] {
        guard kind == .combo else { return ["kind": kind.rawValue, "keycode": keycode, "label": label] }
        return ["kind": kind.rawValue, "keycode": keycode >= 0 ? keycode : NSNull(), "label": label, "mods": mods]
    }

    public init?(json: Any?) {
        guard let object = json as? [String: Any], let kindName = object["kind"] as? String,
              let kind = Kind(rawValue: kindName) else { return nil }
        if kind == .combo {
            guard let mods = object["mods"] as? [String], !mods.isEmpty else { return nil }
            self.init(kind: kind, keycode: object["keycode"] as? Int ?? -1, label: object["label"] as? String ?? "keys", mods: mods)
            return
        }
        guard let keycode = object["keycode"] as? Int else { return nil }
        self.init(kind: kind, keycode: keycode, label: object["label"] as? String ?? "key")
    }
}
