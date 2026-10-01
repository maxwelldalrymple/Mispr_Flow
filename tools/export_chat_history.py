"""Export the Claude Code conversation(s) behind this project into the knowledge base:
python tools/export_chat_history.py TRANSCRIPT.jsonl [...]

Writes knowledge-base/07-chat-log.md (every user message and assistant reply, in order) and
knowledge-base/08-your-messages.md (just the user's messages). Tool calls and their output,
system reminders and background-task notices are left out. Transcripts live in
~/.claude/projects/<folder>/<session>.jsonl.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = ("<command-", "<local-command", "Caveat:", "This session is being continued", "[Request interrupted",
        "<task-notification>")


def clean(text):
    return re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S).strip()


def turns(path):
    """[(timestamp, "user" | "assistant", text)] in order."""
    out = []
    for line in open(path, encoding="utf-8"):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        kind = e.get("type")
        queued = e.get("attachment") or {}
        if kind == "attachment" and queued.get("type") == "queued_command" and (queued.get("origin") or {}).get("kind") == "human":
            prompt = queued.get("prompt")
            if isinstance(prompt, list):
                prompt = " ".join(p.get("text", "[image attached]") if isinstance(p, dict) else str(p) for p in prompt)
            if prompt and str(prompt).strip():  # a message sent while the assistant was working
                out.append((e.get("timestamp", "")[:19].replace("T", " "), "user",
                            clean(str(prompt)) + "  *(sent while Claude was working)*"))
            continue
        if kind not in ("user", "assistant") or e.get("isMeta") or e.get("isCompactSummary"):
            continue
        content = e.get("message", {}).get("content")
        items = [{"type": "text", "text": content}] if isinstance(content, str) else (content or [])
        texts = []
        for c in items:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_result":
                continue
            if c.get("type") == "text":
                t = clean(c.get("text", ""))
                if t and not t.startswith(SKIP):
                    texts.append(t)
            elif c.get("type") == "image" and kind == "user":
                texts.append("[image attached]")
        if texts:
            out.append((e.get("timestamp", "")[:19].replace("T", " "), kind, "\n\n".join(texts)))
    return out


def main(paths):
    all_turns = [t for p in paths for t in turns(p)]
    header = ("Exported from the Claude Code transcript(s) by `tools/export_chat_history.py`. Times are UTC. "
              "Tool calls and their output are left out; the work they did is in `logs/` and git history. "
              "The project began in an earlier claude.ai chat (\"Whispr Clone\") that isn't included here.\n")
    log = ["# 7. Chat log (full conversation)\n", header]
    mine = ["# 8. Every message from the user, in order\n", header]
    n = 0
    for ts, who, text in all_turns:
        if who == "user":
            n += 1
            log.append(f"\n### {ts} · User\n\n{text}\n")
            mine.append(f"{n}. *{ts}* {text.replace(chr(10), ' ')}")
        else:
            log.append(f"\n**Claude:** {text}\n")
    (ROOT / "knowledge-base" / "07-chat-log.md").write_text("\n".join(log))
    (ROOT / "knowledge-base" / "08-your-messages.md").write_text("\n".join(mine) + "\n")
    print(f"wrote 07-chat-log.md ({len(all_turns)} entries) and 08-your-messages.md ({n} user messages)")


if __name__ == "__main__":
    main(sys.argv[1:])
