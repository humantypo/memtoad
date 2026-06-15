# Architectural Decisions

Design principles and the reasoning behind non-obvious choices. Add an entry when a future
engineer would reasonably ask "why did they do it this way?" — and the answer isn't obvious
from the code.

Most recent decisions at top. No archiving.

---

## grill-me-reads-diary-first (June 2026)

The grill-me skill reads all three diary files before asking its first question.

**Why**: The interrogation is only useful if it's grounded in current project constraints. Without Phase 0, grill-me might spend cycles on questions the diary already answers ("how will you handle X?") or miss opportunities to surface "we already decided this" before the user re-litigates a closed decision. The diary read is cheap; the rework from an uninformed interview is not. This is the key integration point between session-historian (which writes the diary) and grill-me (which reads it).

---

## session-historian-inline-not-spawned (June 2026)

Session-historian runs inline in the main conversation rather than as a spawned subagent.

**Why**: The main conversation at session end already has full context — every decision, every change, every discovery made during the session. Spawning a subagent to document it would require re-deriving that context from cold, which is expensive and lossy. The historian is a writing task, not a research task; it does not need its own context window. Startup spawns because it genuinely starts cold. Session-historian does not.

---

## three-files-no-archiving (June 2026)

The diary is permanently three files. Files grow without bound; old content is never archived or rotated.

**Why**: The system this replaced (in the original project) grew to 35 files and 1.8MB through unbounded archiving triggered by file-length thresholds. The startup skill loaded only 3 of those 35 files, meaning the archive accumulated content that was never read. Modern context windows make file-length rotation obsolete. The value of the diary is always in three things: current state, design decisions, hard-won lessons — which map directly to three files. A fourth file is never justified.
