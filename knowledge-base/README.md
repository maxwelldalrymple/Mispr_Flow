# Knowledge base

Everything about Mispr Flow and how it was built, written so an AI assistant (Claude, ChatGPT…) or a new contributor can get up to speed fast.

**Quickest use:** paste or upload [`ALL-IN-ONE.md`](ALL-IN-ONE.md) into a chat, or add this folder to a Claude Project's knowledge. Claude Code also reads [`../CLAUDE.md`](../CLAUDE.md) automatically.

| File | What |
|---|---|
| [01-overview.md](01-overview.md) | What the project is, its architecture, models and paths |
| [02-history.md](02-history.md) | Everything we did, in order (the chat history) |
| [03-decisions.md](03-decisions.md) | Each decision and why |
| [04-research.md](04-research.md) | Benchmarks and findings with numbers |
| [05-working-with-the-user.md](05-working-with-the-user.md) | Preferences and conventions to follow |
| [06-open-items.md](06-open-items.md) | What's next, known limits |
| [07-chat-log.md](07-chat-log.md) | The full conversation: every user message and assistant reply (262 KB) |
| [08-your-messages.md](08-your-messages.md) | Just the user's 237 messages, in order, including those sent while Claude was working |

Detailed guides are in [`../docs/`](../docs/). Per-change reports with test results are in [`../logs/`](../logs/README.md).

Rebuild `ALL-IN-ONE.md` after editing any file with `python tools/build_knowledge_base.py`. It includes everything except the full chat log, to stay small enough to paste.

Re-export the chat from the Claude Code transcript with `python tools/export_chat_history.py ~/.claude/projects/<folder>/<session>.jsonl`.
