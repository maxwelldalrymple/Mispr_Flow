import AppKit
import MisprCore

// Development: `MisprFlow --detect` prints what meeting detection sees right now, then exits.
if CommandLine.arguments.contains("--detect") {
    let snapshot = SystemProbe.snapshot()
    let found = MeetingDetector.detect(snapshot)
    print("source: \(found.source.rawValue)  title: \(found.title ?? "-")  why: \(found.evidence)")
    print("mic in use: \(snapshot.micInUse)")
    for w in snapshot.windowTitles { print("window: \(w.bundleID): \(w.title)") }
    exit(0)
}

// A plain AppKit entry point (rather than SwiftUI's App) so the window, Dock behavior,
// menus, and engine lifetime are all explicit.
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
