# focus-guard

Locks the PC at login or morning after a focus-project day that missed its minutes. The lock lifts as soon as today's minutes reach the project's unlock number; earn them on the phone.

- Rule and invariants: `CLAUDE.md`.
- Install as kuhy, never sudo: `./install.sh`.
- Verdict without locking: `python3 -m focus_guard status`.
