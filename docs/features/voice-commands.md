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
- Every phrase is also listed on the app's **Voice Commands** page, which can be searched.

## Click anything

Buttons, links, fields, tabs, menu items and labeled pictures in **any app**, by the words on them. They're read from the app itself (the macOS Accessibility API), not from a screenshot. Chrome and Electron apps are asked to report their web pages. A full Chrome page scans in about 0.15 s.

| Say | Does |
|---|---|
| "click Sign in" / "click the search box" / "press Pricing" | Moves the mouse there and clicks |
| "double click Budget" / "right click the logo" | Double-click / right-click it |
| "click" | Clicks where the mouse is |
| "move the mouse to Pricing" / "hover over Pricing" | Points without clicking |
| "show numbers", then "7" (or "click seven") | A blue number on everything clickable; say one |
| "never mind" | Hides the numbers |
| "show grid", then "5", "5", "click" | A 3×3 grid: each number zooms in, "click" clicks its middle (for spots with no name) |
| "drag Budget to the Trash" | Drags one thing onto another |
| "scroll the sidebar down" | Scrolls a named part of the window |

- **The closest name wins** when nothing matches exactly: "opus" finds "Opus 4.6", "pref" finds "Preferences", "fable five" finds "Fable 5.1", "thru setup" finds "Walk through setup". It compares word by word (exact, prefix, spelling, sound), and numbers must match.
- **Several matches** (or a close tie) get numbers instead of a guess. Text inside a link counts as the link.
- Not on screen? "click Export" tries the app's menus next.

## Keyboard and typing

| Say | Does |
|---|---|
| "press enter" / "press escape" / "press tab" / "press delete" / "press space" | That key |
| "press command shift t" / "press option left" | Any shortcut: command, shift, option, control + a key |
| "press tab 3 times" / "down 3" / "left five" | Repeated keys and arrows |
| "type hello@example.com" | Types exactly what you said (no cleanup; Whisper's closing period dropped) |
| "select all" / "copy" / "cut" / "paste" / "undo" / "redo" / "save" / "print" | ⌘A ⌘C ⌘X ⌘V ⌘Z ⇧⌘Z ⌘S ⌘P, in any app |

## Editing text

"That" is your last dictation.

| Say | Does |
|---|---|
| "scratch that" / "delete that" | Deletes it |
| "select that" | Selects it |
| "capitalize that" / "uppercase that" / "lowercase that" | Retypes it |
| "new line" / "new paragraph" | ⇧Return once / twice (doesn't send in chat apps) |
| "delete last word" / "delete line" | ⌥⌫ / ⌘⌫ |
| "select last word" / "select next word" / "select line" | |
| "go to end of line" / "start of line" / "end of document" / "next word" | |

## Window layout and desktops

| Say | Does |
|---|---|
| "left half" / "right half" / "top half" / "bottom half" | Snaps the window in front |
| "left third" / "right two thirds" / "middle third" | Thirds |
| "top left corner" / "move to bottom right" | Quarters ("corner" or "move to" is needed: plain "top left" means "tab left") |
| "center" | Centered at 70% |
| "move to the other screen" | To your next display |
| "mission control" / "show desktop" / "app windows" | Mission Control views |
| "next desktop" / "previous desktop" | ⌃→ / ⌃← |
| "desktop 2" | ⌃2: turn on "Switch to Desktop 2" in Keyboard Shortcuts › Mission Control |

## Switches

| Say | Does |
|---|---|
| "dark mode on" / "light mode" / "dark mode" | Appearance (asks once to control System Events) |
| "brightness up" / "dimmer" | The display brightness keys |
| "wifi off" / "turn on wi-fi" / "wifi" | Wi-Fi (`networksetup`) |
| "use AirPods" / "play through the speakers" | Sound output, by closest name. Not an output? It switches to that app |
| "control center" / "notification center" / "launchpad" / "spotlight budget" | Opens them |
| "auto enter on" / "incognito mode" / "sounds off" | Mispr Flow's own modes (no on/off: flip) |

Bluetooth and Do Not Disturb have no built-in switch an app can use: make a Shortcut and say "run shortcut …".

## The web

| Say | Does |
|---|---|
| "google best pizza near me" | A Google search in the browser in front |
| "search youtube for lofi beats" | Also Amazon, Wikipedia, GitHub, Reddit, Maps, Images, Bing, DuckDuckGo |
| "go to apple.com" / "go to news dot ycombinator dot com" | Opens the site ("dot" needed for .app, .tv, .co…) |
| "find pricing on the page" | ⌘F and types it |

## Power tools

| Say | Does |
|---|---|
| "run shortcut Morning" / "run my Morning shortcut" | Runs a shortcut from the Shortcuts app (closest name) |
| "again" / "do that 3 times" | Repeats the last command |
| Your own phrases | **Settings → General → Your own commands**: a phrase that types text and then presses keys ("sign off" → "Best, Alex"; "send it" → cmd enter) |

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

Add "in Chrome" (or say "Chrome new tab") to bring that app forward first. "close tab" also works when Whisper hears "Closed tab." or "Tab, close."

### A tab by its site

| Say | Does |
|---|---|
| "GitHub tab" / "go to the YouTube tab" | Selects the first tab on that site, in the browser in front (else the first running browser that has one) |
| "YouTube tab 2" | The second YouTube tab (windows front to back, tabs left to right) |
| "Chrome tab 3" | A browser's name: its tab 3 (⌘3) |
| A site with no tab open ("Reddit tab") | Opens it in a new tab |

- **Misheard names are assumed:** "chat gbt tab", "get up tab", "net flicks tab" and "you two tab" find ChatGPT, GitHub, Netflix and YouTube. Names are matched against the open tabs' addresses and titles, then against the 1,000 most visited sites (`mispr/assets/sites.txt`), by sound and spelling. Ordinary words don't match a site.
- **Browsers:** Chrome, Safari, Arc, Brave, Edge, Vivaldi, Opera. The first time, macOS asks to let Mispr Flow control the browser (it lists the tabs). Firefox can't be scripted.

## Your Mac

| Say | Does |
|---|---|
| "screenshot" / "take a screenshot" | ⌘⇧3: the whole screen, saved where your screenshots go |
| "screenshot area" / "screenshot of the window" | ⌘⇧4: drag an area, or click a window |
| "screen recording" / "record my screen" | Starts recording the screen (needs Screen Recording permission; otherwise the capture toolbar opens) |
| "stop recording" | Saves the movie next to your screenshots |
| "sleep" / "go to sleep" | Puts the Mac to sleep |
| "lock screen" | Locks it (⌃⌘Q) |
| "log out" / "restart" / "shut down" | Asks macOS, which shows its usual confirmation first: a misheard word can never turn your Mac off |

## Menus of the app in front

Any menu item, by name: "save", "undo", "show sidebar", "new folder", "click export", or with its menu, "file new window". A word that isn't an app is tried as a menu item before "No app called …". The app's name can be left out ("new window" for "New Finder Window").

Items that delete for good (Empty Trash, Erase, Delete Immediately, Force Quit, Clear History) are never pressed by voice. "move to trash" works, since it can be undone.

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
