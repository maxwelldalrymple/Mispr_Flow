"""Write made-up dictations over the past two weeks to voice-recordings/ so History and Insights
can be checked across many days: python tools/make_sample_dictations.py [--remove]

Each one gets real audio made with macOS's `say` (16 kHz mono WAV, like a real recording) and a
JSON record in the engine's format, marked "sample": true. --remove deletes only those.
"""
import json
import subprocess
import sys
import wave
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "voice-recordings"

APPS = {
    "Slack": ("com.tinyspeck.slackmacgap", None, None),
    "Mail": ("com.apple.mail", None, None),
    "Messages": ("com.apple.MobileSMS", None, None),
    "Notes": ("com.apple.Notes", None, None),
    "VS Code": ("com.microsoft.VSCode", None, None),
    "Claude": ("com.anthropic.claudefordesktop", None, None),
    "ChatGPT": ("com.google.Chrome", "https://chatgpt.com/", "ChatGPT"),
    "Gmail": ("com.google.Chrome", "https://mail.google.com/mail/u/0/", "Inbox"),
    "Notion": ("notion.id", None, None),
    "Finder": ("com.apple.finder", None, None),
}

# (days ago, hour, minute, app, what was said (raw), cleaned text, status)
DICTATIONS = [
    (1, 9, 12, "Slack", "Um, morning team, I'm, I'm running about ten minutes late for standup.", "Morning team, I'm running about ten minutes late for standup.", "pasted"),
    (1, 9, 40, "Gmail", "Hi Dana, thanks for setting up the trial instances. We'll run the benchmarks today and, uh, send results by Thursday.", "Hi Dana, thanks for setting up the trial instances. We'll run the benchmarks today and send results by Thursday.", "pasted"),
    (1, 14, 5, "Claude", "Can you write a Python function that, like, batches small image files into one upload stream?", "Can you write a Python function that batches small image files into one upload stream?", "pasted"),
    (1, 22, 18, "Notes", "Idea for the widget: show the elapsed time while recording in hands-free mode.", "Idea for the widget: show the elapsed time while recording in hands-free mode.", "pasted"),
    (2, 8, 55, "Messages", "On my way, grab me a coffee please, thanks!", "On my way, grab me a coffee please, thanks!", "pasted"),
    (2, 11, 30, "ChatGPT", "What's the difference between iperf throughput and real file transfer speed?", "What's the difference between iperf throughput and real file transfer speed?", "pasted"),
    (2, 16, 45, "VS Code", "Add a test that, um, checks the dictation key falls back to fn when the settings are broken.", "Add a test that checks the dictation key falls back to fn when the settings are broken.", "pasted"),
    (2, 17, 2, "Finder", "Rename this folder to final designs, no wait, to approved designs.", "Rename this folder to approved designs.", "copied"),
    (4, 10, 15, "Slack", "Priya, the onboarding screens look great. Ship them after the copy tweaks.", "Priya, the onboarding screens look great. Ship them after the copy tweaks.", "pasted"),
    (4, 13, 20, "Notion", "Release checklist: sign the app, test the installer on a clean Mac, and update the changelog.", "Release checklist: sign the app, test the installer on a clean Mac, and update the changelog.", "pasted"),
    (4, 15, 0, "Claude", "Basically I need a SwiftUI flow layout that wraps tags onto new lines.", "I need a SwiftUI flow layout that wraps tags onto new lines.", "pasted"),
    (4, 15, 1, "Claude", "", "", "cancelled"),
    (5, 9, 5, "Mail", "Hi Rachel, thanks for the intro. Happy to meet the legal tech team next week. Best, Max.", "Hi Rachel, thanks for the intro. Happy to meet the legal tech team next week. Best, Max.", "pasted"),
    (5, 12, 40, "ChatGPT", "Summarize the tradeoffs between Montreal and Virginia for GPU hosting latency.", "Summarize the tradeoffs between Montreal and Virginia for GPU hosting latency.", "pasted"),
    (5, 21, 50, "Notes", "Remember to, uh, back up the model files before switching providers.", "Remember to back up the model files before switching providers.", "pasted"),
    (6, 10, 0, "Slack", "Can someone review my pull request for the incognito changes? Thanks!", "Can someone review my pull request for the incognito changes? Thanks!", "pasted"),
    (6, 14, 25, "VS Code", "Rename the function to focused text target and, like, return a tuple with the reason.", "Rename the function to focused text target and return a tuple with the reason.", "pasted"),
    (8, 9, 30, "Gmail", "Hi team, the beta has forty two active testers. Full numbers are in the doc.", "Hi team, the beta has forty two active testers. Full numbers are in the doc.", "pasted"),
    (8, 11, 10, "Claude", "Explain how macOS decides which app owns a microphone permission when one app launches another.", "Explain how macOS decides which app owns a microphone permission when one app launches another.", "pasted"),
    (8, 16, 35, "Messages", "Sounds good, see you at seven.", "Sounds good, see you at seven.", "pasted"),
    (9, 10, 45, "Notion", "Meeting notes: hold notetaker for the next update and focus the launch on dictation.", "Meeting notes: hold notetaker for the next update and focus the launch on dictation.", "pasted"),
    (9, 13, 15, "ChatGPT", "Give me five names for a privacy first dictation app.", "Give me five names for a privacy first dictation app.", "pasted"),
    (11, 9, 0, "Slack", "Good morning! Standup notes are in the thread.", "Good morning! Standup notes are in the thread.", "pasted"),
    (11, 15, 30, "Claude", "Write a commit message for adding six color themes to the profile settings.", "Write a commit message for adding six color themes to the profile settings.", "pasted"),
    (12, 10, 20, "Mail", "Hi Jordan, can you take the installer test on Friday? Thanks so much.", "Hi Jordan, can you take the installer test on Friday? Thanks so much.", "pasted"),
    (12, 17, 55, "Notes", "Pick up groceries: eggs, coffee, and, um, oat milk.", "Pick up groceries: eggs, coffee, and oat milk.", "pasted"),
    (13, 11, 5, "VS Code", "Make the history list lazy so scrolling stays smooth with hundreds of rows.", "Make the history list lazy so scrolling stays smooth with hundreds of rows.", "pasted"),
    (13, 14, 40, "ChatGPT", "How do I sign a macOS app with a self signed certificate so permissions persist?", "How do I sign a macOS app with a self signed certificate so permissions persist?", "pasted"),
]


