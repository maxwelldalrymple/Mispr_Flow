import Foundation

/// Cuts a 16 kHz mono stream into chunks at natural pauses, so each chunk is a phrase or two
/// from one side of the call (good for Whisper and for telling speakers apart).
public struct Segmenter {
    public static let rate = 16_000.0
    static let frame = 480  // 30 ms

    public var minSpeech = 0.6     // seconds of speech before a pause can end a chunk
    public var pauseToCut = 0.5    // seconds of quiet that end a chunk
    public var maxChunk = 10.0     // seconds; cut anyway (long monologues, music under speech)

    private var buffer: [Float] = []
    private var chunkStart = 0.0   // stream time of buffer[0], seconds
    private var position = 0       // samples consumed so far
    private var speechFrames = 0
    private var silentFrames = 0
    // Frame levels of the last ~5 s, starting from a quiet room.
    private var recentLevels = [Float](repeating: 0.001, count: 166)
    private var pending: [Float] = []

    public init() {}

    /// Feed samples; returns any finished chunks as (start time in seconds, samples).
    public mutating func feed(_ samples: [Float]) -> [(start: Double, samples: [Float])] {
        pending += samples
        var chunks: [(Double, [Float])] = []
        while pending.count >= Self.frame {
            let frame = Array(pending.prefix(Self.frame))
            pending.removeFirst(Self.frame)
            if buffer.isEmpty { chunkStart = Double(position) / Self.rate }
            buffer += frame
            position += Self.frame
            let rms = (frame.reduce(0) { $0 + $1 * $1 } / Float(frame.count)).squareRoot()
            // Background = the quietest moment of the last 5 s (speech always has gaps
            // between syllables, so this stays low even under music); speech is well above it.
            recentLevels.append(rms)
            if recentLevels.count > 166 { recentLevels.removeFirst(recentLevels.count - 166) }
            let floor = recentLevels.min() ?? 0
            let speaking = rms > max(0.003, floor * 2.5)
            if speaking {
                speechFrames += 1
                silentFrames = 0
            } else {
                silentFrames += 1
            }
            let seconds = Double(buffer.count) / Self.rate
            let speech = Double(speechFrames * Self.frame) / Self.rate
            let pause = Double(silentFrames * Self.frame) / Self.rate
            if (speech >= minSpeech && pause >= pauseToCut) || seconds >= maxChunk {
                if let chunk = take() { chunks.append(chunk) }
            } else if speechFrames == 0 && seconds >= 2 {
                reset()  // only silence so far: drop it
            }
        }
        return chunks
    }

    /// The phrase being spoken right now (for live, not-yet-final text), if any.
    public var inProgress: (start: Double, samples: [Float])? {
        Double(speechFrames * Self.frame) / Self.rate >= 0.5 ? (chunkStart, buffer) : nil
    }

    /// Whatever is left when recording stops.
    public mutating func flush() -> (start: Double, samples: [Float])? {
        buffer += pending
        pending = []
        return Double(speechFrames * Self.frame) / Self.rate >= 0.3 ? take() : { reset(); return nil }()
    }

    private mutating func take() -> (Double, [Float])? {
        defer { reset() }
        return speechFrames > 3 ? (chunkStart, buffer) : nil
    }

    private mutating func reset() {
        buffer = []
        speechFrames = 0
        silentFrames = 0
    }
}

public enum WAV {
    /// 16-bit mono PCM WAV bytes for float samples in [-1, 1].
    public static func data(_ samples: [Float], rate: Int = 16_000) -> Data {
        var d = Data()
        func u32(_ v: UInt32) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
        func u16(_ v: UInt16) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
        let bytes = UInt32(samples.count * 2)
        d.append(contentsOf: Array("RIFF".utf8)); u32(36 + bytes); d.append(contentsOf: Array("WAVE".utf8))
        d.append(contentsOf: Array("fmt ".utf8)); u32(16); u16(1); u16(1); u32(UInt32(rate)); u32(UInt32(rate * 2)); u16(2); u16(16)
        d.append(contentsOf: Array("data".utf8)); u32(bytes)
        for s in samples { u16(UInt16(bitPattern: Int16(max(-1, min(1, s)) * 32767))) }
        return d
    }
}

/// Speakers playing the call out loud: the mic hears the other side again, so their words
/// would show up twice (once as them, once as "You"). Mic text that repeats what the other
/// side said around the same time is that echo: it's dropped, or cut out of what you said.
public enum Echo {
    /// How far apart (seconds) the same words can land on the two streams.
    public static let window = 10.0
    /// A mic line this much made of their words is all echo.
    public static let dropShare = 0.6
    /// Shared runs shorter than this ("I think", "yeah") are coincidence, not echo...
    public static let minRun = 3
    /// ...unless they're the whole of a short mic line ("Yep, that's right.").
    public static let minWholeLine = 2

