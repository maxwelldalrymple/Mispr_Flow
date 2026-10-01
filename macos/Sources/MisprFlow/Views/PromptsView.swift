import Combine
import MisprCore
import SwiftUI

/// How the local model cleans up and writes your dictation: the instructions it follows,
/// your own rules, the examples it learns from, and a box to try a draft before saving.
struct PromptsView: View {
    @EnvironmentObject var model: AppModel
    @State private var draft: PromptDraft?
    @State private var saved: PromptDraft?
    @State private var sample = "Um, so I was thinking we could, uh, move the meeting to, like, Thursday. No wait, Friday."
    @State private var result: TryResult?
    @State private var trying = false
    @State private var status: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                header
                if let defaults = model.engine.defaultPrompts, let file = model.engine.promptsFile {
                    if draft != nil { editor(defaults: defaults, file: file) }
                } else {
                    Card { Text("Waiting for the dictation engine…").foregroundStyle(Theme.secondary) }
                }
            }
            .padding(.horizontal, 40).padding(.vertical, 36)
            .frame(maxWidth: 1000, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .onAppear(perform: load)
        .onChange(of: model.engine.promptsFile) { load() }
        .onReceive(model.engine.tried) { result = $0; trying = false }
    }

    private var header: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 6) {
                Text("Prompts").font(.system(size: 24, weight: .semibold))
                Text("Tell the local model how to clean up and write what you say. Changes apply to your next dictation.")
                    .font(.system(size: 13)).foregroundStyle(Theme.secondary)
            }
            Spacer()
            if let status { Text(status).font(.system(size: 12)).foregroundStyle(Theme.secondary).padding(.top, 6) }
            Button("Revert") { draft = saved; status = nil }
                .buttonStyle(OutlineButton()).disabled(draft == saved)
            Button("Save") { save() }
                .buttonStyle(DarkButton()).disabled(draft == saved)
                .keyboardShortcut("s", modifiers: .command)
        }
    }

    @ViewBuilder
    private func editor(defaults: DefaultPrompts, file: URL) -> some View {
        let binding = Binding(get: { draft! }, set: { draft = $0; status = nil })

        section("Cleanup instructions", "The system prompt: what the model is told before every dictation. This is the one in use now.",
                reset: binding.wrappedValue.system == defaults.system ? nil : { draft?.system = defaults.system }) {
            PromptEditor(text: binding.system, minHeight: 230)
        }
        section("Your rules", "Added after the instructions. One per line, e.g. \"Use British spelling.\" or \"Write numbers as digits.\"",
                reset: binding.wrappedValue.extra.isEmpty ? nil : { draft?.extra = "" }) {
            PromptEditor(text: binding.extra, minHeight: 90, placeholder: "Use British spelling.\nNever use exclamation marks.")
        }
        section("Examples", "Before/after pairs the model copies. Write each as a “Said:” line and a “Wrote:” line, with a blank line between pairs.",
                reset: binding.wrappedValue.examples == defaults.examples ? nil : { draft?.examples = defaults.examples }) {
            PromptEditor(text: binding.examples, minHeight: 170)
            Text("\(PromptDraft.parse(binding.wrappedValue.examples).count) examples")
                .font(.system(size: 11)).foregroundStyle(Theme.secondary)
        }
        Card(padding: 18) {
            HStack(alignment: .top, spacing: 16) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Only words you said").font(.system(size: 14, weight: .semibold))
                    Text(binding.wrappedValue.guardOn
                         ? "On: if the model's output contains any word you didn't say, it's thrown away and your original transcript is pasted. Keeps cleanup honest, but blocks rewording."
                         : "Off: the model may reword, reformat, or add words (\"make it formal\", \"turn this into bullet points\"). Read what it writes before sending.")
                        .font(.system(size: 12)).foregroundStyle(Theme.secondary).fixedSize(horizontal: false, vertical: true)
                }
                Spacer()
                Toggle("", isOn: binding.guardOn).toggleStyle(.switch).labelsHidden()
            }
        }
        tryIt
    }

    private var tryIt: some View {
        Card(padding: 18) {
            VStack(alignment: .leading, spacing: 10) {
                Text("Try it").font(.system(size: 14, weight: .semibold))
                Text("Runs your draft (saved or not) on this text with the real model.")
                    .font(.system(size: 12)).foregroundStyle(Theme.secondary)
                PromptEditor(text: $sample, minHeight: 60)
                HStack {
                    Button(trying ? "Running…" : "Run") {
                        guard let draft else { return }
                        trying = true
                        result = nil
                        model.engine.send(.tryPrompt, draft.tryArgs(text: sample))
                    }
                    .buttonStyle(DarkButton()).disabled(trying || sample.trimmingCharacters(in: .whitespaces).isEmpty)
                    if let result { Text("\(result.ms) ms").font(.system(size: 11)).foregroundStyle(Theme.secondary) }
                }
                if let result {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(result.output).font(.system(size: 13)).textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(12).background(RoundedRectangle(cornerRadius: 8).fill(Theme.content))
                        if let rejected = result.rejected {
                            Label("The model's version was rejected (\(rejected)), so this is your original text.",
                                  systemImage: "exclamationmark.triangle")
                                .font(.system(size: 12)).foregroundStyle(.orange)
                        }
                    }
                }
            }
        }
    }

    private func section<Content: View>(_ title: String, _ detail: String, reset: (() -> Void)?,
                                        @ViewBuilder content: () -> Content) -> some View {
        Card(padding: 18) {
            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .firstTextBaseline) {
                    Text(title).font(.system(size: 14, weight: .semibold))
                    Spacer()
                    if let reset { Button("Reset to default", action: reset).buttonStyle(.link).font(.system(size: 12)) }
                }
                Text(detail).font(.system(size: 12)).foregroundStyle(Theme.secondary).fixedSize(horizontal: false, vertical: true)
                content()
            }
        }
    }

    private func load() {
        guard let defaults = model.engine.defaultPrompts, let file = model.engine.promptsFile, draft == nil else { return }
        let loaded = PromptDraft.load(from: file, defaults: defaults)
        draft = loaded
        saved = loaded
    }

    private func save() {
        guard let draft, let file = model.engine.promptsFile else { return }
        do {
            try draft.save(to: file)
            saved = draft
            model.engine.send(.reloadSettings)
            status = "Saved · used from your next dictation"
        } catch {
            status = "Couldn't save: \(error.localizedDescription)"
        }
    }
}

/// A monospaced, growing text area for prompt text.
struct PromptEditor: View {
    @Binding var text: String
    var minHeight: CGFloat
    var placeholder = ""

    var body: some View {
        TextEditor(text: $text)
            .font(.system(size: 12.5, design: .monospaced))
            .scrollContentBackground(.hidden)
            .padding(8)
            .frame(minHeight: minHeight)
            .background(RoundedRectangle(cornerRadius: 8).fill(Theme.content))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.cardStroke))
            .overlay(alignment: .topLeading) {
                if text.isEmpty && !placeholder.isEmpty {
                    Text(placeholder).font(.system(size: 12.5, design: .monospaced)).foregroundStyle(Theme.secondary)
                        .padding(.horizontal, 13).padding(.vertical, 8).allowsHitTesting(false)
                }
            }
    }
}
