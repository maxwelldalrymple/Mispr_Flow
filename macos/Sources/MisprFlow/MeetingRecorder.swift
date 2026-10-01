import AVFoundation
import MisprCore
import ScreenCaptureKit

/// Records a meeting from two sources at once: the microphone ("you") and the Mac's sound
/// output ("them": the other people on a call, via ScreenCaptureKit, no video). Each stream
/// is converted to 16 kHz mono, cut into chunks at pauses, and handed to `onChunk`; the full
/// streams can also be saved as WAV files.
final class MeetingRecorder: NSObject, SCStreamOutput, SCStreamDelegate {
    var onChunk: (_ stream: String, _ start: Double, _ samples: [Float]) -> Void = { _, _, _ in }
    var onLevel: (Float) -> Void = { _ in }
    var onError: (String) -> Void = { _ in }

    private let queue = DispatchQueue(label: "meeting-audio")
    private let engine = AVAudioEngine()
    private var screen: SCStream?
    private var micResampler: Resampler?
    private var systemResampler: Resampler?
    private var segmenters = ["you": Segmenter(), "them": Segmenter()]
    private var writers: [String: StreamingWAV] = [:]
    private var levels = ["you": Float(0), "them": Float(0)]
    private var lastLevelSent = Date.distantPast

    /// `saveTo`: folder for you.wav / them.wav (nil = keep nothing, e.g. Incognito).
    /// Throws if the mic can't start. If only system audio fails, the mic keeps recording and
    /// the returned message says why ("them" won't be heard).
    func start(systemAudio: Bool, saveTo: URL?) async throws -> String? {
        if let saveTo {
            try FileManager.default.createDirectory(at: saveTo, withIntermediateDirectories: true)
            writers["you"] = try StreamingWAV(url: saveTo.appendingPathComponent("you.wav"))
        }
        try startMic()
        guard systemAudio else { return nil }
        do {
            if let saveTo { writers["them"] = try StreamingWAV(url: saveTo.appendingPathComponent("them.wav")) }
            try await startSystemAudio()
            return nil
        } catch {
            writers["them"]?.close()
            writers["them"] = nil
            let declined = (error as NSError).code == -3801
            return declined
                ? "Screen & System Audio isn't allowed, so only your mic is being recorded. Turn it on to hear the others."
                : "System audio didn't start (\(error.localizedDescription)); recording your mic only."
        }
    }

    func stop() {
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        let screen = self.screen
        self.screen = nil
        Task { try? await screen?.stopCapture() }
        queue.sync {
            for stream in ["you", "them"] {
                if let chunk = segmenters[stream]?.flush() { onChunk(stream, chunk.start, chunk.samples) }
            }
            writers.values.forEach { $0.close() }
            writers = [:]
        }
    }

    // MARK: - Microphone

    private func startMic() throws {
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        guard format.sampleRate > 0 else { throw RecorderError("No microphone is available.") }
        micResampler = Resampler(from: format)
        input.installTap(onBus: 0, bufferSize: 4096, format: format) { [weak self] buffer, _ in
            guard let self, let samples = self.micResampler?.convert(buffer) else { return }
            self.queue.async { self.take("you", samples) }
        }
        try engine.start()
    }

    // MARK: - System audio

