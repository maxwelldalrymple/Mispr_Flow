# Whispr Clone

A privacy-first, fully local voice dictation tool for macOS, modeled on the Wispr Flow desktop experience but with **no cloud processing and no persistent audio**.

## Motivation

Wispr Flow offers excellent system-wide dictation: press a hotkey, speak, and polished text appears in whatever application you are using. However, its speech-to-text and text-cleanup pipeline runs in the cloud, which means recordings of your voice leave your machine and may be retained by a third party. For anyone dictating sensitive material (code, credentials in context, personal or business communication), that is an unacceptable privacy risk.

This project reproduces the same workflow entirely on-device, and treats captured audio as ephemeral data that is destroyed as soon as it has been transcribed.

## How It Works

1. **Activation.** Holding the `fn` key (push-to-talk) or double-tapping it within one second (toggle mode) begins recording.
2. **Capture.** Microphone audio is captured into an in-memory buffer.
3. **Transcription.** A local speech-to-text model converts the audio to raw text.
4. **Cleanup.** A lightweight local language model removes filler words, fixes punctuation and capitalization, and applies light formatting, without changing the meaning.
5. **Insertion.** The cleaned text is pasted into the currently focused input, whether that is the Claude app, ChatGPT in a browser, an editor, or any other text field.
6. **Destruction.** The audio buffer is securely wiped immediately after transcription.

## Privacy Principles

- **Local-only processing.** No audio or transcript is sent over the network. The app works with networking disabled (after the one-time model download).
- **Local-only storage, by default.** Recordings and their transcripts are saved to `~/Documents/voice-recordings` so the app can show history and usage stats. They never leave the machine.
- **Incognito mode.** When on, audio never touches disk: it lives only in locked RAM and is zeroed right after transcription. This is the only mode that guarantees a recording is unrecoverable, because on SSDs and APFS, deleting or overwriting a saved file does not reliably destroy the original blocks (copy-on-write, wear leveling, snapshots).
- **Explicit zeroization.** In every mode, the in-memory audio buffer is locked so it cannot be paged out to swap, and zeroed once it has been used.
- **Clipboard hygiene.** Pasted text is marked transient/concealed so clipboard managers skip it, and the previous clipboard is restored afterward.

## Target Platform

- macOS on Apple Silicon (developed on an M1 Pro with 16 GB RAM, macOS 26)

## Running

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m whispr
```

Quit from the waveform icon in the menu bar.

## Status

The floating widget is built (UI only: clicks drive it and the waveform is simulated). See [PLAN.md](PLAN.md) for the stack, architecture, and milestones.
