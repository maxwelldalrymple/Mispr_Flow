# Voice commands (app switcher)

Control your Mac by voice.

1. Pick an **app switcher key** in Settings → General. It can be:
   - a key (F5);
   - one side of a modifier (Right ⌥);
   - a combo of modifiers held together (⌃⌥);
   - modifiers plus a key (⌥S).
2. Hold it and say a command.
3. Let go.

The widget confirms what happened ("→ Google Chrome", "Volume 55%"). The command, with the real names, is saved in Home → **Commands** history (not in Incognito).

**Rules for every command:**
- With no app named, a command acts on **the app you're in**.
- Words like "please", "go", "open" in front are ignored.
- Numbers can be spoken ("eighty percent").

## Apps and windows

| Say | Does |
|---|---|
| "Chrome", "open the terminal", "switch to Slack" | Brings the app to the front (launches it if needed) |
| "close" / "close Chrome" | Closes the front window (doesn't quit) |
| "minimize" / "hide" | Minimizes the front window |
| "expand" / "maximize" | Fills the screen (menu bar and Dock stay) |
| "quit" / "quit Slack" / "exit" | Quits the app normally (it can still warn about unsaved work) |
| "Chrome beside VS Code" (also "put … next to …", "window layout …") | Side by side, half each; the first app named ends up in front |
| "Chrome 70% beside VS Code" | Chrome 70% of the width, VS Code the rest |
| "Chrome 80%" / "make Slack sixty percent" | That share of the screen's width and height, centred |
| "set nickname C to Chrome" | From then on, "C" means Chrome. Nicknames can also be managed in Settings → General |

**Never opening the wrong app.** A whisper of "Pro." once opened Logic Pro; now:
- **Strong matches may launch an app that isn't running:** a nickname, the exact name, the name without spaces ("face time"), or one distinctive word of 5+ letters ("chrome").
- **Weak matches only switch to apps already open:** a short word ("code"), a prefix ("term"), or a sound-alike ("sapari").
- **Generic words never match:** "pro", "app", "studio", "desktop", "mac"…
- **Shared words:** "chrome" means Google Chrome over Chrome Remote Desktop. A real toss-up does nothing.

## Tabs and pages (the app's own shortcuts)

| Say | Shortcut |
|---|---|
| new tab / close tab / reopen tab | ⌘T / ⌘W / ⇧⌘T |
| next tab / previous tab (also "tab right" / "tab left") | ⌃⇥ / ⌃⇧⇥ |
| tab 3 ("tab three"), tab 1–8 / tab 9 or last tab | ⌘3 / ⌘9 |
| move tab left / move tab right | ⌃⇧PgUp / ⌃⇧PgDn |
| next window / previous window | ⌘\` / ⌘⇧\` |
| new window / close window / incognito (private) window | ⌘N / ⇧⌘W / ⇧⌘N |
| reload ("refresh") / back / forward | ⌘R / ⌘[ / ⌘] |
| address bar / find / bookmark | ⌘L / ⌘F / ⌘D |
| zoom in / zoom out / reset zoom / full screen | ⌘= / ⌘- / ⌘0 / ⌃⌘F |

Add "in Chrome" (or say "Chrome new tab") to bring that app forward first.

| Say | Does |
|---|---|
| "window 2" / "go to window one in Chrome" | Brings that window of the app forward. Windows are numbered left to right, then top to bottom, so with two side by side the left one is window 1 |
| "tabs side by side" / "split tab" / "split view" | Uses Chrome's own split view if it has one; otherwise moves the tab into its own window and puts the two windows side by side |

## Sound and media

| Say | Does |
|---|---|
| "pause" / "play" / "next song" / "previous track" | Media keys: whatever is playing |
| "skip forward 30 seconds" / "rewind 10 seconds" / "jump ahead 2 minutes" | Arrow keys, one press per 5 s (YouTube, web players, QuickTime) |
| "volume up" / "louder" / "volume down" / "volume 40%" | Output volume |
| "mute" / "unmute" | The Mac's sound |
| "mute mic" / "unmute mic" | Input volume to 0 and back. While muted, holding the switch key opens the mic just to hear you, so "unmute mic" works by voice |
| "mute tab" / "unmute tab" | Chrome, Brave, Edge, Arc: the tab menu's "Mute site". Directional, never toggles back |
| "mute Spotify" | In a browser it mutes the tab. macOS can't mute one app without extra audio software, so elsewhere it says so |

## Scrolling

| Say | Does |
|---|---|
| "scroll down" / "scroll up" | About half a screen, under the pointer |
| "… a little" / "… more" / "… a lot" / "… 3 times" | Less, more, repeat |
| "page down" / "page up" | About a screen |
| "scroll to the top" / "scroll to the bottom" | ⌘↑ / ⌘↓ |

## Folders and files

| Say | Does |
|---|---|
| "open folder Projects" / "open the Downloads folder" | Finds it under your home folder and opens it in Finder; the highest-level match wins if there are duplicates |
| In Finder: "open Taxes" | A folder inside the one you're viewing opens **in the same window** |
| In Finder: "open Budget" | A file inside it opens in its app (no need to say ".xlsx") |
| In Finder, nothing matches | "“receipts” can't be found in Docs" (or, if it's clearly an app, switches to it) |

**How folders are found:**
- Spotlight first (instant, any depth), then a level-by-level search as a backup.
- Names are loose: "mispr flow" finds `Mispr_Flow`.
- Sound-alikes count when nothing has the exact name: "clawed" / "claw to" → `claude` (Soundex).
- Hidden folders, Library and build/dependency folders are skipped.

**Permissions** (setup's **Optional features** page):
- **Full Disk Access**, so Documents, Desktop and Downloads can be searched.
- **Control Finder**, for same-window navigation.

Code: `mispr/apps.py` (parsing, matching, actions), `mispr/hotkey.py` (the switch key), `mispr/widget.py` (`switch_key`, `_do_switch_command`).