    private func startSystemAudio() async throws {
        guard let display = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true).displays.first else {
            throw RecorderError("No display to capture audio from.")
        }
        let config = SCStreamConfiguration()
        config.capturesAudio = true
        config.excludesCurrentProcessAudio = true  // never transcribe our own sound cues
        config.sampleRate = 48_000
        config.channelCount = 1
        config.width = 2  // audio only; keep the (required) video stream tiny and rare
        config.height = 2
        config.minimumFrameInterval = CMTime(value: 1, timescale: 1)
        let stream = SCStream(filter: SCContentFilter(display: display, excludingApplications: [], exceptingWindows: []),
                              configuration: config, delegate: self)
        try stream.addStreamOutput(self, type: .audio, sampleHandlerQueue: queue)
        try await stream.startCapture()
        screen = stream
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer buffer: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .audio, let pcm = buffer.pcmBuffer else { return }
        if systemResampler == nil { systemResampler = Resampler(from: pcm.format) }
        if let samples = systemResampler?.convert(pcm) { take("them", samples) }
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        onError("System audio stopped: \(error.localizedDescription)")
    }

    // MARK: - Shared

    /// On `queue`: save, chunk, and meter one batch of 16 kHz samples.
    private func take(_ stream: String, _ samples: [Float]) {
        writers[stream]?.append(samples)
        for chunk in segmenters[stream]?.feed(samples) ?? [] { onChunk(stream, chunk.start, chunk.samples) }
        let rms = (samples.reduce(0) { $0 + $1 * $1 } / Float(max(samples.count, 1))).squareRoot()
        levels[stream] = rms
        if Date().timeIntervalSince(lastLevelSent) > 0.1 {
            lastLevelSent = Date()
            onLevel(min(1, max(levels["you"] ?? 0, levels["them"] ?? 0) * 8))
        }
    }
}

struct RecorderError: LocalizedError {
    let message: String
    init(_ message: String) { self.message = message }
    var errorDescription: String? { message }
}

/// Any input format -> 16 kHz mono Float32.
final class Resampler {
    static let target = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 16_000, channels: 1, interleaved: false)!
    private let converter: AVAudioConverter?

    init(from format: AVAudioFormat) {
        converter = AVAudioConverter(from: format, to: Self.target)
    }

    func convert(_ buffer: AVAudioPCMBuffer) -> [Float]? {
        guard let converter, buffer.frameLength > 0 else { return nil }
        let capacity = AVAudioFrameCount(Double(buffer.frameLength) * 16_000 / buffer.format.sampleRate) + 32
        guard let out = AVAudioPCMBuffer(pcmFormat: Self.target, frameCapacity: capacity) else { return nil }
        var fed = false
        var error: NSError?
        converter.convert(to: out, error: &error) { _, status in
            if fed { status.pointee = .noDataNow; return nil }
            fed = true
            status.pointee = .haveData
            return buffer
        }
        guard error == nil, let data = out.floatChannelData else { return nil }
        return Array(UnsafeBufferPointer(start: data[0], count: Int(out.frameLength)))
    }
}

/// A 16 kHz mono 16-bit WAV written as audio arrives (header patched on close).
final class StreamingWAV {
    private let handle: FileHandle
    private var bytes: UInt32 = 0

    init(url: URL) throws {
        FileManager.default.createFile(atPath: url.path, contents: WAV.data([]))
        handle = try FileHandle(forWritingTo: url)
        try handle.seekToEnd()
    }

    func append(_ samples: [Float]) {
        var data = Data(capacity: samples.count * 2)
        for s in samples {
            withUnsafeBytes(of: Int16(max(-1, min(1, s)) * 32767).littleEndian) { data.append(contentsOf: $0) }
        }
        try? handle.write(contentsOf: data)
        bytes += UInt32(data.count)
    }

    func close() {
        func patch(_ offset: UInt64, _ value: UInt32) {
            try? handle.seek(toOffset: offset)
            withUnsafeBytes(of: value.littleEndian) { try? handle.write(contentsOf: Data($0)) }
        }
        patch(4, 36 + bytes)
        patch(40, bytes)
        try? handle.close()
    }
}

extension CMSampleBuffer {
    /// The audio in a ScreenCaptureKit sample buffer as an AVAudioPCMBuffer.
    var pcmBuffer: AVAudioPCMBuffer? {
        guard let description = formatDescription, var asbd = description.audioStreamBasicDescription,
              let format = AVAudioFormat(streamDescription: &asbd) else { return nil }
        let frames = AVAudioFrameCount(numSamples)
        guard frames > 0, let pcm = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames) else { return nil }
        pcm.frameLength = frames
        let status = CMSampleBufferCopyPCMDataIntoAudioBufferList(self, at: 0, frameCount: Int32(frames), into: pcm.mutableAudioBufferList)
        return status == noErr ? pcm : nil
    }
}
