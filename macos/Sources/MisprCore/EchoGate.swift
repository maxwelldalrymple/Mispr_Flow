import Foundation

/// Speakers instead of headphones: the mic hears the call again, and that echo would be
/// transcribed as "You". The gate compares each 20 ms of mic audio with how loud the call
/// (system audio) was just before: when the mic is no louder than the call's usual leak into
/// it, that slice is echo and is silenced before it's cut into chunks. Your own voice is much
/// louder than the leak, so it passes, even while others talk.
///
/// The echo's delay is found by matching the loudness patterns of the two streams (the lag
/// where they correlate best), so each mic slice is compared with the moment of the call it
/// would be an echo of. How much of the call leaks into the mic ("leak") is learned as it goes:
/// the median mic/call loudness ratio while the call is clearly loud. With headphones there's almost no
/// leak, so almost nothing is gated. Mic audio is held back briefly (`hold`) so the matching
/// call audio has arrived before deciding.
public final class EchoGate {
    public static let rate = 16_000
    public static let frame = 320  // 20 ms
    /// Call audio quieter than this can't cause audible echo.
    public static let callActive: Float = 0.004
    /// The mic must be this many times louder than the expected leak to count as you.
    public static let margin: Float = 3
    /// How far back (and ahead) the call audio can be from the mic's copy of it, in seconds:
    /// speaker and room delay plus the two capture paths' buffering.
    public static let lookBack = 0.6, lookAhead = 0.15
    /// Mic audio is decided this long after it arrives.
    public static let hold = 0.3
    /// After a slice that is clearly you, keep this many more (160 ms) so word endings and
    /// soft sounds between syllables aren't clipped.
    public static let hangover = 8
    /// Until enough has been heard to learn the leak, assume this much (a laptop speaker).
    public static let startingLeak: Float = 0.3

    private var call: [Int: Float] = [:]  // call loudness per 20 ms slot (slot = time / 20 ms)
    private var micHistory: [(slot: Int, rms: Float)] = []  // recent mic loudness, for finding the delay
    /// The echo's delay in 20 ms slots, once found (negative: the mic's buffers arrive first).
    public private(set) var delaySlots: Int?
    private var sinceDelayCheck = 0
    private var held: [Float] = []
    private var heldEnd = 0.0  // arrival time of the newest held sample
    private var ratios: [Float] = []  // recent mic/call loudness at the echo's delay, call clearly loud
    private var rough: [Float] = []  // the same before the delay is known (vs. the loudest nearby moment)
    private var openFor = 0  // slices still kept after your last clear one
    public private(set) var silencedFrames = 0
    public private(set) var keptFrames = 0

    public init() {}

    /// Call moments at least this loud teach the leak (quieter ones are mostly room noise).
    public static let callLoud: Float = 0.02

    /// The leak estimate: the median mic/call ratio over recent loud call moments (robust to
    /// fading syllables and to you talking now and then). Until ~0.5 s of loud call has been
    /// heard, a laptop speaker's leak is assumed.
    public var leak: Float {
        // No delay found yet (with headphones there's no echo to find): the rough ratios, which
        // can only under-estimate the leak, so your voice is never silenced by a wrong guess.
        let source = delaySlots != nil && ratios.count >= 25 ? ratios : rough
        guard source.count >= 25 else { return Self.startingLeak }
        let sorted = source.sorted()
        return sorted[sorted.count / 2]
    }

    /// System audio (the call) that arrived ending at `time` (seconds, any steady clock).
    public func system(_ samples: [Float], at time: Double) {
        let frames = samples.count / Self.frame
        for i in 0..<frames {
            let slice = samples[(i * Self.frame)..<((i + 1) * Self.frame)]
            let start = time - Double(samples.count - i * Self.frame) / Double(Self.rate)
            call[Self.slot(start)] = Self.rms(slice)
        }
        let oldest = Self.slot(time - 4)
        call = call.filter { $0.key >= oldest }
    }

    /// Mic audio that arrived ending at `time`; returns the mic audio now decided (older than
    /// `hold`), with echo silenced. Over a recording nothing is lost: `flush` returns the rest.
    public func mic(_ samples: [Float], at time: Double) -> [Float] {
        held += samples
        heldEnd = time
        let ready = max(0, held.count - Int(Self.hold * Double(Self.rate)))
        let whole = ready / Self.frame * Self.frame
        guard whole > 0 else { return [] }
        var out = Array(held[0..<whole])
        held.removeFirst(whole)
        decide(&out, endingAt: time - Double(held.count) / Double(Self.rate))
        return out
    }