def say_to_wav(text, path):
    subprocess.run(["say", "-o", str(path), "--data-format=LEI16@16000", text or "um"], check=True)
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def main():
    if "--remove" in sys.argv:
        removed = 0
        for f in OUT.glob("*/*.json"):
            record = json.loads(f.read_text())
            if record.get("sample"):
                f.with_suffix(".wav").unlink(missing_ok=True)
                f.unlink()
                removed += 1
        print(f"removed {removed} sample dictations")
        return
    now = datetime.now().astimezone()
    for days_ago, hour, minute, app, raw, clean, status in DICTATIONS:
        started = (now - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=7, microsecond=0)
        stem = f"{started:%Y-%m-%d_%H-%M-%S}-000"
        day = OUT / f"{started:%Y-%m-%d}"
        day.mkdir(parents=True, exist_ok=True)
        seconds = say_to_wav(raw, day / f"{stem}.wav")
        bundle, url, title = APPS[app]
        target = {"app": "Google Chrome" if url else app, "bundle_id": bundle, "url": url, "page_title": title}
        record = {
            "id": stem,
            "sample": True,
            "started_at": started.isoformat(timespec="milliseconds"),
            "ended_at": (started + timedelta(seconds=seconds)).isoformat(timespec="milliseconds"),
            "duration_s": round(seconds, 1),
            "status": status,
            "transcript": clean,
            "raw_transcript": raw,
            "words": len(clean.split()),
            "recorded_in": {"app": target["app"], "bundle_id": bundle},
            "pasted_into": None if status == "cancelled" else target,
            "model": "ggml-large-v3-turbo-q5_0.bin",
            "cleanup": {"model": "gemma-3-4b-it-Q4_K_M.gguf", "applied": raw != clean, "ms": 600, "rejected": None},
            "audio_file": f"{stem}.wav",
        }
        (day / f"{stem}.json").write_text(json.dumps(record, indent=2))
    print(f"wrote {len(DICTATIONS)} sample dictations over {len({d[0] for d in DICTATIONS})} days")


if __name__ == "__main__":
    main()
