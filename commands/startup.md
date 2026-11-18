---
description: Load full project context at session start — architecture, decisions, current state
---

Run the memtoad `startup` skill. If `CLAUDE.md` contains `<!-- memtoad:store -->` (enhanced memory), it runs inline and reads the diary Indexes with the memstore command named there, not the whole files. Otherwise use the Agent tool to spawn the `startup` subagent with this prompt:

"Load full project context. Read diary/architectural_decisions.md, diary/lessons_learned.md, and diary/session_context.md in order. An entry whose heading's date parenthetical says `superseded by <slug>` or `retired <Mon YYYY>: <reason>` is no longer in force: treat it as history and what did not work, never as a current rule. Synthesize the current state, active priorities, and any open questions, then report a concise briefing."
