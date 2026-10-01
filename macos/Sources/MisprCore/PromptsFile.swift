import Foundation

/// prompts.json, shared with the engine (mispr/prompts.py): the cleanup instructions, your
/// extra rules, the examples, and whether the no-invented-words guard is on.
public struct PromptDraft: Equatable {
    public var system: String
    public var extra: String
    public var examples: String  // editable "Said: … / Wrote: …" text
    public var guardOn: Bool

    public init(system: String, extra: String = "", examples: String, guardOn: Bool = true) {
        self.system = system
        self.extra = extra
        self.examples = examples
        self.guardOn = guardOn
    }

    public static let said = "Said:", wrote = "Wrote:"

    /// Same text format as prompts.format_examples.
    public static func format(_ pairs: [[String]]) -> String {
        pairs.filter { $0.count == 2 }.map { "\(said) \($0[0])\n\(wrote) \($0[1])" }.joined(separator: "\n\n")
    }

    /// Same rules as prompts.parse_examples: incomplete pairs are skipped.
    public static func parse(_ text: String) -> [[String]] {
        var pairs: [[String]] = [], pending: String?
        for raw in text.split(separator: "\n", omittingEmptySubsequences: false) {
            let line = raw.trimmingCharacters(in: .whitespaces)
            if line.hasPrefix(said) {
                pending = line.dropFirst(said.count).trimmingCharacters(in: .whitespaces)
            } else if line.hasPrefix(wrote), let p = pending {
                pairs.append([p, line.dropFirst(wrote.count).trimmingCharacters(in: .whitespaces)])
                pending = nil
            }
        }
        return pairs
    }

    /// The saved prompts, filling gaps from the engine's defaults.
    public static func load(from url: URL, defaults: DefaultPrompts) -> PromptDraft {
        let fallback = PromptDraft(system: defaults.system, examples: defaults.examples)
        guard let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return fallback }
        let system = (object["system"] as? String).flatMap { $0.isEmpty ? nil : $0 } ?? defaults.system
        let examples = (object["examples"] as? [[String]]).map(format) ?? defaults.examples
        return PromptDraft(system: system, extra: object["extra"] as? String ?? "", examples: examples,
                           guardOn: object["guard"] as? Bool ?? true)
    }

    public func save(to url: URL) throws {
        let object: [String: Any] = ["system": system, "extra": extra, "examples": Self.parse(examples), "guard": guardOn]
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys]).write(to: url, options: .atomic)
    }

    /// Arguments for the engine's try_prompt command.
    public func tryArgs(text: String) -> [String: Any] {
        ["text": text, "system": system, "extra": extra, "examples": examples, "guard": guardOn]
    }
}
