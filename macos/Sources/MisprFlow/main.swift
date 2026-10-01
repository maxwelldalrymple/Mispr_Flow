import AppKit
import AVFoundation
import MisprCore

// Development: `MisprFlow --detect` prints what meeting detection sees right now, then exits.
if CommandLine.arguments.contains("--detect") {
    print(DevTools.detectReport(SystemProbe.snapshot(), mic: AVCaptureDevice.authorizationStatus(for: .audio),
                                screenAllowed: CGPreflightScreenCaptureAccess()))
    exit(0)
}

// Development: `MisprFlow --segment file.wav` prints where the chunker would cut a recording.
if let i = CommandLine.arguments.firstIndex(of: "--segment"), i + 1 < CommandLine.arguments.count,
   let data = FileManager.default.contents(atPath: CommandLine.arguments[i + 1]) {
    print(DevTools.segmentReport(wav: data))
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
