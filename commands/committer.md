---
description: Update and stage the diary before a commit — picks LIGHTWEIGHT or FULL session-historian mode from what is staged and the shared review cadence. Does not commit. Run after tests pass.
---

Invoke the committer skill. Check what is staged, determine LIGHTWEIGHT or FULL session-historian mode (from the staged files and the `Last full review:` line plus git), update the diary, and stage diary changes. Do not commit; a plugin hook checks that diary/ is staged before `git commit` runs.