    /// Everything still held (when recording stops), decided the same way.
    public func flush() -> [Float] {
        var out = held
        held = []
        decide(&out, endingAt: heldEnd)
        return out
    }

    private func decide(_ audio: inout [Float], endingAt end: Double) {
        let frames = audio.count / Self.frame
        for i in 0..<frames {
            let range = (i * Self.frame)..<((i + 1) * Self.frame)
            let time = end - Double(audio.count - i * Self.frame) / Double(Self.rate)
            let slot = Self.slot(time)
            let mine = Self.rms(audio[range])
            remember(slot, mine)
            let reference: Float
            if let lag = delaySlots {  // the moment it echoes, give or take a slot
                reference = ((lag - 1)...(lag + 1)).compactMap { call[slot - $0] }.max() ?? 0
            } else {  // delay not known yet: the loudest call moment it could be
                reference = (Self.minLag...Self.maxLag).compactMap { call[slot - $0] }.max() ?? 0
            }
            guard reference >= Self.callActive else { keptFrames += 1; continue }
            let ratio = mine / reference
            // Learn the leak only at the known delay, against the exact moment it echoes.
            if let lag = delaySlots, let exact = call[slot - lag], exact >= Self.callLoud {
                ratios.append(mine / exact)
                if ratios.count > 400 { ratios.removeFirst(ratios.count - 400) }  // the last ~8 s of call
            } else if delaySlots == nil, reference >= Self.callLoud {
                rough.append(ratio)
                if rough.count > 400 { rough.removeFirst(rough.count - 400) }
            }
            if ratio >= Self.margin * leak {
                openFor = Self.hangover  // clearly you
                keptFrames += 1
            } else if openFor > 0 {
                openFor -= 1  // the tail of what you were saying
                keptFrames += 1
            } else {
                for k in range { audio[k] = 0 }
                silencedFrames += 1
            }
        }
    }

    static let minLag = -Int(lookAhead / 0.02), maxLag = Int(lookBack / 0.02)

    static func slot(_ time: Double) -> Int { Int((time / 0.02).rounded(.down)) }

    /// Keep the mic's loudness, and every ~2 s re-find the delay: the lag where the mic's
    /// loudness pattern best follows the call's (correlation of log loudness over ~6 s).
    private func remember(_ slot: Int, _ rms: Float) {
        micHistory.append((slot, rms))
        if micHistory.count > 300 { micHistory.removeFirst(micHistory.count - 300) }
        sinceDelayCheck += 1
        guard sinceDelayCheck >= 100, micHistory.count >= 150 else { return }
        sinceDelayCheck = 0
        var best: (lag: Int, corr: Float)?
        for lag in Self.minLag...Self.maxLag {
            var xs: [Float] = [], ys: [Float] = []
            for (s, m) in micHistory {
                if let c = call[s - lag], c >= Self.callActive { xs.append(log(m + 1e-4)); ys.append(log(c + 1e-4)) }
            }
            guard xs.count >= 50 else { continue }
            let corr = Self.correlation(xs, ys)
            if corr > (best?.corr ?? 0.5) { best = (lag, corr) }
        }
        if let best {
            if best.lag != delaySlots { ratios = [] }  // what was learned at another delay doesn't apply
            delaySlots = best.lag
        }
    }

    static func correlation(_ x: [Float], _ y: [Float]) -> Float {
        let n = Float(x.count), mx = x.reduce(0, +) / n, my = y.reduce(0, +) / n
        var sxy: Float = 0, sxx: Float = 0, syy: Float = 0
        for i in x.indices { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) * (x[i] - mx); syy += (y[i] - my) * (y[i] - my) }
        return sxx > 0 && syy > 0 ? sxy / (sxx * syy).squareRoot() : 0
    }

    static func rms(_ x: ArraySlice<Float>) -> Float {
        guard !x.isEmpty else { return 0 }
        return (x.reduce(0) { $0 + $1 * $1 } / Float(x.count)).squareRoot()
    }
}
