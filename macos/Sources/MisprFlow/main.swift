import AppKit
import AVFoundation
import MisprCore

// Development: `MisprFlow --detect` prints what meeting detection sees right now, then exits.
if CommandLine.arguments.contains("--detect") {
    let snapshot = SystemProbe.snapshot()
    let found = MeetingDetector.detect(snapshot)
    print("source: \(found.source.rawValue)  title: \(found.title ?? "-")  why: \(found.evidence)")
    print("mic in use: \(snapshot.micInUse)")
    let mic = ["notDetermined", "restricted", "denied", "authorized"][AVCaptureDevice.authorizationStatus(for: .audio).rawValue]
    print("microphone permission: \(mic), screen & system audio: \(CGPreflightScreenCaptureAccess() ? "allowed" : "not allowed")")
    for w in snapshot.windowTitles { print("window: \(w.bundleID): \(w.title)") }
    exit(0)
}

// Development: `MisprFlow --segment file.wav` prints where the chunker would cut a recording.
if let i = CommandLine.arguments.firstIndex(of: "--segment"), i + 1 < CommandLine.arguments.count,
   let data = FileManager.default.contents(atPath: CommandLine.arguments[i + 1]), data.count > 44 {
    let samples = data.dropFirst(44).withUnsafeBytes { Array($0.bindMemory(to: Int16.self)) }.map { Float($0) / 32768 }
    var segmenter = Segmenter()
    for chunk in segmenter.feed(samples) + [segmenter.flush()].compactMap({ $0 }) {
        print(String(format: "chunk at %5.1fs  %4.1fs long", chunk.start, Double(chunk.samples.count) / 16_000))
    }
    exit(0)
}

// Development: `open "Mispr Flow.app" --args --record-test` records 8 s of mic + system audio as the
// app (so its own permissions apply) and writes chunk sizes and levels to /tmp/mispr-record-test.txt.
if CommandLine.arguments.contains("--record-test") {
    let recorder = MeetingRecorder()
    var report = "mic permission: \(AVCaptureDevice.authorizationStatus(for: .audio).rawValue) (3 = authorized)\n"
    report += "screen capture preflight: \(CGPreflightScreenCaptureAccess())\n"
    report += "bundle: \(Bundle.main.bundleIdentifier ?? "-") at \(Bundle.main.bundlePath)\n"
    var peak: Float = 0
    recorder.onLevel = { peak = max(peak, $0) }
    recorder.onChunk = { stream, start, samples in report += "chunk \(stream) at \(start)s: \(samples.count / 16_000)s\n" }
    recorder.onError = { report += "error: \($0)\n" }
    Task {
        do {
            if let warning = try await recorder.start(systemAudio: true, saveTo: nil) { report += "warning: \(warning)\n" }
        } catch { report += "start failed: \(error)\n" }
    }
    RunLoop.main.run(until: Date().addingTimeInterval(8))
    recorder.stop()
    report += "peak level: \(peak)\n"
    try? report.write(toFile: "/tmp/mispr-record-test.txt", atomically: true, encoding: .utf8)
    exit(0)
}

// A plain AppKit entry point (rather than SwiftUI's App) so the window, Dock behavior,
// menus, and engine lifetime are all explicit.
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
