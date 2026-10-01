import Foundation

/// Where a meeting is happening, which decides what gets recorded: calls need the other
/// people's audio (system audio); an in-person meeting only needs the microphone.
public enum MeetingSource: String, CaseIterable, Identifiable, Codable {
    case zoom = "Zoom"
    case googleMeet = "Google Meet"
    case teams = "Microsoft Teams"
    case webex = "Webex"
    case facetime = "FaceTime"
    case slack = "Slack huddle"
    case discord = "Discord"
    case inPerson = "In person"
    case otherCall = "Other call"

    public var id: String { rawValue }

    public var symbol: String {
        switch self {
        case .zoom, .webex: "video"
        case .googleMeet: "video.badge.waveform"
        case .teams: "person.3"
        case .facetime: "video.circle"
        case .slack, .discord: "headphones"
        case .inPerson: "person.2.wave.2"
        case .otherCall: "phone"
        }
    }

    /// A call captures what the others say through system audio; a room just uses the mic.
    public var needsSystemAudio: Bool { self != .inPerson }
}

/// What the Mac looks like right now, for detection. Gathered by the app (running apps,
/// processes, window titles through Accessibility, whether any app is using the mic).
public struct SystemSnapshot: Equatable {
    public var runningBundleIDs: Set<String>
    public var processNames: Set<String>
    public var windowTitles: [WindowTitle]
    public var micInUse: Bool

    public struct WindowTitle: Equatable, Hashable {
        public var bundleID: String
        public var title: String

        public init(_ bundleID: String, _ title: String) {
            self.bundleID = bundleID
            self.title = title
        }
    }

    public init(runningBundleIDs: Set<String> = [], processNames: Set<String> = [],
                windowTitles: [WindowTitle] = [], micInUse: Bool = false) {
        self.runningBundleIDs = runningBundleIDs
        self.processNames = processNames
        self.windowTitles = windowTitles
        self.micInUse = micInUse
    }
}

public struct MeetingDetection: Equatable {
    public var source: MeetingSource
    /// A meeting name found along the way (e.g. from the Meet tab title).
    public var title: String?
    /// Why we think so, shown on hover ("Zoom's meeting process is running").
    public var evidence: String
    /// The call's window, when known (for Split screen).
    public var window: SystemSnapshot.WindowTitle?

    public init(source: MeetingSource, title: String?, evidence: String, window: SystemSnapshot.WindowTitle? = nil) {
        self.source = source
        self.title = title
        self.evidence = evidence
        self.window = window
    }
}

public enum MeetingDetector {
    public static let browsers: Set<String> = [
        "com.google.Chrome", "com.google.Chrome.canary", "com.apple.Safari", "com.brave.Browser",
        "com.microsoft.edgemac", "company.thebrowser.Browser", "company.thebrowser.dia", "org.mozilla.firefox",
        "com.operasoftware.Opera", "com.vivaldi.Vivaldi", "org.chromium.Chromium",
    ]
    /// Zoom starts its meeting host process only while you're in a meeting.
    static let zoomMeetingProcesses: Set<String> = ["CptHost", "caphost", "aomhost"]

    public static func detect(_ s: SystemSnapshot) -> MeetingDetection {
        // 1. Zoom app: its meeting process exists only during a call.
        let zoomWindow = s.windowTitles.first { $0.bundleID == "us.zoom.xos" && ($0.title == "Zoom Meeting" || $0.title.hasPrefix("Zoom Webinar")) }
        if !s.processNames.isDisjoint(with: zoomMeetingProcesses) || zoomWindow != nil {
            return MeetingDetection(source: .zoom, title: nil, evidence: "Zoom's meeting window is open",
                                    window: zoomWindow ?? .init("us.zoom.xos", "Zoom Meeting"))
        }
        // 2. Calls in a browser tab (window titles show the active tab).
        for w in s.windowTitles where browsers.contains(w.bundleID) {
            if let title = meetTitle(w.title) {
                return MeetingDetection(source: .googleMeet, title: title, evidence: "A Google Meet tab is open", window: w)
            }
        }
        if s.micInUse {
            for w in s.windowTitles where browsers.contains(w.bundleID) {
                let t = w.title.lowercased()
                if t.contains("microsoft teams") { return MeetingDetection(source: .teams, title: nil, evidence: "Teams is open in the browser and the mic is in use", window: w) }
                if t.contains("zoom") { return MeetingDetection(source: .zoom, title: nil, evidence: "Zoom is open in the browser and the mic is in use", window: w) }
                if t.contains("webex") { return MeetingDetection(source: .webex, title: nil, evidence: "Webex is open in the browser and the mic is in use", window: w) }
            }
        }
        // 3. Call apps that don't announce calls: running + the mic busy.
        let apps: [(Set<String>, MeetingSource)] = [
            (["com.microsoft.teams2", "com.microsoft.teams"], .teams),
            (["com.cisco.webexmeetingsapp", "Cisco-Systems.Spark"], .webex),
            (["com.apple.FaceTime"], .facetime),
            (["com.hnc.Discord"], .discord),
        ]
        if let huddle = s.windowTitles.first(where: { $0.bundleID == "com.tinyspeck.slackmacgap" && $0.title.localizedCaseInsensitiveContains("huddle") }) {
            return MeetingDetection(source: .slack, title: nil, evidence: "A Slack huddle window is open", window: huddle)
        }
        if s.micInUse {
            for (ids, source) in apps where !s.runningBundleIDs.isDisjoint(with: ids) {
                let bundle = ids.first { s.runningBundleIDs.contains($0) }!
                return MeetingDetection(source: source, title: nil, evidence: "\(source.rawValue) is running and the mic is in use",
                                        window: .init(bundle, ""))  // "" = the app's front window
            }
            if s.runningBundleIDs.contains("us.zoom.xos") {
                return MeetingDetection(source: .zoom, title: nil, evidence: "Zoom is running and the mic is in use")
            }
        }
        // 4. Something has the mic but we can't tell what (e.g. a Meet call in a background tab,
        //    whose title isn't visible): treat it as a call so the others' audio is captured.
        if s.micInUse {
            return MeetingDetection(source: .otherCall, title: nil, evidence: "Another app is using the mic")
        }
        // 5. No call anywhere: a meeting in the room.
        return MeetingDetection(source: .inPerson, title: nil, evidence: "No call app is in a meeting")
    }

    /// "Meet – Weekly sync" -> "Weekly sync"; meeting codes ("abc-defg-hij") aren't names.
    static func meetTitle(_ windowTitle: String) -> String? {
        let prefixes = ["Meet – ", "Meet - ", "Meet — "]
        guard let prefix = prefixes.first(where: { windowTitle.hasPrefix($0) }) else {
            return windowTitle.contains("meet.google.com") ? "" : nil
        }
        var name = String(windowTitle.dropFirst(prefix.count))
        // Browsers append " - Google Chrome", " — Profile" etc.
        for suffix in [" - Google Chrome", " – Google Chrome", " - Brave", " — Safari", " - Microsoft Edge", " - Arc"] {
            if let range = name.range(of: suffix) { name = String(name[..<range.lowerBound]) }
        }
        name = name.trimmingCharacters(in: .whitespaces)
        let isCode = name.range(of: #"^[a-z]{3}-[a-z]{4}-[a-z]{3}$"#, options: .regularExpression) != nil
        return isCode ? "" : name
    }
}
