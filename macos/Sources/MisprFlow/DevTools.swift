import AVFoundation
import MisprCore

/// The developer flags' reports (`--detect`, `--segment`), built here so they can be tested.
enum DevTools {
    static func micPermissionName(_ status: AVAuthorizationStatus) -> String {
        switch status {
        case .notDetermined: "notDetermined"
        case .restricted: "restricted"
        case .denied: "denied"
        case .authorized: "authorized"
        @unknown default: "unknown"
        }
    }

    /// What meeting detection sees, line by line.
    static func detectReport(_ snapshot: SystemSnapshot, mic: AVAuthorizationStatus, screenAllowed: Bool) -> String {
        let found = MeetingDetector.detect(snapshot)
        var lines = [
            "source: \(found.source.rawValue)  title: \(found.title ?? "-")  why: \(found.evidence)",
            "mic in use: \(snapshot.micInUse)",
            "microphone permission: \(micPermissionName(mic)), screen & system audio: \(screenAllowed ? "allowed" : "not allowed")",
        ]
        lines += snapshot.windowTitles.map { "window: \($0.bundleID): \($0.title)" }
        return lines.joined(separator: "\n")
    }

    /// Where the chunker cuts a 16-bit mono WAV (the 44-byte header is skipped).
    static func segmentReport(wav data: Data) -> String {
        guard data.count > 44 else { return "not a WAV with audio" }
        let samples = data.dropFirst(44).withUnsafeBytes { Array($0.bindMemory(to: Int16.self)) }.map { Float($0) / 32768 }
        var segmenter = Segmenter()
        let chunks = segmenter.feed(samples) + [segmenter.flush()].compactMap { $0 }
        return chunks.map { String(format: "chunk at %5.1fs  %4.1fs long", $0.start, Double($0.samples.count) / 16_000) }
            .joined(separator: "\n")
    }
}
