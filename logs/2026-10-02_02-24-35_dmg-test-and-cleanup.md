# DMG install test, and build cleanup

**Test (by the owner):**
- Downloaded Mispr-Flow-1.0.0.dmg from the v1.0.0 release; its SHA-256 matched the README.
- Installed to /Applications and opened it with right-click → Open.
- Reset permissions (`tccutil reset All io.github.maxwelldalrymple.MisprFlow`) and deleted settings.json.
- Setup ran fresh: Microphone and Accessibility allowed, then models, then the tutorial. Everything worked.

**Problem found on the first try:** setup stuck on Accessibility.
- **Cause:** two more copies of the app, with the same bundle ID, were on disk from the build: `build/dmg-stage/` and `build/Mispr Flow.app`. macOS launched the staging copy, and the permission went to a different copy.
- **Effect:** none for DMG users, who only have one copy.
- **Fix:** `tools/build_dmg.sh` now deletes the staging copy and the development app after packaging. Run `tools/build_app.sh` again to get the development build.

**Tests:** script syntax check only. The change is cleanup after the DMG is written.
