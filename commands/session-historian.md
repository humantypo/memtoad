---
description: Document session accomplishments, decisions, and lessons to diary (runs inline)
---

Run the session-historian skill inline. Do not spawn an agent. You already have full session context.

Review what was accomplished this session. Then:
- Always rewrite diary/session_context.md with the current state.
- Only if a new architectural decision was made: append to diary/architectural_decisions.md.
- Only if a new lesson was learned: append to diary/lessons_learned.md.
- If `CLAUDE.md` contains `<!-- memtoad:store -->`, follow the skill's enhanced-memory steps: new entries go below the digest region, then ingest, digest, compact and check-pointers.
