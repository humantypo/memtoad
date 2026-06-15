---
name: session-historian
description: Document the current session's accomplishments, decisions, and lessons learned into the diary. Run inline (no agent spawn) at the end of a session or after significant work. Updates up to three files conditionally.
---

Run the following **inline in the main conversation** (do not spawn an agent — you already have full session context):

## What to update

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
- Most recent entries at the top in all three files
- Cross-references use `(→ slug-name)` notation, not numbers
- No archiving — files grow without rotation

## Commit discipline

Run session-historian *before* staging the commit, not after. The correct order:
1. Run tests
2. Run `/session-historian` — write diary entries
3. Stage `diary/` alongside the code changes
4. Commit everything together

Do not reference the commit hash in diary entries; it isn't known yet when session-historian runs. The git log is the authoritative record of what changed and when.
