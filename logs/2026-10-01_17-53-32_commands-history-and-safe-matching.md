# Voice commands: history tab, and never opening the wrong app

**Branch:** `speaker-id`

## User reports

1. Voice commands weren't saved in history.
2. They should have their own "Commands" history tab.
3. Saying "Chrome" opened Logic Pro.

## Findings and fixes

**1–2. History.**
- Commands were wiped by design and never saved.
- Now each one is saved with what was said (never in Incognito), with a new status `command`.
- Home history has **Dictation | Commands** tabs. Commands carry a "Voice command" tag and have their own empty state and search.
- Commands are left out of word counts and speed (`Status.isDictation`).

**3. Wrong app.**
- The log shows Whisper heard only **"Pro."** (the start of "Chrome" was clipped).
- Matching took "pro" as a word of "Logic Pro" and launched it.
- New `match_scored` rules:
  - **Strong** (may open an app that isn't running): a nickname, the exact name, the name without spaces, or one distinctive word of 5+ letters ("chrome", "logic").
  - **Weak** (only switches to apps already open): a short word ("code"), a prefix ("term"), or a sound-alike ("sapari").
  - **Never matches:** generic name words ("pro", "app", "studio", "desktop", "mac"…), even when such an app is open.
  - **Shared words:** the app where the word is clearly the bigger part of the name wins ("Google Chrome" over "Chrome Remote Desktop"). Otherwise only an open app counts, or nothing.
  - Sound-alike cutoff raised from 0.75 to 0.82.
- A weak guess at an app that isn't running opens nothing and shows "Not sure you meant Logic Pro: say its full name".

## Tests

All passed:
- `pytest tests/test_apps.py tests/test_widget.py`
- `swift test --filter 'RenderTests|CommandHistoryTests'`: 21 tests, 0 failures

New:
- `TestConfidentMatching` (9): "pro" never matches, even with Logic Pro open; strong/weak for chrome, logic, face time, code, term, sapari; "crome" gives nothing.
- Widget:
  - "Pro." opens nothing;
  - a prefix of an open app switches;
  - a guess at a closed app asks for the full name;
  - commands go into history, but not empty ones and not in Incognito.
- Swift: commands decode and stay out of stats; the Commands tab splits records correctly and renders its empty state.
