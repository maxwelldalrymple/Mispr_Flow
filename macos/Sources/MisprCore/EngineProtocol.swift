import Foundation

/// Messages between the app and the Python engine (see mispr/host.py).
///
/// Engine -> app: stdout lines "@mispr {json}"; anything else on stdout is ignored.
/// App -> engine: one JSON object per line on stdin, e.g. {"cmd": "open_setup"}.
public enum EngineEvent: Equatable {
    /// Sent once at startup: where the engine keeps its data.
    case hello(recordingsDir: URL, settingsFile: URL)
    /// A dictation was saved (not sent in Incognito).
    case saved(URL)
    /// A well-formed event this version doesn't know.
    case unknown(String)

    public static let prefix = "@mispr "

    public static func parse(_ line: String) -> EngineEvent? {
        guard line.hasPrefix(prefix),
              let data = line.dropFirst(prefix.count).data(using: .utf8),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let event = object["event"] as? String
        else { return nil }
        switch event {
        case "hello":
            guard let recordings = object["recordings_dir"] as? String,
                  let settings = object["settings_path"] as? String else { return nil }
            return .hello(recordingsDir: URL(fileURLWithPath: recordings), settingsFile: URL(fileURLWithPath: settings))
        case "saved":
            guard let path = object["path"] as? String else { return nil }
            return .saved(URL(fileURLWithPath: path))
        default:
            return .unknown(event)
        }
    }
}

public enum EngineCommand: String {
    case openSetup = "open_setup"
    case reloadSettings = "reload_settings"
    case quit

    public var line: String { "{\"cmd\": \"\(rawValue)\"}\n" }
}

/// Splits a byte stream into lines, keeping a partial last line until its newline arrives.
public struct LineSplitter {
    private var pending = Data()

    public init() {}

    public mutating func feed(_ data: Data) -> [String] {
        pending.append(data)
        var lines: [String] = []
        while let newline = pending.firstIndex(of: UInt8(ascii: "\n")) {
            let line = pending[pending.startIndex..<newline]
            lines.append(String(decoding: line, as: UTF8.self))
            pending = Data(pending[pending.index(after: newline)...])
        }
        return lines
    }
}
