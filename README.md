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

- **Local-only processing.** No audio or transcript is sent over the network. The app should work with networking disabled.
- **Audio never touches disk.** Recordings live only in RAM. This matters because on SSDs and APFS, overwriting a file "in place" does not guarantee the original blocks are destroyed: copy-on-write, wear leveling, and snapshots can all leave the old data physically recoverable. Keeping audio in memory avoids that problem entirely.
- **Explicit zeroization.** Once transcription completes, the audio buffer is overwritten with zeros before it is released, and where possible it is locked in memory so it cannot be paged out to swap.
- **Minimal retention.** Transcripts are not logged or stored unless the user explicitly opts in.
- **Clipboard hygiene.** If the clipboard is used to paste, its previous contents are restored afterward so dictated text does not linger.

## Target Platform

- macOS on Apple Silicon (developed on an M1 Pro with 16 GB RAM, macOS 26)

## Status

Planning phase. See the `planning` branch for design decisions in progress.
