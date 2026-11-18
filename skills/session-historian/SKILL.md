---
name: session-historian
description: Document the current session's accomplishments, decisions, and lessons learned into the diary. Run inline (no agent spawn) at the end of a session or after significant work. Updates up to three files conditionally, labels entries a new one supersedes, and keeps the session log to active work; with enhanced memory on, also archives and digests each new entry in the memstore.
---

Run the following **inline in the main conversation** (do not spawn an agent — you already have full session context):

## Modes

**FULL** (default when invoked directly): Update all three diary files as appropriate. Used after sessions with code changes, new decisions, or significant work.

**LIGHTWEIGHT** (invoked by `/committer` for documentation-only commits): Update only `diary/session_context.md`. Append to `diary/lessons_learned.md` only if something genuinely non-obvious was learned. Do not touch `diary/architectural_decisions.md`, with one exception: a decision promoted from a session note that is dropping off (see **The session log**). If it is worth writing, it is still relevant.

When invoked directly via `/session-historian`, always run FULL. The `/committer` skill decides which mode to use based on what's staged.

## What to update (FULL mode)

**Always**: Rewrite `diary/session_context.md` with the current state:
- Date and project version/status
- **Arc**: one line per milestone (a version or phase): what changed and why it mattered. Add a line only when this session completes a milestone. This, not the session log, is the record of where the project has been.
- What was done in this session (WHY-focused narrative, not a per-file change list), under the session log rule below
- Open items for future work
- Links to the other two diary files

**Always in FULL mode**: set the `Last full review: <Month D, YYYY>` line near the top of `diary/architectural_decisions.md` (above its first `---`) to today, adding it if missing. `/committer` reads this line to decide when the next FULL run is due; it is the only cadence state there is, shared through git.

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

**Every new decision or lesson: does it replace, retire or amend an existing entry?** Before writing it, read the other entries' headings (with enhanced memory, the Index) and ask that one question. Only an entry the new one actually changes counts, not one on a related topic.
- **Replaces it wholly:** say so in the new entry, e.g. `This reverses (→ old-slug).`, and label the old one `superseded by <new-slug>`. A lesson can be superseded by a decision and the other way round.
- **Something stopped applying with nothing replacing it** (the code it governs was removed, say): label it `retired <Mon YYYY>: <one-clause reason>`.
- **Replaces only part of it** (one mechanism changes, the rest still holds): write `This amends (→ old-slug).` in the new entry, and make the smallest correction to the old entry so it is true again. No label: it is still in force. With enhanced memory a digested entry's correction goes in its digest text; its archived original stays as written.
- Labelling never removes text. Show the user each label and correction you apply in your report.

## The session log

"Most Recent Sessions" is context on the work in progress, not a history: git and the other two files hold what lasts. It keeps:
- the current session and the one before it, counted **by date**: a second run on the same day updates that day's note in place, never adds another heading;
- any older note whose work is still in flight (better still, move the in-flight part to Open Items and drop the note).

Before a note drops off, check it for anything durable. A decision or lesson goes into its file (allowed even in LIGHTWEIGHT); unfinished work goes into Open Items. If `git ls-files --error-unmatch diary/session_context.md` fails (the file is untracked, as in hybrid and private mode), the dropped notes exist nowhere else: list them to the user, one line each, before rewriting the file.

## What NOT to write

- Per-file change lists ("file A modified at line N to add param Y")
- Code snippets unless they illustrate a lesson or decision
- "Status: COMPLETE" announcements
- Verification steps ("tests pass", "build green")
- Anything already in git history (commit hashes, file paths of changes)

## Format rules

- `session_context.md`: lean prose sections — Current State, Most Recent Sessions, Open Items, Key Diary Files
- `session_context.md` sections, in order: Arc, Current State, Most Recent Sessions, Open Items, Key Diary Files
- Most recent entries at the top in all three files (with enhanced memory: new full entries go directly below the digest region, see below)
- Cross-references use `(→ slug-name)` notation, not numbers
- **Labels** go inside the date parenthetical, exactly: `## old-slug (June 2026; superseded by new-slug)` or `## old-slug (June 2026; retired Nov 2026: the install scripts were removed)`. The reason is one clause with no parentheses. An unlabelled entry is in force; there is no `active` label.
- Nothing is archived out of reach or deleted: without the store the files grow without rotation; with it, every entry stays one pointer away, and a labelled entry keeps all its text

