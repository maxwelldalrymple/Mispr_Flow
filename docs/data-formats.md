# Data formats

Everything is plain files on the Mac.

## `settings.json`

Path: `~/Library/Application Support/Mispr_Flow/settings.json`. Written by both the app and the engine; unknown keys are kept by the app and ignored by the engine.

```json
{
  "incognito": false, "auto_enter": false, "cleanup": true, "sounds": true,
  "hotkey": {"kind": "fn", "keycode": 63, "label": "fn"},
  "switch_hotkey": {"kind": "combo", "mods": ["control", "option"], "keycode": null, "label": "⌃⌥"},
  "app_nicknames": {"c": "Google Chrome", "scooby snacks": "Google Chrome"},
  "onboarded": true
}
```

**`hotkey` kinds:**
- `fn`;
- `modifier` (one side, by key code: 54/55 ⌘, 56/60 ⇧, 58/61 ⌥, 59/62 ⌃);
- `key` (any key code).

**`switch_hotkey`** can also be `combo`: modifiers by name, with a key code or `null`. `null` turns it off.

## `prompts.json`

Same folder. The Prompts page's cleanup instructions: `system`, `extra` (your own rules), `examples` ("Said: … / Wrote: …" pairs), `guard` (the no-invented-words check).

## A dictation or command: `voice-recordings/YYYY-MM-DD/<id>.json` (+ `<id>.wav`, 16 kHz mono)

```json
{
  "id": "2026-10-01_18-00-13-182",
  "started_at": "2026-10-01T18:00:10.120-07:00", "ended_at": "2026-10-01T18:00:13.182-07:00", "duration_s": 3.06,
  "status": "pasted",
  "transcript": "Let's ship on Friday.", "raw_transcript": "um let's ship on friday", "words": 4,
  "recorded_in": {"app": "Slack", "bundle_id": "com.tinyspeck.slackmacgap"},
  "pasted_into": {"app": "Slack", "bundle_id": "com.tinyspeck.slackmacgap", "url": null, "page_title": null},
  "model": "ggml-large-v3-turbo-q5_0.bin",
  "cleanup": {"model": "gemma-3-4b-it-Q4_K_M.gguf", "applied": true, "ms": 540, "rejected": null},
  "audio_file": "2026-10-01_18-00-13-182.wav"
}
```

**`status` values:**
- `pasted`;
- `copied` (no text box);
- `cancelled`;
- `command` (a voice command: `transcript` is what it did, e.g. "Opened claude"; `raw_transcript` is what was heard).

Commands are kept out of word counts and speed stats.

## A meeting note: `meeting-recordings/YYYY-MM-DD/<id>.json` (+ `<id>/you.wav`, `<id>/them.wav`)

```json
{
  "id": "2026-10-01_14-29-38-270", "title": "Release plan", "app": "Zoom",
  "started_at": "…", "ended_at": "…", "duration_s": 612,
  "participants": [{"name": "You", "is_me": true}, {"name": "Priya", "role": null}],
  "transcript": [{"speaker": "You", "start_s": 0.5, "text": "Let's ship Friday."}],
  "summary": {"overview": "…", "decisions": ["…"], "action_items": [{"owner": "Priya", "task": "…", "due": "Thursday"}],
              "open_questions": ["…"]},
  "my_thoughts": "…"
}
```

## Contacts: `meeting-recordings/people.json`

```json
{"Priya": {"role": "Designer", "company": "Acme", "email": "p@acme.com", "phone": "", "notes": "Loves charts."}}
```

Cards with nothing filled in are dropped.

## Other

| What | Where |
|---|---|
| Models | `~/Library/Application Support/Mispr_Flow/models/` (see [models.md](models.md)) |
| Engine log | `~/Library/Logs/Mispr Flow/engine.log` |
| Full Disk Access probe | reads `~/Library/Application Support/com.apple.TCC/TCC.db` (read only, never changed) |
