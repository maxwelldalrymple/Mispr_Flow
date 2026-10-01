# Setup and permissions

A setup window appears on first launch, and again whenever something required is missing. Reopen it from the menu bar: **Setup Guide…**

1. **Welcome**
2. **Allow access** (required): **Microphone**, **Accessibility** (captures the dictation key, pastes, reads the browser URL)
3. **Optional features** (skippable):
   - **Screen & System Audio:** meeting notes hear the other people on a call.
   - **Full Disk Access:** "open folder" can search Documents, Desktop and Downloads. macOS has no prompt for this one, so Allow… opens the System Settings list; switch Mispr Flow on there.
   - **Control Finder:** "open …" in Finder opens folders in the same window. This is macOS's Automation prompt.
4. **Models:** downloads Whisper turbo (0.57 GB) and Gemma (2.5 GB) with SHA-256 checks.
5. **Ready**

Meeting-only models (`base.en`, TitaNet, Silero) download the first time you take meeting notes.

**How permissions are checked without nagging:**
- The window re-checks permissions on a timer without triggering prompts. Finder uses `AEDeterminePermissionToAutomateTarget` without asking; Full Disk Access reads the protected TCC database.
- Only clicking **Allow…** asks.

**Keeping permissions across rebuilds:** the app is signed with a local certificate, "Mispr Flow Local Signing" (`tools/make_signing_cert.sh`, made trusted with `tools/trust_signing_cert.sh`). If permissions keep resetting, see [troubleshooting](../troubleshooting.md).
