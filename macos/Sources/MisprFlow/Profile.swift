import AppKit
import MisprCore
import SwiftUI

/// Your profile and look (Settings > Profile), kept in this app's preferences on this Mac.
final class Profile: ObservableObject {
    enum Appearance: String, CaseIterable, Identifiable {
        case system = "System", light = "Light", dark = "Dark"
        var id: String { rawValue }
    }

    static let avatarColors: [UInt32] = [0x1F5C4A, 0x1E6FB8, 0x6B4FC4, 0xD4572A, 0xC2185B, 0x34477F, 0x8D6E63, 0x2B2B2B]

    @Published var name: String { didSet { save("name", name) } }
    @Published var nickname: String { didSet { save("nickname", nickname) } }
    @Published var role: String { didSet { save("role", role) } }
    @Published var avatarColor: UInt32 { didSet { defaults.set(Int(avatarColor), forKey: key("avatarColor")) } }
    @Published var themeID: String {
        didSet {
            save("theme", themeID)
            Palette.current = Palette.named(themeID)
        }
    }
    @Published var appearance: Appearance {
        didSet {
            save("appearance", appearance.rawValue)
            apply()
        }
    }
    @Published private(set) var photo: NSImage?

    private let defaults: UserDefaults
    private let photoURL: URL

    /// The first-run tour was finished or skipped.
    var tutorialDone: Bool {
        get { defaults.bool(forKey: "profile.tutorialDone") }
        set { defaults.set(newValue, forKey: "profile.tutorialDone") }
    }

    init(defaults: UserDefaults = .standard, photoURL customPhoto: URL? = nil) {
        self.defaults = defaults
        self.photoURL = customPhoto ?? FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Mispr_Flow/profile-photo.png")
        name = defaults.string(forKey: "profile.name") ?? ""
        nickname = defaults.string(forKey: "profile.nickname") ?? ""
        role = defaults.string(forKey: "profile.role") ?? ""
        let color = defaults.integer(forKey: "profile.avatarColor")
        avatarColor = color == 0 ? Self.avatarColors[0] : UInt32(color)
        themeID = defaults.string(forKey: "profile.theme") ?? Palette.classic.id
        appearance = Appearance(rawValue: defaults.string(forKey: "profile.appearance") ?? "") ?? .system
        photo = NSImage(contentsOf: photoURL)
        Palette.current = Palette.named(themeID)
    }

    var info: ProfileInfo { ProfileInfo(name: name, nickname: nickname, role: role) }

    /// Changes when anything that affects colors changes; used to redraw every view.
    var lookID: String { "\(themeID)-\(appearance.rawValue)" }

    func apply() {
        switch appearance {
        case .system: NSApp.appearance = nil
        case .light: NSApp.appearance = NSAppearance(named: .aqua)
        case .dark: NSApp.appearance = NSAppearance(named: .darkAqua)
        }
    }

    func choosePhoto() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.image]
        panel.message = "Choose a profile picture"
        guard panel.runModal() == .OK, let url = panel.url, let image = NSImage(contentsOf: url) else { return }
        setPhoto(image)
    }

    /// Save a picture (cropped square, 256 px) as the profile photo.
    func setPhoto(_ image: NSImage) {
        let square = Self.squareThumbnail(image, side: 256)
        guard let tiff = square.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
              let png = rep.representation(using: .png, properties: [:]) else { return }
        try? FileManager.default.createDirectory(at: photoURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? png.write(to: photoURL, options: .atomic)
        photo = square
    }

    func removePhoto() {
        try? FileManager.default.removeItem(at: photoURL)
        photo = nil
    }

    private func key(_ name: String) -> String { "profile.\(name)" }

    private func save(_ name: String, _ value: String) {
        defaults.set(value, forKey: key(name))
    }

    /// Center-crop to a square and scale down.
    static func squareThumbnail(_ image: NSImage, side: CGFloat) -> NSImage {
        let size = image.size
        let crop = min(size.width, size.height)
        let source = NSRect(x: (size.width - crop) / 2, y: (size.height - crop) / 2, width: crop, height: crop)
        let result = NSImage(size: NSSize(width: side, height: side))
        result.lockFocus()
        NSGraphicsContext.current?.imageInterpolation = .high
        image.draw(in: NSRect(x: 0, y: 0, width: side, height: side), from: source, operation: .copy, fraction: 1)
        result.unlockFocus()
        return result
    }
}

/// Your photo, or your initials on your color.
struct AvatarView: View {
    @EnvironmentObject var model: AppModel
    var size: CGFloat = 28

    var body: some View {
        Group {
            if let photo = model.profile.photo {
                Image(nsImage: photo).resizable().interpolation(.high)
            } else {
                ZStack {
                    Circle().fill(Color(nsColor: Theme.nsColor(hex: model.profile.avatarColor)))
                    Text(model.profile.info.initials(account: NSFullUserName()))
                        .font(.system(size: size * 0.4, weight: .semibold)).foregroundStyle(.white)
                }
            }
        }
        .frame(width: size, height: size)
        .clipShape(Circle())
    }
}
