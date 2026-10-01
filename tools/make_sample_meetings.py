"""Write four made-up meetings to meeting-recordings/ so the Notetaker pages have something to
show before real meeting capture exists: python tools/make_sample_meetings.py [--remove]

Each file uses the meeting format the notetaker will write (see docs/architecture.md):
participants, a timed transcript, a summary, and your own notes. They're marked
"sample": true; --remove deletes only those.
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "meeting-recordings"
TZ = datetime.now().astimezone().tzinfo

MEETINGS = [
    {
        "title": "Weekly product sync",
        "start": (2026, 9, 29, 10, 0),
        "minutes": 11.5,
        "app": "Zoom",
        "participants": [("Max", "Founder", True), ("Priya Shah", "Design"), ("Jordan Lee", "Engineering"), ("Sam Ortiz", "Product")],
        "lines": [
            ("Max", "Morning everyone. Quick one today. I want to cover the beta feedback, the widget polish, and whether we hold the release date."),
            ("Sam", "Sounds good. I pulled the beta numbers last night. We're at forty two active testers and about thirty of them dictate every day."),
            ("Priya", "That's higher than I expected. What's the average session look like?"),
            ("Sam", "Most dictations are under twenty seconds. People use it for quick replies in Slack and for prompts in Claude and ChatGPT."),
            ("Max", "That matches what I see in my own insights. Eighty percent of mine are AI prompts."),
            ("Jordan", "On the engineering side, the big win this week is that paste now detects when there's no text box. It copies to the clipboard instead and plays the error sound."),
            ("Priya", "I love that. The old behavior felt broken. Did we change the notice copy?"),
            ("Jordan", "Yes, it says no text box, copied to clipboard. And in incognito it doesn't copy at all."),
            ("Max", "Good. Incognito should never leave anything behind. That's the whole promise."),
            ("Sam", "Testers keep asking for a way to change the shortcut. A few of them use external keyboards without a function key."),
            ("Jordan", "That shipped yesterday. You can pick any key now, right option, F5, whatever you want."),
            ("Priya", "Can we show the key name in the widget tooltip too? Otherwise people forget what they picked."),
            ("Jordan", "Already done. The tooltip and the home page both show the chosen key."),
            ("Max", "Nice. Priya, how's the widget polish going?"),
            ("Priya", "I'm happy with the pill. The one thing I'd still change is the cancel toast. The undo bar drains a little too fast."),
            ("Sam", "Five seconds felt right in testing, but a couple of people said they missed it."),
            ("Max", "Let's try seven seconds and see if anyone complains."),
            ("Jordan", "Easy change. I'll do it today."),
            ("Max", "Okay, release date. Are we still good for the fifteenth?"),
            ("Jordan", "The app itself is ready. The risk is the installer. Signing and the model download in the package still need a full test on a clean Mac."),
            ("Sam", "How long would that take?"),
            ("Jordan", "Two days if nothing goes wrong. Four if the notarization dance bites us."),
            ("Max", "Then let's keep the fifteenth as the target but make the call on the tenth. If the installer isn't solid by then, we slip a week."),
            ("Priya", "Works for me. I'll have the onboarding screens final by Friday either way."),
            ("Sam", "I'll draft the release notes and the landing page copy."),
            ("Max", "Great. Anything else?"),
            ("Jordan", "One question. Do we want meeting notes in the first release or hold it?"),
            ("Max", "Hold it. Dictation is the product. Notes can be the headline for the next update."),
            ("Sam", "Agreed. Thanks everyone."),
        ],
        "summary": {
            "overview": "Beta is healthy (42 active testers, ~30 daily). Recent fixes landed: paste detects missing text boxes, incognito never copies, and the dictation key is configurable. Release stays targeted for the 15th with a go/no-go on the 10th, gated on the installer.",
            "decisions": ["Cancel toast undo window goes from 5 to 7 seconds.", "Release target stays the 15th; go/no-go on the 10th based on the installer.", "Meeting notes are held for the next update."],
            "action_items": [("Jordan Lee", "Change the undo window to 7 seconds", "Today"), ("Jordan Lee", "Full installer test on a clean Mac", "Oct 10"), ("Priya Shah", "Finalize onboarding screens", "Friday"), ("Sam Ortiz", "Draft release notes and landing page copy", "Oct 8")],
            "open_questions": ["Will notarization add delays to the installer?"],
        },
        "thoughts": "Installer is the real risk. Ask Jordan for a mid-week update.\nTesters love the no-text-box fix.",
    },
    {
        "title": "GPU hosting: upload and download speeds",
        "start": (2026, 9, 28, 15, 30),
        "minutes": 9.0,
        "app": "Google Meet",
        "participants": [("Max", "Founder", True), ("Alex Chen", "Partner"), ("Dana Brooks", "Solutions engineer, CloudGPU")],
        "lines": [
            ("Max", "Thanks for jumping on, Dana. Alex and I want to understand transfer speeds before we commit to a provider."),
            ("Dana", "Of course. What does the workload look like?"),
            ("Alex", "We run ComfyUI locally, but the heavy generation happens on a GPU instance. The CNC box sits in the middle and relays models and images."),
            ("Max", "So the questions are how fast we can push models up and how fast results come back down."),
            ("Dana", "Got it. Our instances have ten gigabit networking, but what you actually see depends on the region and on your own uplink."),
            ("Alex", "Our office uplink is about five hundred megabits. Model files are anywhere from two to twelve gigabytes."),
            ("Dana", "At five hundred megabits a twelve gigabyte model takes a bit over three minutes in ideal conditions. Realistically plan for four or five."),
            ("Max", "That's fine if we cache models on the instance. Can we keep a persistent volume?"),
            ("Dana", "Yes, persistent storage is billed separately but it means you upload each model once."),
            ("Alex", "What about the images coming back? They're small, but there are a lot of them."),
            ("Dana", "For many small files, latency matters more than bandwidth. Batch them or stream them over one connection."),
            ("Max", "How do we measure this properly before signing anything?"),
            ("Dana", "I can give you a trial instance. Run iperf for raw throughput and time a real model upload. That tells you more than any spec sheet."),
            ("Alex", "Can we pick the region? We're in Toronto."),
            ("Dana", "Your closest regions would be Montreal or Virginia. Montreal will usually have lower latency for you."),
            ("Max", "And the cost difference between them?"),
            ("Dana", "Montreal is about eight percent more per hour, but egress is the same."),
            ("Alex", "Eight percent is fine if the latency is noticeably better."),
            ("Max", "Okay. Let's do the trial in Montreal and compare it against Virginia with the same tests."),
            ("Dana", "I'll set up both and send credentials today."),
            ("Alex", "Perfect. We'll share the numbers with you by Thursday."),
        ],
        "summary": {
            "overview": "Evaluated CloudGPU for the ComfyUI relay setup. Real-world upload for a 12 GB model is ~4–5 min on the office's 500 Mbps uplink; a persistent volume avoids re-uploads. Small result images are latency-bound, so batching matters. Trial instances in Montreal and Virginia will be benchmarked.",
            "decisions": ["Use a persistent volume so models upload once.", "Benchmark both Montreal and Virginia before choosing."],
            "action_items": [("Dana Brooks", "Set up trial instances in Montreal and Virginia and send credentials", "Today"), ("Alex Chen", "Run iperf and a real model upload on both regions", "Thursday"), ("Max", "Compare cost per hour vs latency and decide", "Friday")],
            "open_questions": ["Is Montreal's latency gain worth 8% more per hour?", "How should result images be batched?"],
        },
        "thoughts": "Ask about egress caps.\nUplink is the bottleneck, not their 10 Gb.",
    },
    {
        "title": "Design review: Insights page",
        "start": (2026, 9, 25, 13, 0),
        "minutes": 8.0,
        "app": "Zoom",
        "participants": [("Max", "Founder", True), ("Priya Shah", "Design"), ("Lena Novak", "Research")],
        "lines": [
            ("Priya", "I'll share my screen. This is the new Insights page with the usage tab on top and your voice next to it."),
            ("Lena", "The words per minute gauge reads really well. Is it compared against typing?"),
            ("Priya", "Yes. Forty words per minute is the typing baseline, so the gauge shows how many times faster you are."),
            ("Max", "I like that more than a fake percentile. It's honest."),
            ("Lena", "In research sessions people loved the fun facts. Keystrokes skipped was the favorite by far."),
            ("Priya", "The catchphrase card got a laugh too. Someone's was literally let's circle back."),
            ("Max", "Ha. What didn't land?"),
            ("Lena", "The desktop usage list confused two people. They didn't know what other tasks meant."),
            ("Priya", "We could rename it to everything else and show the top app inside it."),
            ("Max", "Do that. Clear beats clever."),
            ("Lena", "Also, three people asked if the data leaves their Mac. We should say that on the page itself."),
            ("Priya", "There's a line at the bottom of your voice, but not on usage."),
            ("Max", "Put it on both. Privacy is the reason people pick us."),
            ("Lena", "Last thing. The streak calendar is small on laptops. Can it scale with the window?"),
            ("Priya", "Yes, I'll make the cells flexible."),
            ("Max", "Great work, both of you. Ship it after those three changes."),
        ],
        "summary": {
            "overview": "Reviewed the redesigned Insights page. The typing-relative WPM gauge and fun facts tested well; 'other tasks' was confusing and privacy reassurance was missing from the usage tab.",
            "decisions": ["Rename 'other tasks' to 'everything else' and show its top app.", "Add the on-device privacy line to both Insights tabs.", "Make streak calendar cells scale with the window."],
            "action_items": [("Priya Shah", "Make the three Insights changes", "Monday"), ("Lena Novak", "Re-test with two participants", "Next week")],
            "open_questions": [],
        },
        "thoughts": "",
    },
    {
        "title": "Intro call with Northwind Ventures",
        "start": (2026, 9, 23, 11, 0),
        "minutes": 12.5,
        "app": "Google Meet",
        "participants": [("Max", "Founder", True), ("Rachel Kim", "Partner, Northwind Ventures")],
        "lines": [
            ("Rachel", "Thanks for making time, Max. I've been using the beta for a week. Tell me the story behind it."),
            ("Max", "I loved voice dictation tools but I couldn't use them for work. Everything I said went to someone's server. Mispr Flow does the whole thing on the Mac."),
            ("Rachel", "So transcription and the cleanup both run locally?"),
            ("Max", "Both. Whisper for speech to text and a small language model for cleanup. Nothing leaves the machine, and there's an incognito mode that doesn't even write to disk."),
            ("Rachel", "How does the quality compare with the cloud tools?"),
            ("Max", "For dictation it's very close. The cleanup is deliberately conservative. It can't add words you didn't say unless you turn that guard off on the prompts page."),
            ("Rachel", "That's an interesting design choice. Why so strict?"),
            ("Max", "Because the worst failure for a dictation tool is putting words in your mouth. People send these messages to their boss."),
            ("Rachel", "Fair. What's the business model if it's open source and free?"),
            ("Max", "The core stays free. We think teams will pay for things like shared dictionaries and managed deployment, still without anyone's audio leaving their devices."),
            ("Rachel", "Who's the first customer for that?"),
            ("Max", "Legal and healthcare teams. They want dictation but can't send audio to a third party."),
            ("Rachel", "That's a real wedge. How big is the team?"),
            ("Max", "Four of us right now, with two contractors on design and research."),
            ("Rachel", "And the timeline to a paid product?"),
            ("Max", "Public release next month, the team features early next year."),
            ("Rachel", "I'd like to introduce you to one of our portfolio companies in legal tech. They'd be a good design partner."),
            ("Max", "That would be fantastic, thank you."),
            ("Rachel", "I'll send an email this week. Let's talk again after your launch."),
        ],
        "summary": {
            "overview": "Intro with Rachel Kim (Northwind Ventures), who has used the beta for a week. Covered the on-device approach, the strict no-invented-words cleanup, and the plan: free core, paid team features for privacy-sensitive teams like legal and healthcare.",
            "decisions": ["Reconnect after the public launch."],
            "action_items": [("Rachel Kim", "Introduce Max to a legal-tech portfolio company", "This week"), ("Max", "Send the launch announcement to Rachel", "Launch day")],
            "open_questions": ["Pricing for team features?"],
        },
        "thoughts": "She asked good questions about the guard.\nFollow up on the legal-tech intro.",
    },
]


def build(meeting):
    start = datetime(*meeting["start"], tzinfo=TZ)
    total = meeting["minutes"] * 60
    names = {p[0].split()[0]: p[0] for p in meeting["participants"]}
    words = [len(text.split()) for _, text in meeting["lines"]]
    scale = total / sum(words)  # spread the lines over the meeting, by length
    transcript, t = [], 2.0
    for (speaker, text), n in zip(meeting["lines"], words):
        transcript.append({"speaker": names.get(speaker, speaker), "start_s": round(t, 1), "text": text})
        t += n * scale * 0.97
    stem = start.strftime("%Y-%m-%d_%H-%M-%S") + "-000"
    return stem, {
        "id": stem,
        "sample": True,
        "title": meeting["title"],
        "started_at": start.isoformat(timespec="milliseconds"),
        "ended_at": (start + timedelta(seconds=total)).isoformat(timespec="milliseconds"),
        "duration_s": round(total, 1),
        "app": meeting["app"],
        "participants": [{"name": p[0], "role": p[1], "is_me": len(p) > 2 and p[2]} for p in meeting["participants"]],
        "transcript": transcript,
        "summary": {
            "overview": meeting["summary"]["overview"],
            "decisions": meeting["summary"]["decisions"],
            "action_items": [{"owner": o, "task": t_, "due": d} for o, t_, d in meeting["summary"]["action_items"]],
            "open_questions": meeting["summary"]["open_questions"],
        },
        "my_thoughts": meeting["thoughts"],
        "audio_file": None,
    }


def main():
    if "--remove" in sys.argv:
        removed = 0
        for f in OUT.glob("*/*.json"):
            if json.loads(f.read_text()).get("sample"):
                f.unlink()
                removed += 1
        print(f"removed {removed} sample meetings")
        return
    for meeting in MEETINGS:
        stem, record = build(meeting)
        day = OUT / stem[:10]
        day.mkdir(parents=True, exist_ok=True)
        (day / f"{stem}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
        print(f"wrote {day.name}/{stem}.json ({record['duration_s'] / 60:.1f} min, {len(record['transcript'])} lines)")


if __name__ == "__main__":
    main()
