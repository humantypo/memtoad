---
description: Document session accomplishments, decisions, and lessons to diary (runs inline)
---

Run the session-historian skill inline. Do not spawn an agent. You already have full session context.

Review what was accomplished this session. Then:
- Always rewrite diary/session_context.md with the current state; keep its session log to the current session and the one before it (by date), and update the Arc when a milestone is completed.
- Only if a new architectural decision was made: append to diary/architectural_decisions.md, and set its `Last full review:` line to today.
- Only if a new lesson was learned: append to diary/lessons_learned.md.
- For each new entry, label any existing entry it supersedes or retires.
- If `CLAUDE.md` contains `<!-- memtoad:store -->`, follow the skill's enhanced-memory steps: new entries go below the digest region, then ingest, digest, compact, set-label and check-pointers.
