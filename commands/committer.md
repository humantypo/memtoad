---
description: Update diary and commit staged changes atomically — handles LIGHTWEIGHT vs FULL session-historian automatically based on what is staged. Run after tests pass.
---

Invoke the committer skill. Check what is staged, determine LIGHTWEIGHT or FULL session-historian mode, update the diary, stage diary changes, confirm the final file list, then commit.
