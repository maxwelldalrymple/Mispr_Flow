# "open folder" finds folders reliably: Spotlight, sound-alikes, Full Disk Access

**Branch:** `speaker-id`

## User reports

- "Open Claude folder" opened nothing.
- Whisper wrote "clawed" / "claw to" for "Claude".
- "It can't find any of the folders."

## Findings

- The log shows "Open Claude Folder" was heard correctly at 17:59, yet nothing was found.
- The `claude` folder is in **~/Documents**. macOS blocks apps from Documents, Desktop and Downloads without permission. The app's folder walk hit that block, skipped the folder silently, and reported nothing.
- The same search from a terminal found it in 0.28 s.

## Changes

- **Spotlight first** (`mdfind -onlyin ~`): instant, any depth, exact names first, then sound-alikes. The shallowest match wins, folders before files, and hidden/Library/build folders are skipped. The level-by-level walk remains as the backup (Spotlight sometimes answers empty while busy).
- **Sound-alike names:** Soundex of the name with spaces removed. "clawed", "claw to" and "Claude" are all C430. Used only when no exact name matches, and never for names under 4 letters.
- **Locked folders** are now logged ("no permission to look in …") instead of being skipped silently.
- **Permission, as the user asked:** setup has an optional **Full Disk Access** row.
  - Allow… opens Privacy & Security → Full Disk Access, since macOS has no prompt for it.
  - The status check reads the protected TCC database, which never prompts.
  - It replaced a per-folder approach.
- **Setup window:** 520 → 600 px tall, with shorter descriptions, so all five rows fit. Checked on the regenerated screenshots.

On this Mac:
- "claude" → `~/documents/software-projects/claude` (0.18 s)
- "claud" → same (0.22 s)
- "clawed" → same (sound-alike)
- "downloads" → `~/downloads` (0.13 s)

## Tests

The full Python suite ran: **1198 passed, 10 skipped**.

New:
- sound codes, including split words;
- an exact name beats a sound-alike;
- Spotlight: exact then sound-alike, shallowest, hidden skipped, off or failing gives None;
- the Full Disk Access check (readable, locked, missing);
- the setup row;
- permission lists updated;
- golden screenshots regenerated and checked.