    /// "CI/CD on re:Invent!" -> ["cicd", "on", "reinvent"]: lowercase, letters and digits only.
    public static func words(_ text: String) -> [String] {
        text.lowercased().split(whereSeparator: \.isWhitespace)
            .map { String($0.unicodeScalars.filter(CharacterSet.alphanumerics.contains).map(Character.init)) }
    }

    /// The mic text with the other side's words taken out, or nil when nothing of yours is left.
    public static func clean(_ mine: String, against theirs: [String]) -> String? {
        let original = mine.split(whereSeparator: \.isWhitespace).map(String.init)
        let tokens = words(mine)
        let other = theirs.flatMap(words).filter { !$0.isEmpty }
        guard !tokens.isEmpty, !other.isEmpty else { return mine }
        // Match on real words only ("-" between sentences doesn't break a run).
        let spoken = tokens.indices.filter { !tokens[$0].isEmpty }
        let said = spoken.map { tokens[$0] }
        var echoed = [Bool](repeating: false, count: tokens.count)
        var i = 0
        while i < said.count {
            var best = 0
            for j in other.indices {
                var k = 0
                while i + k < said.count, j + k < other.count, said[i + k] == other[j + k] { k += 1 }
                best = max(best, k)
            }
            let wholeLine = i == 0 && best == said.count && best >= minWholeLine
            if best >= minRun || wholeLine {
                for k in i..<(i + best) { echoed[spoken[k]] = true }
                i += best
            } else {
                i += 1
            }
        }
        let echoCount = spoken.filter { echoed[$0] }.count
        if echoCount == 0 { return mine }
        // Punctuation-only bits go with the echo when no word of yours is next to them.
        for index in tokens.indices where tokens[index].isEmpty {
            let before = spoken.last { $0 < index }, after = spoken.first { $0 > index }
            if (before.map { echoed[$0] } ?? true) && (after.map { echoed[$0] } ?? true) { echoed[index] = true }
        }
        let kept = original.indices.filter { !echoed[$0] }
        if Double(echoCount) >= dropShare * Double(max(1, spoken.count)) || kept.filter({ !tokens[$0].isEmpty }).count < 2 {
            return nil
        }
        return kept.map { original[$0] }.joined(separator: " ")
    }
}

/// The transcript as it comes in: lines from "you" (mic) and "them" (system audio, with a
/// speaker number when several voices were told apart), kept in time order.
public struct LiveTranscript: Equatable {
    public struct Line: Equatable, Identifiable {
        public var id = UUID()
        public var stream: String   // "you" or "them"
        public var speaker: Int     // 0 for you; 1, 2... for voices on the other side
        public var offset: Double   // seconds from the start
        public var text: String
    }

    public private(set) var lines: [Line] = []
    /// Names given to speakers (rename "Female 1" to "Priya").
    public var names: [Int: String] = [:]
    /// What each voice on the other side sounds like: "male", "female", or "person".
    public private(set) var voices: [Int: String] = [:]
    /// Live, not-yet-final text per stream ("you"/"them"), shown greyed until the phrase ends.
    public private(set) var partials: [String: Line] = [:]
    /// Mic lines dropped or trimmed as echo of the other side.
    public private(set) var echoesRemoved = 0

    /// Show what's being said right now; ignored once that phrase has been finalized.
    public mutating func setPartial(stream: String, offset: Double, text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let finalized = lines.contains { $0.stream == stream && $0.offset >= offset - 0.05 }
        guard !trimmed.isEmpty, !finalized else { return }
        if stream == "you" {
            let heard = theirText(near: offset) + [partials["them"]?.text].compactMap { $0 }
            guard let mine = Echo.clean(trimmed, against: heard) else { partials["you"] = nil; return }
            partials[stream] = Line(stream: stream, speaker: 0, offset: offset, text: mine)
            return
        }
        partials[stream] = Line(stream: stream, speaker: 0, offset: offset, text: trimmed)
    }

    /// What the other side said within the echo window of `offset`, in time order.
    private func theirText(near offset: Double) -> [String] {
        lines.filter { $0.stream == "them" && abs($0.offset - offset) <= Echo.window }.map(\.text)
    }

    /// Who a live line is from: you, or the other side's most recent speaker.
    public func partialLabel(_ stream: String) -> String {
        if stream == "you" { return "You" }
        return lines.last { $0.stream == "them" }.map(label) ?? "Them"
    }

    public func partialSpeaker(_ stream: String) -> Int {
        stream == "you" ? 0 : (lines.last { $0.stream == "them" }?.speaker ?? 1)
    }

    public init() {}

