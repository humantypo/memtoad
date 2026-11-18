---
name: startup
description: Load full project context at the start of a session — reads architectural decisions, current implementation state, and session context to establish a complete picture before beginning work. With enhanced memory on, reads the diary Indexes instead of the whole files, inline.
---

First check whether the project uses enhanced memory: `CLAUDE.md` contains `<!-- memtoad:store -->`.

## Without enhanced memory (the default)

Use the Agent tool to spawn the `startup` subagent with this prompt:

"Load full project context. Read diary/architectural_decisions.md, diary/lessons_learned.md, and diary/session_context.md in order. An entry whose heading's date parenthetical says `superseded by <slug>` or `retired <Mon YYYY>: <reason>` is no longer in force: treat it as history and what did not work, never as a current rule. Synthesize the current state, active priorities, and any open questions, then report a concise briefing."

## With enhanced memory

The two big diary files are an **Index** plus one-paragraph digests, with the full text of every entry in the tracked store `diary/memstore/`, so reading them whole defeats the point. Run **inline** (no agent), using the memstore command named in CLAUDE.md's `<!-- memtoad:store -->` block (written `memstore` below):

1. `memstore index` prints both Indexes (one line per decision and per lesson, newest first) and lists any full entries that are not yet compacted. Lines under "No longer in force" are superseded or retired: history and what did not work, never current rules. If it prints a NOTICE that the Indexes are over budget, pass that on in one line and suggest `/tidy`; do nothing else about it.
2. Read `diary/session_context.md` in full: it is the current state and is never compacted.
3. Read in full any entry the index command marked `[FULL]`: those are the newest, not yet digested, and sit below the digest region of the named file.
4. Do **not** read the Digests region up front. When an Index line matters to the user's task, read that digest paragraph from the file (same order as the Index, ending in a `mem:` pointer) or the exact original with `memstore get <pointer>`. For a topic you cannot place, `memstore search "<query>"`.
5. Report a concise briefing: current state, active priorities, open questions, the Index topics that bear on what the user said they are about to do, and how much was loaded.

If the memstore command fails, say so plainly and stop to ask; do not fall back to guessing what the diary contains, and do not read the whole files instead without saying so.
