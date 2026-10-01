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
