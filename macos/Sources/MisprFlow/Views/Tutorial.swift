import SwiftUI

/// The places the tour outlines. Views mark themselves with `.tourSpot(_:)`.
enum TourSpot: String {
    case fnKey, history, topBar, commands, page, newNote, settings
}

/// One step of the first-run tour: which page to show, what to outline, and what to say.
struct TourStep: Equatable {
    let page: Page
    let spot: TourSpot?
    let title: String
    let body: String

    static let all: [TourStep] = [
        TourStep(page: .home, spot: .fnKey, title: "Dictate anywhere",
                 body: "Hold fn in any app, speak, and let go: clean text appears where you're typing. Double-tap fn for hands-free."),
        TourStep(page: .home, spot: .history, title: "Your history",
                 body: "Every dictation, and every voice command, is here. Search, play, or copy any of them."),
        TourStep(page: .home, spot: .topBar, title: "Auto-Enter and Incognito",
                 body: "Auto-Enter presses Return for you so messages send themselves. Incognito saves nothing at all."),
        TourStep(page: .commands, spot: .page, title: "Control your Mac by voice",
                 body: "Hold your switch key and say it: “click Sign in”, “left half”, “YouTube tab”, “press enter”. Every command is here, searchable."),
        TourStep(page: .insights, spot: .page, title: "Insights",
                 body: "Your pace, streaks, time saved and voice profile, from your own dictations."),
        TourStep(page: .notetaker, spot: .newNote, title: "Meeting notes",
                 body: "Press ⌥M on a call: live transcript, who said what, and a summary. Nothing is saved until you press Save."),
        TourStep(page: .prompts, spot: .page, title: "Prompts",
                 body: "Change how your words are cleaned up, and try it right here."),
        TourStep(page: .home, spot: .settings, title: "Make it yours",
                 body: "Profile, themes, your dictation and switch keys, nicknames and sounds. Replay this tour from Help → Show Tutorial."),
    ]
}

struct TourAnchors: PreferenceKey {
    static let defaultValue: [TourSpot: Anchor<CGRect>] = [:]
    static func reduce(value: inout [TourSpot: Anchor<CGRect>], nextValue: () -> [TourSpot: Anchor<CGRect>]) {
        value.merge(nextValue()) { $1 }
    }
}

extension View {
    /// Lets the tour find and outline this view.
    func tourSpot(_ spot: TourSpot) -> some View {
        // Merge with the spots inside this view (anchorPreference would replace them).
        transformAnchorPreference(key: TourAnchors.self, value: .bounds) { $0[spot] = $1 }
    }
}

/// Dims the window except the outlined spot, with a card: "3 of 8", Back, Next, Skip tour.
struct TourOverlay: View {
    @EnvironmentObject var model: AppModel
    let anchors: [TourSpot: Anchor<CGRect>]

    var body: some View {
        if let index = model.tourStep, TourStep.all.indices.contains(index) {
            let step = TourStep.all[index]
            GeometryReader { geo in
                let hole = step.spot.flatMap { anchors[$0] }.map { geo[$0].insetBy(dx: -8, dy: -8) }
                ZStack(alignment: .topLeading) {
                    Path { p in
                        p.addRect(CGRect(origin: .zero, size: geo.size))
                        if let hole { p.addRoundedRect(in: hole, cornerSize: CGSize(width: 12, height: 12)) }
                    }
                    .fill(Color.black.opacity(0.6), style: FillStyle(eoFill: true))
                    .onTapGesture {}  // the rest of the window waits while the tour is up
                    if let hole {
                        RoundedRectangle(cornerRadius: 12).stroke(Theme.accent, lineWidth: 2.5)
                            .frame(width: hole.width, height: hole.height).offset(x: hole.minX, y: hole.minY)
                            .allowsHitTesting(false)
                    }
                    card(step, index)
                        .frame(width: 320)
                        .offset(Self.cardOrigin(near: hole, in: geo.size, card: CGSize(width: 320, height: 170)))
                }
            }
            .transition(.opacity)
            .animation(.easeInOut(duration: 0.2), value: index)
        }
    }

    /// Below the outlined spot if it fits, otherwise above, otherwise beside it; centred with nothing to outline.
    static func cardOrigin(near hole: CGRect?, in size: CGSize, card: CGSize) -> CGSize {
        guard let hole else { return CGSize(width: (size.width - card.width) / 2, height: (size.height - card.height) / 2) }
        let x = min(max(16, hole.midX - card.width / 2), size.width - card.width - 16)
        if hole.maxY + 14 + card.height <= size.height { return CGSize(width: x, height: hole.maxY + 14) }
        if hole.minY - 14 - card.height >= 0 { return CGSize(width: x, height: hole.minY - 14 - card.height) }
        let side = hole.maxX + 14 + card.width <= size.width ? hole.maxX + 14 : max(16, hole.minX - 14 - card.width)
        return CGSize(width: side, height: max(16, min(hole.midY - card.height / 2, size.height - card.height - 16)))
    }

    private func card(_ step: TourStep, _ index: Int) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("\(index + 1) of \(TourStep.all.count)").font(.system(size: 11, weight: .semibold)).foregroundStyle(Theme.accent)
            Text(step.title).font(.system(size: 16, weight: .semibold))
            Text(step.body).font(.system(size: 13)).foregroundStyle(Theme.secondary).fixedSize(horizontal: false, vertical: true)
            HStack {
                Button("Skip tour") { model.endTour() }.buttonStyle(.plain).font(.system(size: 12)).foregroundStyle(Theme.secondary)
                Spacer()
                if index > 0 { Button("Back") { model.moveTour(-1) }.buttonStyle(OutlineButton()) }
                Button { model.moveTour(1) } label: {
                    Text(index == TourStep.all.count - 1 ? "Done" : "Next").font(.system(size: 13, weight: .semibold)).foregroundStyle(.white)
                        .padding(.horizontal, 16).frame(height: 30).background(Capsule().fill(Theme.accent))
                }
                .buttonStyle(PressableButton()).keyboardShortcut(.defaultAction)
            }
            .padding(.top, 4)
        }
        .padding(16)
        .background(RoundedRectangle(cornerRadius: 14).fill(Theme.content))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Theme.cardStroke))
        .shadow(color: .black.opacity(0.3), radius: 18, y: 8)
    }
}
