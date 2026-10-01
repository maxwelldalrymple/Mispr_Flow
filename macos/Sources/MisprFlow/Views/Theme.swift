import AppKit
import SwiftUI

/// Warm neutrals in light mode (like Wispr Flow), true darks in dark mode.
enum Theme {
    static let sidebar = adaptive(light: 0xF3F1EC, dark: 0x1B1B1D)
    static let content = adaptive(light: 0xFBFAF7, dark: 0x232325)
    static let card = adaptive(light: 0xF3F1EC, dark: 0x2C2C2F)
    static let cardStroke = adaptive(light: 0xE7E4DD, dark: 0x3A3A3D)
    static let selection = adaptive(light: 0xE6E3DC, dark: 0x333336)
    static let text = adaptive(light: 0x1C1B19, dark: 0xF2F2F2)
    static let secondary = adaptive(light: 0x6E6B65, dark: 0xA0A0A5)
    static let accent = adaptive(light: 0x1F5C4A, dark: 0x4FB38F)  // insights green
    static let accentSoft = adaptive(light: 0xCFE3DA, dark: 0x24453A)
    static let key = adaptive(light: 0xF6A33B, dark: 0xF6A33B)  // the fn key chip

    static func display(_ size: CGFloat) -> Font { .system(size: size, weight: .regular, design: .serif) }

    private static func adaptive(light: UInt32, dark: UInt32) -> Color {
        Color(nsColor: NSColor(name: nil) { appearance in
            let hex = appearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua ? dark : light
            return NSColor(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
                           blue: CGFloat(hex & 0xFF) / 255, alpha: 1)
        })
    }
}

/// A rounded panel used for stats and lists.
struct Card<Content: View>: View {
    var padding: CGFloat = 18
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: 14).fill(Theme.card))
    }
}

/// The logo: the app icon when running as the .app, a waveform symbol otherwise.
struct Logo: View {
    var size: CGFloat = 22

    var body: some View {
        if let image = NSImage(named: "icon") ?? Bundle.main.url(forResource: "icon", withExtension: "png").flatMap(NSImage.init(contentsOf:)) {
            Image(nsImage: image).resizable().interpolation(.high).frame(width: size, height: size)
                .clipShape(RoundedRectangle(cornerRadius: size * 0.22))
        } else {
            Image(systemName: "waveform.circle.fill").resizable().frame(width: size, height: size)
        }
    }
}
