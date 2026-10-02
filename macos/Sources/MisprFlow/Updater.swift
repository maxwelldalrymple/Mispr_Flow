import AppKit
import MisprCore

/// Automatic updates from GitHub Releases: about 5 times a day (and a minute after launch) it
/// asks GitHub for the latest release. A newer one is downloaded, its signature checked
/// (Update.verify), and the new app staged next to this one. When you're not dictating or in a
/// meeting, the app quits, the new copy takes its place, and it opens again. Nothing about you is
/// sent: it's one plain request for the release list.
///
/// Only the DMG build updates itself (Info.plist MisprBundled); a development build never does.
final class Updater: ObservableObject {
    enum Status: Equatable {
        case idle
        case checking
        case upToDate(String)
        case downloading(String)
        case waiting(String)  // downloaded and checked; installs when you're not busy
        case installing(String)
        case failed(String)
    }

    @Published private(set) var status: Status = .idle
    /// Is "Automatic updates" on (settings.json auto_update)?
    var enabled: () -> Bool = { true }
    /// Dictating or recording a meeting: an update waits.
    var busy: () -> Bool = { false }

    let current: String
    private let bundleURL: URL
    private let canUpdate: Bool
    private var timer: Timer?
    private var idleTimer: Timer?
    private var staged: (app: URL, version: String)?
    private var working = false

    init(bundle: Bundle = .main) {
        current = bundle.infoDictionary?["CFBundleShortVersionString"] as? String ?? "0"
        bundleURL = bundle.bundleURL
        canUpdate = bundle.infoDictionary?["MisprBundled"] as? Bool == true
    }

    /// Why this copy can't replace itself, or nil if it can.
    var blocker: String? {
        if !canUpdate { return "Development build: updates come from git" }
        if bundleURL.path.contains("/AppTranslocation/") || bundleURL.path.hasPrefix("/Volumes/") {
            return "Move Mispr Flow to Applications to get updates"
        }
        if !FileManager.default.isWritableFile(atPath: bundleURL.deletingLastPathComponent().path) {
            return "Can't write to \(bundleURL.deletingLastPathComponent().path): update by hand from GitHub"
        }
        return nil
    }

    @MainActor
    func start() {
        guard canUpdate else { return }
        Timer.scheduledTimer(withTimeInterval: Update.firstCheckAfter, repeats: false) { [weak self] _ in
            Task { @MainActor in await self?.check() }
        }
        timer = Timer.scheduledTimer(withTimeInterval: Update.checkEvery, repeats: true) { [weak self] _ in
            Task { @MainActor in await self?.check() }
        }
    }

    /// Look for a newer release; download, verify and stage it. `manual` (Check now) runs even
    /// with automatic updates off.
    @MainActor
    func check(manual: Bool = false) async {
        guard !working, manual || enabled() else { return }
        if let blocker {
            if manual { status = .failed(blocker) }
            return
        }
        if let staged {
            status = .waiting(staged.version)
            return installWhenIdle()
        }
        working = true
        defer { working = false }
        status = .checking
        do {
            var request = URLRequest(url: Update.latestURL)
            request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
            request.setValue("Mispr-Flow/\(current)", forHTTPHeaderField: "User-Agent")
            let (data, _) = try await URLSession.shared.data(for: request)
            guard let release = Update.parse(data), Update.isNewer(release.version, than: current) else {
                status = .upToDate(current)
                return
            }
            status = .downloading(release.version)
            let app = try await download(release)
            staged = (app, release.version)
            status = .waiting(release.version)
            installWhenIdle()
        } catch {
            status = .failed("Update check failed: \(error.localizedDescription)")
        }
    }

