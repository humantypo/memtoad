---
name: session-historian
description: Document the current session's accomplishments, decisions, and lessons learned into the diary. Run inline (no agent spawn) at the end of a session or after significant work. Updates up to three files conditionally; with enhanced memory on, also archives and digests each new entry in the memstore.
---

Run the following **inline in the main conversation** (do not spawn an agent — you already have full session context):

## Modes

**FULL** (default when invoked directly): Update all three diary files as appropriate. Used after sessions with code changes, new decisions, or significant work.

**LIGHTWEIGHT** (invoked by `/committer` for documentation-only commits): Update only `diary/session_context.md`. Append to `diary/lessons_learned.md` only if something genuinely non-obvious was learned. Do not touch `diary/architectural_decisions.md`.

When invoked directly via `/session-historian`, always run FULL. The `/committer` skill decides which mode to use based on what's staged.

## What to update (FULL mode)

**Always**: Rewrite `diary/session_context.md` with the current state:
- Date and project version/status
- What was done in this session (WHY-focused narrative, not a per-file change list)
- Open items for future work
- Links to the other two diary files

**Only if a new architectural decision was made**: Append to `diary/architectural_decisions.md`:
- A `## slug-based-header (Month YYYY)`
- One-sentence statement of the decision
- WHY: the constraint, tradeoff, or failure mode that drove the decision
- Optional: a brief code snippet only if it makes the WHY clearer

**Only if a new anti-pattern or hard-won lesson was learned**: Append to `diary/lessons_learned.md`:
- A `## slug-based-header (Month YYYY)`
- **Rule**: one-sentence actionable takeaway
- **Why**: what happened, what it cost, why the lesson isn't obvious
- Optional: brief code snippet only if it illustrates the lesson

## What NOT to write

- Per-file change lists ("file A modified at line N to add param Y")
- Code snippets unless they illustrate a lesson or decision
- "Status: COMPLETE" announcements
- Verification steps ("tests pass", "build green")
- Anything already in git history (commit hashes, file paths of changes)

## Format rules

- `session_context.md`: lean prose sections — Current State, Most Recent Sessions, Open Items, Key Diary Files
- Most recent entries at the top in all three files (with enhanced memory: new full entries go directly below the digest region, see below)
- Cross-references use `(→ slug-name)` notation, not numbers
- Nothing is archived out of reach: without the store the files grow without rotation; with it, every entry stays one pointer away

## With enhanced memory (`CLAUDE.md` contains `<!-- memtoad:store -->`)

`diary/architectural_decisions.md` and `diary/lessons_learned.md` are an **Index** plus one-paragraph **digests** inside a marked region at the top (`<!-- memstore:digests:start -->` ... `<!-- memstore:digests:end -->`); the full text of every entry lives in the tracked store `diary/memstore/`. Use the memstore command named in CLAUDE.md's `<!-- memtoad:store -->` block (written `memstore` below). After deciding what to record, in order:

1. **Place each new decision/lesson as a full entry directly below `<!-- memstore:digests:end -->`**, never inside the region. Heading: `## kebab-slug (Month D, YYYY)`. The slug must be new (ingest fails on a collision).
2. **Archive:** `memstore ingest diary`.
3. **Digest:** for each new entry write a one-paragraph digest in the style below, save `{"<slug>": "<digest>"}` as JSON in a temporary location (not in the repository), run `memstore compact <architectural_decisions|lessons_learned> --digests FILE --dry-run`, then without `--dry-run`. This replaces the entry with its digest and rebuilds the Index. You have the session context, so write the digests yourself; do not delegate them to a cheaper model (one tested this way dropped the key rule of the entry that mattered most).
4. **Check and proofread:** `memstore check-pointers` must report 0 errors. Read its warnings: they list names or numbers a digest has that its entry lacks. Proofread each digest against its full entry (`memstore get <pointer>`) before anything is staged.
5. Leave `diary/memstore/` for the committer's `git add diary/`.
6. If the memstore command or chromadb is unavailable, leave the full entries in the file, say so plainly, and do not invent a fallback. `diary/session_context.md` is not part of this and is written as before.

**Digest style.** One line, one paragraph, no heading, no `mem:` (the tool appends the pointer); usually 300–600 characters, up to about 800 for large entries:

`**Title (Mon D, YYYY), active.** <rule in operative form, with the exact names to find it: functions, files, flags, tables, commands> <one-clause reason> <prohibitions that are the point>.`

- Keep, in order: the operative rule; the names; a one-clause reason; explicit prohibitions. Drop narrative, evidence tables, file lists, worked examples, commit hashes.
- State fail-fast, no-fallback, approval-gate and data-integrity rules as strongly as the entry does.
- Write the status word "active" only if the entry says it is in force **and** a quick grep shows the code it names still exists; if unsure, omit it.
- A reference to something removed or superseded gets one clause at most.
- Never invent a name, number or date.

Do not reference the commit hash in diary entries; it isn't known until after the commit. The git log is the authoritative record of what changed and when. Use `/committer` to handle the diary update and commit atomically.
