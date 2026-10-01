# Engine ↔ app protocol

The SwiftUI app (`macos/`) starts the Python engine (`python -m mispr` with `MISPR_HOSTED=1`), and the two talk in **JSON lines** over the engine's stdin/stdout.

- **App → engine:** `{"cmd": "<name>", ...}`, one per line on stdin. Handled in `mispr/app.py: _connect_host`.
- **Engine → app:** lines starting with `@mispr ` followed by `{"event": "<name>", ...}`, on a private duplicate of stdout (`host.open_channel`). Ordinary prints and logs don't collide with it. Parsed in `MisprCore/EngineProtocol.swift`.
- The engine quits when stdin closes (the app quit or crashed). The app restarts a crashed engine.

## Commands (app → engine)

| cmd | Fields | Does |
|---|---|---|
| `open_setup` | | Shows the setup window |
| `reload_settings` | | Re-reads settings.json (dictation key, switch key, nicknames, Incognito…) |
| `quit` | | Quits the engine |
| `start_meeting` / `stop_meeting` | | The widget shows / hides its meeting pill |
| `meeting_level` | `level` | Live audio level for the widget during a meeting |
| `transcribe_chunk` | `id, path, stream ("you"/"them"), offset, delete, partial` | Final text (or a live preview when `partial`) for one WAV chunk |
| `summarize` | `id, lines` | Writes the meeting summary |
| `ask` | `id, question, lines` | Answers a question ("" = What did I miss?) |
| `try_prompt` | `text, system, extra, examples, guard` | Runs the Prompts page's draft on sample text |

## Events (engine → app)

| event | Fields | Means |
|---|---|---|
| `hello` | `recordings_dir, settings_path, prompts_path, default_prompts` | The engine started; where its data lives |
| `saved` | `path` | A dictation or command was saved (or updated): refresh history |
| `open_note` | `start` | ⌥M / ◉: show the note panel (and start or stop) |
| `meeting` | `active` | A meeting started or stopped from the widget |
| `chunk_text` | `id, stream, speaker, offset, text, voice, partial, last` | Transcript text. One chunk can become several lines (one per speaker); only the last has `last: true` |
| `speakers_merged` | `id, speaker, into` | Two voices were one person: relabel |
| `summary` | `id, summary` | Summary JSON: title, overview, decisions, action_items, open_questions |
| `answer` | `id, question, text` | The answer to `ask` |
| `tried` | `output, applied, rejected, ms` | The Prompts page's Try-it result |
| `settings_changed` | | The engine changed settings.json itself (a nickname set by voice) |

Unknown events are ignored (`EngineEvent.unknown`), so older apps keep working with newer engines.
