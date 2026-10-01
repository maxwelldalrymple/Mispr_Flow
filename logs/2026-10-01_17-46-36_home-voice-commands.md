# Home: Voice commands card

**Branch:** `speaker-id`

A "Voice commands" card under Shortcuts on Home lists the computer-control commands in three groups: Apps & windows, Tabs & pages, Sound. It shows "Hold <your key>, say it, let go." If no switcher key is set yet, it explains that and links to Settings → General instead.

## Tests

`swift test --filter RenderTests`: 19 tests, 0 failures. New: `testHomeVoiceCommandsCardWithAndWithoutASwitchKey` renders both states and checks the groups.
