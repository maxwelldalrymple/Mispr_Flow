import Foundation

/// Cuts a 16 kHz mono stream into chunks at natural pauses, so each chunk is a phrase or two
/// from one side of the call (good for Whisper and for telling speakers apart).
public struct Segmenter {
    public static let rate = 16_000.0
    static let frame = 480  // 30 ms

    public var minSpeech = 1.0     // seconds of speech before a pause can end a chunk
    public var pauseToCut = 0.7    // seconds of quiet that end a chunk
    public var maxChunk = 15.0     // seconds; cut anyway (long monologues)

    private var buffer: [Float] = []
    private var chunkStart = 0.0   // stream time of buffer[0], seconds
    private var position = 0       // samples consumed so far
    private var speechFrames = 0
    private var silentFrames = 0
    private var noiseFloor: Float = 0.004
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
            let speaking = rms > max(0.006, noiseFloor * 3)
            if speaking {
                speechFrames += 1
                silentFrames = 0
            } else {
                silentFrames += 1
                noiseFloor = noiseFloor * 0.95 + rms * 0.05  // track the room's background level
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

    public init() {}

    public mutating func add(stream: String, speaker: Int, offset: Double, text: String, voice: String = "person") {
        if stream == "them" { voices[max(1, speaker)] = voice }  // the latest guess wins (it firms up over time)
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        let line = Line(stream: stream, speaker: stream == "you" ? 0 : max(1, speaker), offset: offset, text: trimmed)
        let index = lines.firstIndex { $0.offset > offset } ?? lines.count
        lines.insert(line, at: index)
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
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        encoder.dateEncodingStrategy = .custom { date, encoder in
            var container = encoder.singleValueContainer()
            try container.encode(formatter.string(from: date))
        }
        let url = day.appendingPathComponent("\(id).json")
        try encoder.encode(self).write(to: url, options: .atomic)
        return url
    }

    /// "2026-09-30_23-16-04-000", like recordings.
    public static func newID(_ date: Date = Date()) -> String {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd_HH-mm-ss"
        return f.string(from: date) + "-000"
    }
}
