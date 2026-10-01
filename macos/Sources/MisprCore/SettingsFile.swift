import Foundation

/// settings.json, shared with the engine (mispr/settings.py). The app changes a key, writes
/// the file (keeping keys it doesn't know), then tells the engine to reload.
public struct SettingsFile {
    public let url: URL

    public static let defaults: [String: Bool] = ["incognito": false, "auto_enter": false, "cleanup": true, "sounds": true, "onboarded": false]

    public static var defaultURL: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Mispr_Flow/settings.json")
    }

    public init(url: URL = SettingsFile.defaultURL) {
        self.url = url
    }

    public func read() -> [String: Any] {
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [:] }
        return object
    }

    public func bool(_ key: String) -> Bool {
        read()[key] as? Bool ?? Self.defaults[key] ?? false
    }

    public var dictationKey: DictationKey { DictationKey(json: read()["hotkey"]) ?? .fn }

    public func setDictationKey(_ key: DictationKey) throws {
        try set("hotkey", key.json)
    }

    /// The app switcher key, or nil when it's off.
    public var switchKey: DictationKey? { DictationKey(json: read()["switch_hotkey"]) }

    public func setSwitchKey(_ key: DictationKey?) throws {
        try set("switch_hotkey", key?.json ?? NSNull())
    }

    /// Spoken nicknames for apps: ["c": "Google Chrome"].
    public var nicknames: [String: String] { read()["app_nicknames"] as? [String: String] ?? [:] }

    public func setNicknames(_ nicknames: [String: String]) throws {
        try set("app_nicknames", nicknames)
    }

    public func set(_ key: String, _ value: Any) throws {
        var object = read()
        object[key] = value
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        let data = try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys])
        try data.write(to: url, options: .atomic)
    }
}
