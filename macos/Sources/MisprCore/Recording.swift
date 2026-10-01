import Foundation

/// An app a dictation was recorded in or pasted into.
public struct AppRef: Codable, Hashable {
    public var app: String?
    public var bundleId: String?
    public var url: String?
    public var pageTitle: String?

    public init(app: String? = nil, bundleId: String? = nil, url: String? = nil, pageTitle: String? = nil) {
        self.app = app
        self.bundleId = bundleId
        self.url = url
        self.pageTitle = pageTitle
    }

    enum CodingKeys: String, CodingKey {
        case app, url
        case bundleId = "bundle_id"
        case pageTitle = "page_title"
    }
}

/// One saved dictation: the JSON record the engine writes next to each WAV
/// (mispr/storage.py). Unknown fields are ignored so older and newer records both load.
public struct Recording: Codable, Identifiable, Hashable {
    public enum Status: String, Codable {
        case pasted, copied, cancelled
        case command  // a voice command (app switcher), not dictation

        /// Dictation that produced text (what word counts and speed are measured on).
        public var isDictation: Bool { self == .pasted || self == .copied }
    }

    public var id: String
    public var startedAt: Date
    public var endedAt: Date
    public var durationS: Double
    public var status: Status
    public var transcript: String
    public var rawTranscript: String?
    public var words: Int
    public var recordedIn: AppRef?
    public var pastedInto: AppRef?
    public var audioFile: String?
    /// The JSON file this was read from (not stored in it).
    public var fileURL: URL?

    enum CodingKeys: String, CodingKey {
        case id, status, transcript, words
        case startedAt = "started_at"
        case endedAt = "ended_at"
        case durationS = "duration_s"
        case rawTranscript = "raw_transcript"
        case recordedIn = "recorded_in"
        case pastedInto = "pasted_into"
        case audioFile = "audio_file"
    }

    public init(id: String, startedAt: Date, endedAt: Date, durationS: Double, status: Status,
                transcript: String, rawTranscript: String? = nil, words: Int,
                recordedIn: AppRef? = nil, pastedInto: AppRef? = nil, audioFile: String? = nil, fileURL: URL? = nil) {
        self.id = id
        self.startedAt = startedAt
        self.endedAt = endedAt
        self.durationS = durationS
        self.status = status
        self.transcript = transcript
        self.rawTranscript = rawTranscript
        self.words = words
        self.recordedIn = recordedIn
        self.pastedInto = pastedInto
        self.audioFile = audioFile
        self.fileURL = fileURL
    }

    /// The app the words went to (or were meant for).
    public var app: AppRef? { pastedInto ?? recordedIn }

    public var audioURL: URL? {
        guard let audioFile, let fileURL else { return nil }
        return fileURL.deletingLastPathComponent().appendingPathComponent(audioFile)
    }

    /// Cleanup changed the words (fillers removed, a correction applied, punctuation fixed).
    public var wasCleaned: Bool {
        guard let rawTranscript, !transcript.isEmpty else { return false }
        return rawTranscript != transcript
    }
}

public enum RecordingStore {
    /// Every record under `dir` (one folder per day), newest first. Unreadable files are skipped.
    public static func load(from dir: URL, fileManager: FileManager = .default) -> [Recording] {
        guard let days = try? fileManager.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil) else { return [] }
        let decoder = makeDecoder()
        var records: [Recording] = []
        for day in days where day.hasDirectoryPath {
            let files = (try? fileManager.contentsOfDirectory(at: day, includingPropertiesForKeys: nil)) ?? []
            for file in files where file.pathExtension == "json" {
                guard let data = try? Data(contentsOf: file),
                      var record = try? decoder.decode(Recording.self, from: data) else { continue }
                record.fileURL = file
                records.append(record)
            }
        }
        return records.sorted { $0.startedAt > $1.startedAt }
    }

    /// Delete a recording's JSON and audio.
    public static func delete(_ record: Recording, fileManager: FileManager = .default) throws {
        if let audio = record.audioURL, fileManager.fileExists(atPath: audio.path) {
            try fileManager.removeItem(at: audio)
        }
        if let json = record.fileURL {
            try fileManager.removeItem(at: json)
        }
    }

    public static func makeDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        let fractional = ISO8601DateFormatter()
        fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let whole = ISO8601DateFormatter()
        decoder.dateDecodingStrategy = .custom { decoder in
            let text = try decoder.singleValueContainer().decode(String.self)
            if let date = fractional.date(from: text) ?? whole.date(from: text) { return date }
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "bad date \(text)"))
        }
        return decoder
    }
}