    /// Download the DMG and its signature, check the signature, and copy the new app next to
    /// this one (same disk, so the swap is a rename). Returns the staged app.
    @MainActor
    private func download(_ release: Release) async throws -> URL {
        let folder = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Mispr Flow/Updates", isDirectory: true)
        try? FileManager.default.removeItem(at: folder)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        let (signature, _) = try await URLSession.shared.data(from: release.signature)
        let (temp, _) = try await URLSession.shared.download(from: release.dmg)
        let dmg = folder.appendingPathComponent(release.dmg.lastPathComponent)
        try FileManager.default.moveItem(at: temp, to: dmg)
        guard Update.verify(file: dmg, signature: String(decoding: signature, as: UTF8.self)) else {
            try? FileManager.default.removeItem(at: dmg)
            throw UpdateError("the download's signature doesn't match; not installing it")
        }
        let mount = folder.appendingPathComponent("mount", isDirectory: true)
        try run("/usr/bin/hdiutil", ["attach", "-nobrowse", "-readonly", "-noautoopen", "-mountpoint", mount.path, dmg.path])
        defer { _ = try? run("/usr/bin/hdiutil", ["detach", "-force", mount.path]) }
        let newApp = mount.appendingPathComponent("Mispr Flow.app")
        let info = Bundle(url: newApp)?.infoDictionary ?? [:]
        guard info["CFBundleIdentifier"] as? String == Bundle.main.bundleIdentifier,
              info["CFBundleShortVersionString"] as? String == release.version else {
            throw UpdateError("the download isn't Mispr Flow \(release.version)")
        }
        let staged = bundleURL.deletingLastPathComponent().appendingPathComponent(".Mispr Flow \(release.version).app")
        try? FileManager.default.removeItem(at: staged)
        try run("/usr/bin/ditto", [newApp.path, staged.path])
        try? FileManager.default.removeItem(at: dmg)
        return staged
    }

    /// Install once you've been idle (not dictating, no meeting) for a minute.
    @MainActor
    private func installWhenIdle() {
        idleTimer?.invalidate()
        var quietSince: Date?
        idleTimer = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { [weak self] timer in
            Task { @MainActor in
                guard let self, let staged = self.staged else { return timer.invalidate() }
                if self.busy() { quietSince = nil; return }
                let since = quietSince ?? Date()
                quietSince = since
                if Date().timeIntervalSince(since) >= 60 {
                    timer.invalidate()
                    self.install(staged.app, version: staged.version)
                }
            }
        }
    }

    /// Quit; a small helper waits for this app to exit, puts the new copy in its place, and opens it.
    @MainActor
    private func install(_ app: URL, version: String) {
        status = .installing(version)
        UserDefaults.standard.set(version, forKey: "updatedTo")
        let script = """
        pid="$1"; old="$2"; new="$3"
        while kill -0 "$pid" 2>/dev/null; do sleep 0.2; done
        rm -rf "$old.previous"
        if mv "$old" "$old.previous" && mv "$new" "$old"; then rm -rf "$old.previous"; else mv "$old.previous" "$old"; fi
        open "$old"
        """
        let helper = Process()
        helper.executableURL = URL(fileURLWithPath: "/bin/sh")
        helper.arguments = ["-c", script, "mispr-update", String(ProcessInfo.processInfo.processIdentifier), bundleURL.path, app.path]
        do {
            try helper.run()
            NSApp.terminate(nil)
        } catch {
            status = .failed("Couldn't install: \(error.localizedDescription)")
        }
    }

    /// After an update: the version it updated to (once), so the app can say so.
    static func justUpdated(to current: String) -> Bool {
        guard UserDefaults.standard.string(forKey: "updatedTo") == current else { return false }
        UserDefaults.standard.removeObject(forKey: "updatedTo")
        return true
    }

    @discardableResult
    private func run(_ tool: String, _ arguments: [String]) throws -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: tool)
        process.arguments = arguments
        let out = Pipe()
        process.standardOutput = out
        process.standardError = out
        try process.run()
        process.waitUntilExit()
        let text = String(decoding: out.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
        guard process.terminationStatus == 0 else { throw UpdateError("\(URL(fileURLWithPath: tool).lastPathComponent) failed: \(text)") }
        return text
    }
}

struct UpdateError: LocalizedError {
    let message: String
    init(_ message: String) { self.message = message }
    var errorDescription: String? { message }
}
