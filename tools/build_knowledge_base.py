"""Build knowledge-base/ALL-IN-ONE.md: the knowledge base plus the feature and reference guides
in one file, to paste or upload into an AI assistant. Run after editing any of them:
python tools/build_knowledge_base.py"""
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS = [
    "knowledge-base/01-overview.md", "knowledge-base/05-working-with-the-user.md", "knowledge-base/02-history.md",
    "knowledge-base/03-decisions.md", "knowledge-base/04-research.md", "knowledge-base/06-open-items.md",
    "docs/features/dictation.md", "docs/features/voice-commands.md", "docs/features/meeting-notes.md",
    "docs/features/notetaker.md", "docs/features/main-window.md", "docs/features/setup-and-permissions.md",
    "docs/features/privacy.md", "docs/architecture.md", "docs/engine-protocol.md", "docs/models.md",
    "docs/testing.md", "mispr/README.md", "macos/README.md", "tools/README.md",
]

INTRO = """# Mispr Flow: complete knowledge base

You are being given the full context of the Mispr Flow project: what it is, how it's built, every
decision and why, the history of the work, research results, and how the project owner likes to
work. Read section 1 (overview) and section 2 (working preferences) first, and follow those
preferences when helping. Paths are relative to the repository root
(github.com/maxwelldalrymple/Mispr_Flow).

"""


def main():
    out = [INTRO, f"_Built {datetime.now():%Y-%m-%d %H:%M} from {len(PARTS)} files by tools/build_knowledge_base.py._\n"]
    for part in PARTS:
        text = (ROOT / part).read_text().strip()
        out.append(f"\n\n---\n\n<!-- {part} -->\n\n{text}\n")
    (ROOT / "knowledge-base" / "ALL-IN-ONE.md").write_text("".join(out))
    print(f"wrote knowledge-base/ALL-IN-ONE.md ({sum(len(o) for o in out) // 1000} KB from {len(PARTS)} files)")


if __name__ == "__main__":
    main()
