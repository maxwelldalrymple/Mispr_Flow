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
    /// A meeting chunk was transcribed (speaker: 0 = you, 1+ = voices on the other side).
    /// `partial`: live text for a phrase still being spoken (replaced by the final text).
    /// `last`: a chunk with several speakers comes back as several lines; only its last one
    /// has last = true (older engines send one line per chunk, so it defaults to true).
    case chunkText(meeting: String, stream: String, speaker: Int, offset: Double, text: String, voice: String,
                   partial: Bool = false, last: Bool = true)
    /// The meeting summary (nil if the model couldn't write one), with a suggested title.
    case summary(meeting: String, summary: Meeting.Summary?, title: String)
    /// An answer to "Ask anything" / "What did I miss?".
    case answer(meeting: String, question: String, text: String)
    /// A dictation was saved (not sent in Incognito).
    case saved(URL)
    /// The widget's note button or ⌥M: show the note window (and start/stop recording).
    case openNote(start: Bool)
    /// A meeting recording started or stopped (from the note window or the widget's pill).
    case meeting(active: Bool)
    /// The engine changed settings.json itself (a nickname set by voice): re-read it.
    case settingsChanged
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
            return .openNote(start: object["start"] as? Bool ?? false)
        case "chunk_text":
            return .chunkText(meeting: object["id"] as? String ?? "", stream: object["stream"] as? String ?? "them",
                              speaker: object["speaker"] as? Int ?? 0, offset: object["offset"] as? Double ?? 0,
                              text: object["text"] as? String ?? "", voice: object["voice"] as? String ?? "person",
                              partial: object["partial"] as? Bool ?? false, last: object["last"] as? Bool ?? true)
        case "summary":
            let summary = Meeting.Summary(json: object["summary"])
            let title = (object["summary"] as? [String: Any])?["title"] as? String ?? ""
            return .summary(meeting: object["id"] as? String ?? "", summary: summary, title: title)
        case "answer":
            return .answer(meeting: object["id"] as? String ?? "", question: object["question"] as? String ?? "",
                           text: object["text"] as? String ?? "")
        case "settings_changed":
            return .settingsChanged
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
    case transcribeChunk = "transcribe_chunk"
    case summarize
    case ask
    case meetingLevel = "meeting_level"
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
