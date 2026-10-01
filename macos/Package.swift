// swift-tools-version: 5.10
// The Mispr Flow app: a SwiftUI window around the Python dictation engine (../mispr).
// Build the .app with ../tools/build_app.sh; run the logic tests with `swift test`.
import PackageDescription

let package = Package(
    name: "MisprFlow",
    platforms: [.macOS(.v14)],
    targets: [
        // Everything testable without a UI: engine process, messages, recordings, stats, settings.
        .target(name: "MisprCore"),
        .executableTarget(name: "MisprFlow", dependencies: ["MisprCore"]),
        .testTarget(name: "MisprCoreTests", dependencies: ["MisprCore"]),
    ]
)
