# Security policy

## Reporting a vulnerability

Please report security issues **privately** through GitHub's "Report a vulnerability" (Security tab → Advisories) on this repository, not in a public issue. Include steps to reproduce and the version or commit. You'll get a reply as soon as possible, and credit if you want it.

## What Mispr Flow promises

- **Nothing leaves your Mac.** Audio, text, meetings and commands are processed locally. The only network use is downloading the models once, over HTTPS, each checked against a pinned SHA-256 (`mispr/models.py`). There's no telemetry, analytics or update check.
- **Your data is private on disk.** Dictations, meetings, settings and the log are in owner-only folders (`700`), and the log never contains what you said. Incognito saves nothing.
- **Nothing acts on a guess.** Voice commands never launch an app on a weak match, and terminal mode never types a word you didn't say.

## Audits

The latest audit is in [`logs/*_security-audit.md`](logs/README.md): its method, findings, fixes, and what's needed for a signed, notarized release.

## Supported versions

Only the latest `main` gets security fixes until the first public release.
