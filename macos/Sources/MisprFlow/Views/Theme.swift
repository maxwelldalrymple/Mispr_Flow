import AppKit
import SwiftUI

/// The app's colors. Each one is resolved at draw time from the chosen palette (Profile >
/// Theme) and the light/dark appearance, so changing either recolors everything.
enum Theme {
    static let sidebar = adaptive(\.sidebar)
    static let content = adaptive(\.content)
    static let card = adaptive(\.card)
    static let cardStroke = adaptive(\.cardStroke)
    static let selection = adaptive(\.selection)
    static let text = adaptive(\.text)
    static let secondary = adaptive(\.secondary)
    static let accent = adaptive(\.accent)
    static let accentSoft = adaptive(\.accentSoft)
    static let key = Color(nsColor: NSColor(srgbRed: 0xF6 / 255, green: 0xA3 / 255, blue: 0x3B / 255, alpha: 1))  // the fn key chip

    static func display(_ size: CGFloat) -> Font { .system(size: size, weight: .regular, design: .serif) }

    private static func adaptive(_ role: KeyPath<Palette.Colors, UInt32>) -> Color {
        Color(nsColor: NSColor(name: nil) { appearance in
            let dark = appearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
            let colors = dark ? Palette.current.dark : Palette.current.light
            return nsColor(hex: colors[keyPath: role])
        })
    }

    static func nsColor(hex: UInt32) -> NSColor {
        NSColor(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255,
                blue: CGFloat(hex & 0xFF) / 255, alpha: 1)
    }
}

/// A color theme: a light and a dark set of the same roles.
struct Palette: Identifiable, Equatable {
    struct Colors: Equatable {
        var sidebar, content, card, cardStroke, selection, text, secondary, accent, accentSoft: UInt32
    }

    let id: String
    let name: String
    let light: Colors
    let dark: Colors

    /// The palette everything draws with; set from Profile.
    static var current = classic

    static let classic = Palette(id: "classic", name: "Classic",
        light: Colors(sidebar: 0xF3F1EC, content: 0xFBFAF7, card: 0xF3F1EC, cardStroke: 0xE7E4DD, selection: 0xE6E3DC,
                      text: 0x1C1B19, secondary: 0x6E6B65, accent: 0x1F5C4A, accentSoft: 0xCFE3DA),
        dark: Colors(sidebar: 0x1B1B1D, content: 0x232325, card: 0x2C2C2F, cardStroke: 0x3A3A3D, selection: 0x333336,
                     text: 0xF2F2F2, secondary: 0xA0A0A5, accent: 0x4FB38F, accentSoft: 0x24453A))
    static let ocean = Palette(id: "ocean", name: "Ocean",
        light: Colors(sidebar: 0xE6EFF7, content: 0xF7FAFD, card: 0xE8F0F7, cardStroke: 0xD2DFEB, selection: 0xD3E2F0,
                      text: 0x10202F, secondary: 0x5A6B7C, accent: 0x1E6FB8, accentSoft: 0xCFE2F4),
        dark: Colors(sidebar: 0x0D1824, content: 0x132130, card: 0x1A2B3C, cardStroke: 0x26394D, selection: 0x21354A,
                     text: 0xEAF2FA, secondary: 0x8FA4B8, accent: 0x5AA9F0, accentSoft: 0x1B3A58))
    static let forest = Palette(id: "forest", name: "Forest",
        light: Colors(sidebar: 0xE9EFE4, content: 0xF8FAF5, card: 0xE9EFE3, cardStroke: 0xD5DFCD, selection: 0xD8E3D0,
                      text: 0x16200F, secondary: 0x5F6B57, accent: 0x2F6B3A, accentSoft: 0xD2E6D1),
        dark: Colors(sidebar: 0x111913, content: 0x17211A, card: 0x1E2B21, cardStroke: 0x2A3A2C, selection: 0x25362A,
                     text: 0xEAF3EA, secondary: 0x93A895, accent: 0x6BC07A, accentSoft: 0x203D27))
    static let sunset = Palette(id: "sunset", name: "Sunset",
        light: Colors(sidebar: 0xF8ECE4, content: 0xFFF9F5, card: 0xF7E9DF, cardStroke: 0xECD6C7, selection: 0xF1DCCC,
                      text: 0x2A1810, secondary: 0x7C6457, accent: 0xD4572A, accentSoft: 0xF6D9C9),
        dark: Colors(sidebar: 0x1E1411, content: 0x271A16, card: 0x33231D, cardStroke: 0x46302A, selection: 0x3D2A22,
                     text: 0xFBEDE6, secondary: 0xB89C8F, accent: 0xFF8A4C, accentSoft: 0x4A2A1C))
    static let lavender = Palette(id: "lavender", name: "Lavender",
        light: Colors(sidebar: 0xEEEAF7, content: 0xFBF9FE, card: 0xEDE8F7, cardStroke: 0xDCD3EE, selection: 0xE1D9F2,
                      text: 0x1D1630, secondary: 0x6C6380, accent: 0x6B4FC4, accentSoft: 0xE0D7F7),
        dark: Colors(sidebar: 0x16121E, content: 0x1D1827, card: 0x262032, cardStroke: 0x352C45, selection: 0x2F263E,
                     text: 0xF1ECFB, secondary: 0xA79DBC, accent: 0xA68BFF, accentSoft: 0x342A55))
    static let midnight = Palette(id: "midnight", name: "Midnight",
        light: Colors(sidebar: 0xE8EAF0, content: 0xF7F8FB, card: 0xE7EAF1, cardStroke: 0xD4D9E3, selection: 0xD9DEE9,
                      text: 0x111526, secondary: 0x5D6378, accent: 0x34477F, accentSoft: 0xD6DDF0),
        dark: Colors(sidebar: 0x090C14, content: 0x0F131D, card: 0x161B29, cardStroke: 0x222A3D, selection: 0x1D2436,
                     text: 0xE8ECF7, secondary: 0x8D95AD, accent: 0x7C9CFF, accentSoft: 0x1E2A4E))

    static let all = [classic, ocean, forest, sunset, lavender, midnight]

    static func named(_ id: String) -> Palette { all.first { $0.id == id } ?? classic }
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

/// The logo (a ring around five waveform bars) drawn as shapes, so it's sharp at any size;
/// the 1024 px PNG with its soft glow went blurry when shrunk to sidebar size.
struct Logo: View {
    var size: CGFloat = 22
    static let bars: [CGFloat] = [0.42, 0.62, 1.0, 0.62, 0.42]  // heights, as in icon.png

    var body: some View {
        ZStack {
            Circle().fill(Color.black)
            Circle().strokeBorder(Color.white, lineWidth: max(1, size * 0.06)).padding(size * 0.04)
            HStack(spacing: size * 0.075) {
                ForEach(Array(Self.bars.enumerated()), id: \.offset) { _, height in
                    Capsule().fill(Color.white).frame(width: size * 0.075, height: size * 0.5 * height)
                }
            }
        }
        .frame(width: size, height: size)
    }
}