## With enhanced memory (`CLAUDE.md` contains `<!-- memtoad:store -->`)

`diary/architectural_decisions.md` and `diary/lessons_learned.md` are an **Index** plus one-paragraph **digests** inside a marked region at the top (`<!-- memstore:digests:start -->` ... `<!-- memstore:digests:end -->`); the full text of every entry lives in the tracked store `diary/memstore/`. Use the memstore command named in CLAUDE.md's `<!-- memtoad:store -->` block (written `memstore` below). After deciding what to record, in order:

1. **Place each new decision/lesson as a full entry directly below `<!-- memstore:digests:end -->`**, never inside the region. Heading: `## kebab-slug (Month D, YYYY)`. The slug must be new (ingest fails on a collision). Settle the heading before step 2: once an entry is ingested, never rename or delete it, because its archived copy would be left with no digest. If that happens anyway, `check-pointers` reports it; `memstore restore <pointer>` puts the archived text back, and you compact it with a digest labelled `superseded by <new-slug>` (a rename) or `retired <Mon YYYY>: written in error`.
2. **Archive:** `memstore ingest diary`.
3. **Digest:** for each new entry write a one-paragraph digest in the style below, save `{"<slug>": "<digest>"}` as JSON in a temporary location (not in the repository), run `memstore compact <architectural_decisions|lessons_learned> --digests FILE --dry-run`, then without `--dry-run`. This replaces the entry with its digest and rebuilds the Index. You have the session context, so write the digests yourself; do not delegate them to a cheaper model (one tested this way dropped the key rule of the entry that mattered most).
4. **Label what the new entries supersede:** for a digested entry, `memstore set-label mem:diary/<file>#<old-slug> --superseded-by <new-slug>` (or `--retired "Nov 2026: <reason>"`), which edits its lead and moves it to the Index's "No longer in force" list. A full entry below the region is labelled by editing its heading. Never fold or delete a digest: its archived entry would then have no digest, and `check-pointers` reports that as an error.
5. **Check and proofread:** `memstore check-pointers` must report 0 errors. Read its warnings: they list names or numbers a digest has that its entry lacks. Proofread each digest against its full entry (`memstore get <pointer>`) before anything is staged.
6. Leave `diary/memstore/` for the committer's `git add diary/`.
7. If the memstore command or chromadb is unavailable, leave the full entries in the file, say so plainly, and do not invent a fallback. `diary/session_context.md` is not part of this and is written as before.

**Digest style.** One line, one paragraph, no heading, no `mem:` (the tool appends the pointer); usually 300–600 characters, up to about 800 for large entries:

`**Title (Mon D, YYYY).** <rule in operative form, with the exact names to find it: functions, files, flags, tables, commands> <one-clause reason> <prohibitions that are the point>.`

- Keep, in order: the operative rule; the names; a one-clause reason; explicit prohibitions. Drop narrative, evidence tables, file lists, worked examples, commit hashes.
- State fail-fast, no-fallback, approval-gate and data-integrity rules as strongly as the entry does.
- Do not write a status word. A digest is in force unless its lead carries a label, which goes inside the date parenthetical, as in `**Title (Mon D, YYYY; superseded by new-slug).**`; use `set-label` rather than writing one by hand. When the entry being digested already carries a label in its heading, copy that label into the lead's parenthetical unchanged, so compaction never puts a superseded entry back in force.
- A reference to something removed or superseded gets one clause at most.
- Never invent a name, number or date.

Do not reference the commit hash in diary entries; it isn't known until after the commit. The git log is the authoritative record of what changed and when. Use `/committer` to handle the diary update and commit atomically.