    public mutating func add(stream: String, speaker: Int, offset: Double, text: String, voice: String = "person") {
        if stream == "them" { voices[max(1, speaker)] = voice }  // the latest guess wins (it firms up over time)
        if let live = partials[stream], live.offset <= offset + 0.05 { partials[stream] = nil }  // the phrase is final now
        var trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        if stream == "you" {  // the speakers' sound coming back in through the mic
            guard let mine = Echo.clean(trimmed, against: theirText(near: offset)) else { echoesRemoved += 1; return }
            if mine != trimmed { echoesRemoved += 1 }
            trimmed = mine
        }
        let line = Line(stream: stream, speaker: stream == "you" ? 0 : max(1, speaker), offset: offset, text: trimmed)
        let index = lines.firstIndex { $0.offset > offset } ?? lines.count
        lines.insert(line, at: index)
        if stream == "them" { removeEcho(near: offset) }  // the mic's copy may have arrived first
    }

    /// Re-check mic lines near `offset` now that more of the other side is known.
    private mutating func removeEcho(near offset: Double) {
        for index in lines.indices.reversed() where lines[index].stream == "you" && abs(lines[index].offset - offset) <= Echo.window {
            let heard = theirText(near: lines[index].offset)
            if let mine = Echo.clean(lines[index].text, against: heard) {
                if mine != lines[index].text { lines[index].text = mine; echoesRemoved += 1 }
            } else {
                lines.remove(at: index)
                echoesRemoved += 1
            }
        }
    }

    /// Two voices were the same person: their lines become `into`'s (a name given to either is kept).
    public mutating func merge(_ speaker: Int, into: Int) {
        guard speaker != into else { return }
        for i in lines.indices where lines[i].stream == "them" && lines[i].speaker == speaker { lines[i].speaker = into }
        if (names[into] ?? "").isEmpty, let name = names[speaker] { names[into] = name }
        names[speaker] = nil
        voices[speaker] = nil
    }

    public var themSpeakers: Set<Int> { Set(lines.filter { $0.stream == "them" }.map(\.speaker)) }

    /// "You", a name you gave, or what the voice sounds like, numbered in order of first
    /// appearance: "Male 1", "Female 1", "Male 2"; "Person 1" when it can't tell.
    public func label(_ line: Line) -> String {
        if line.stream == "you" { return "You" }
        if let name = names[line.speaker], !name.isEmpty { return name }
        let kind = voices[line.speaker] ?? "person"
        var order: [Int] = []
        for l in lines where l.stream == "them" && !order.contains(l.speaker) && (voices[l.speaker] ?? "person") == kind {
            order.append(l.speaker)
        }
        let n = (order.firstIndex(of: line.speaker) ?? 0) + 1
        return "\(kind.prefix(1).uppercased() + kind.dropFirst()) \(n)"
    }

    /// Consecutive lines from the same person, shown as one group of bubbles.
    public var groups: [(label: String, speaker: Int, lines: [Line])] {
        var out: [(String, Int, [Line])] = []
        for line in lines {
            let label = label(line)
            if let last = out.last, last.0 == label { out[out.count - 1].2.append(line) } else { out.append((label, line.speaker, [line])) }
        }
        return out
    }

    /// For the engine's summarize/ask commands.
    public var engineLines: [[String: String]] {
        lines.map { ["speaker": label($0), "text": $0.text] }
    }

    /// The saved note (Meeting format).
    public func meeting(id: String, title: String, startedAt: Date, duration: Double, source: String,
                        thoughts: String, summary: Meeting.Summary?) -> Meeting {
        var people = [Meeting.Participant(name: "You", role: nil, isMe: true)]
        for speaker in themSpeakers.sorted() {
            let line = lines.first { $0.stream == "them" && $0.speaker == speaker }!
            people.append(.init(name: label(line), role: nil, isMe: false))
        }
        return Meeting(id: id, title: title.isEmpty ? "Meeting" : title, startedAt: startedAt, durationS: duration, app: source,
                       participants: people,
                       transcript: lines.map { Meeting.Line(speaker: label($0), startS: $0.offset, text: $0.text) },
                       summary: summary, myThoughts: thoughts)
    }
}

extension Meeting {
    /// Write as JSON (the engine's/samples' format) to `dir/<day>/<id>.json`; returns the file.
    @discardableResult
    public func save(in dir: URL) throws -> URL {
        let day = dir.appendingPathComponent(String(id.prefix(10)))
        try FileManager.default.createDirectory(at: day, withIntermediateDirectories: true)
        let url = day.appendingPathComponent("\(id).json")
        try write(to: url)
        return url
    }

    /// Write back to the file it was loaded from (edits like renaming a person).
    public func rewrite() throws {
        guard let fileURL else { throw CocoaError(.fileNoSuchFile) }
        try write(to: fileURL)
    }

    private func write(to url: URL) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        encoder.dateEncodingStrategy = .custom { date, encoder in
            var container = encoder.singleValueContainer()
            try container.encode(formatter.string(from: date))
        }
        try encoder.encode(self).write(to: url, options: .atomic)
    }

    /// "2026-09-30_23-16-04-123", like recordings (milliseconds, so a note started right after
    /// discarding another never reuses its name).
    public static func newID(_ date: Date = Date()) -> String {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd_HH-mm-ss-SSS"
        return f.string(from: date)
    }
}
