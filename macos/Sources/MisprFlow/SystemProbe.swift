import AppKit
import ApplicationServices
import CoreAudio
import Darwin
import MisprCore

/// Gathers what MeetingDetector needs from the live system. Nothing is recorded: it reads app
/// and process names, window titles (Accessibility, already granted), and whether any app
/// is using the default microphone.
enum SystemProbe {
    /// Apps whose window titles say whether a call is on.
    static let titleApps: Set<String> = MeetingDetector.browsers.union(["us.zoom.xos", "com.tinyspeck.slackmacgap"])

    static func snapshot() -> SystemSnapshot {
        let apps = NSWorkspace.shared.runningApplications
        var titles: [SystemSnapshot.WindowTitle] = []
        for app in apps {
            guard let bundle = app.bundleIdentifier, titleApps.contains(bundle) else { continue }
            for title in windowTitles(pid: app.processIdentifier) {
                titles.append(.init(bundle, title))
            }
        }
        return SystemSnapshot(runningBundleIDs: Set(apps.compactMap(\.bundleIdentifier)),
                              processNames: processNames(), windowTitles: titles, micInUse: micInUse())
    }

    static func windowTitles(pid: pid_t) -> [String] {
        let app = AXUIElementCreateApplication(pid)
        AXUIElementSetMessagingTimeout(app, 0.25)
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &value) == .success,
              let windows = value as? [AXUIElement] else { return [] }
        return windows.compactMap { window in
            var title: CFTypeRef?
            guard AXUIElementCopyAttributeValue(window, kAXTitleAttribute as CFString, &title) == .success else { return nil }
            return title as? String
        }
    }

    static func processNames() -> Set<String> {
        let count = proc_listallpids(nil, 0)
        guard count > 0 else { return [] }
        var pids = [pid_t](repeating: 0, count: Int(count) * 2)
        let filled = proc_listallpids(&pids, Int32(pids.count * MemoryLayout<pid_t>.size))
        var names: Set<String> = []
        var buffer = [CChar](repeating: 0, count: 256)
        for pid in pids.prefix(Int(max(0, filled))) where pid > 0 {
            if proc_name(pid, &buffer, UInt32(buffer.count)) > 0 { names.insert(String(cString: buffer)) }
        }
        return names
    }

    /// True when any app has the default input device running (a call, a recording...).
    static func micInUse() -> Bool {
        var device = AudioDeviceID(0)
        var size = UInt32(MemoryLayout<AudioDeviceID>.size)
        var address = AudioObjectPropertyAddress(mSelector: kAudioHardwarePropertyDefaultInputDevice,
                                                 mScope: kAudioObjectPropertyScopeGlobal,
                                                 mElement: kAudioObjectPropertyElementMain)
        guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &address, 0, nil, &size, &device) == noErr,
              device != 0 else { return false }
        var running = UInt32(0)
        size = UInt32(MemoryLayout<UInt32>.size)
        address.mSelector = kAudioDevicePropertyDeviceIsRunningSomewhere
        guard AudioObjectGetPropertyData(device, &address, 0, nil, &size, &running) == noErr else { return false }
        return running != 0
    }
}

/// Split screen: the call's window fills the left of the screen and the note sits on the right.
enum WindowArranger {
    /// Returns false when the call's window can't be found or moved.
    @discardableResult
    static func split(meeting: SystemSnapshot.WindowTitle, note: NSWindow, noteWidth: CGFloat = 470, gap: CGFloat = 8) -> Bool {
        guard let app = NSWorkspace.shared.runningApplications.first(where: { $0.bundleIdentifier == meeting.bundleID }),
              let window = axWindow(pid: app.processIdentifier, title: meeting.title) else { return false }
        let screen = note.screen ?? NSScreen.main ?? NSScreen.screens[0]
        let visible = screen.visibleFrame
        let noteFrame = NSRect(x: visible.maxX - noteWidth - gap, y: visible.minY + gap,
                               width: noteWidth, height: visible.height - 2 * gap)
        note.setFrame(noteFrame, display: true, animate: true)
        // Accessibility uses top-left coordinates measured from the primary screen's top.
        let primaryTop = NSScreen.screens[0].frame.maxY
        var origin = CGPoint(x: visible.minX + gap, y: primaryTop - visible.maxY + gap)
        var size = CGSize(width: noteFrame.minX - visible.minX - 2 * gap, height: visible.height - 2 * gap)
        guard let position = AXValueCreate(.cgPoint, &origin), let dimensions = AXValueCreate(.cgSize, &size) else { return false }
        AXUIElementSetAttributeValue(window, kAXPositionAttribute as CFString, position)
        AXUIElementSetAttributeValue(window, kAXSizeAttribute as CFString, dimensions)
        AXUIElementPerformAction(window, kAXRaiseAction as CFString)
        app.activate()
        note.orderFront(nil)
        return true
    }

    /// The window with this title (or the app's main/first window when the title is empty).
    static func axWindow(pid: pid_t, title: String) -> AXUIElement? {
        let app = AXUIElementCreateApplication(pid)
        AXUIElementSetMessagingTimeout(app, 0.5)
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &value) == .success,
              let windows = value as? [AXUIElement], !windows.isEmpty else { return nil }
        guard !title.isEmpty else { return windows.first }
        return windows.first { window in
            var t: CFTypeRef?
            AXUIElementCopyAttributeValue(window, kAXTitleAttribute as CFString, &t)
            return (t as? String) == title
        } ?? windows.first
    }
}
