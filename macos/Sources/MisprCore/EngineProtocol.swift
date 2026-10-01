import Foundation

/// Messages between the app and the Python engine (see mispr/host.py).
///
/// Engine -> app: stdout lines "@mispr {json}"; anything else on stdout is ignored.
/// App -> engine: one JSON object per line on stdin, e.g. {"cmd": "open_setup"}.
public enum EngineEvent: Equatable {
    /// Sent once at startup: where the engine keeps its data, and its built-in prompts.
    case hello(recordingsDir: URL, settingsFile: URL, promptsFile: URL?, defaultPrompts: DefaultPrompts?)
    /// The result of a "Try it" run on the Prompts page.
    case tried(TryResult)
    /// A dictation was saved (not sent in Incognito).
    case saved(URL)
    /// The widget's note button was clicked: show the note window.
    case openNote
    /// A meeting recording started or stopped (from the note window or the widget's pill).
    case meeting(active: Bool)
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
            let prompts = (object["prompts_path"] as? String).map { URL(fileURLWithPath: $0) }
            let defaults = (object["default_prompts"] as? [String: Any]).flatMap { d -> DefaultPrompts? in
                guard let system = d["system"] as? String, let examples = d["examples"] as? String else { return nil }
                return DefaultPrompts(system: system, examples: examples)
            }
            return .hello(recordingsDir: URL(fileURLWithPath: recordings), settingsFile: URL(fileURLWithPath: settings),
                          promptsFile: prompts, defaultPrompts: defaults)
        case "tried":
            return .tried(TryResult(output: object["output"] as? String ?? "", applied: object["applied"] as? Bool ?? false,
                                    rejected: object["rejected"] as? String, ms: object["ms"] as? Int ?? 0))
        case "saved":
            guard let path = object["path"] as? String else { return nil }
            return .saved(URL(fileURLWithPath: path))
        case "open_note":
            return .openNote
        case "meeting":
            guard let active = object["active"] as? Bool else { return nil }
            return .meeting(active: active)
        default:
            return .unknown(event)
        }
    }
}

public struct DefaultPrompts: Equatable {
    public var system: String
    public var examples: String  // "Said: … / Wrote: …" text
}

public struct TryResult: Equatable {
    public var output: String
    public var applied: Bool
    public var rejected: String?
    public var ms: Int
}

public enum EngineCommand: String {
    case openSetup = "open_setup"
    case reloadSettings = "reload_settings"
    case startMeeting = "start_meeting"
    case stopMeeting = "stop_meeting"
    case tryPrompt = "try_prompt"
    case quit

    public var line: String { line() }

    /// The command as one JSON line, with optional arguments alongside "cmd".
    public func line(_ args: [String: Any] = [:]) -> String {
        var object = args
        object["cmd"] = rawValue
        let data = (try? JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])) ?? Data("{}".utf8)
        return String(decoding: data, as: UTF8.self) + "\n"
    }
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
