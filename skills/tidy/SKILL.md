---
name: tidy
description: Consolidate superseded entries in diary/architectural_decisions.md — when a later entry reverses an earlier one, fold the pair into a single current entry in place. Never deletes reasoning, never archives, never touches lessons_learned.md or session_context.md. Run on demand, not automatically.
---

Run the following steps **inline in the main conversation**. Never spawn an agent — the target file is small by design and the merge decisions benefit from being visible to the user as they happen.

`tidy` exists because `architectural_decisions.md` and `lessons_learned.md` are deliberately append-only (→ three-files-no-archiving, → archive-files-are-never-read) — archiving by date or size was tried once and rejected because archived content stops being read. `tidy` does not archive anything and does not shorten the file by removing content. It only merges an explicit two-entry supersession into one entry, so a reader sees the current decision once instead of twice.

## Step 1 — Find candidate pairs

Read `diary/architectural_decisions.md`. Find every entry whose body contains `This reverses (→ some-slug)`. For each hit, locate the entry headed `## some-slug (...)` earlier in the file. That's a candidate pair: a reversal entry (newer) and the entry it reverses (older).

## Step 2 — Filter to safe pairs

Skip a candidate pair if either is true:

- The older slug is referenced by `(→ slug)` anywhere else in the file, in an entry that is not the reversal itself. That means other entries depend on the reader being able to find it as a standalone entry — merging would strand that context.
- The older entry is itself a reversal of a still-older entry (a chain of 3+). Only merge the two most recent links once the chain has stopped growing; report longer chains to the user instead of guessing which links are safe to fold.

Only entries with the explicit `This reverses (→ slug)` phrase qualify. Do not merge entries just because they cover a related topic — `tidy` acts only on authored supersession language, never on inferred similarity.

## Step 3 — Draft the merge

For each safe pair, draft a single replacement entry:

```markdown
## newer-slug (Month YYYY, supersedes older-slug)

<the newer entry's decision statement, unchanged>

**Why**: <the newer entry's WHY, unchanged or lightly trimmed>. Originally (older Month YYYY) <one compressed sentence: what the older entry decided and the core reason it was reconsidered — drawn from the older entry's own WHY, not invented>.
```

Rules for the draft:

- The surviving header keeps the *newer* slug and date, with `, supersedes older-slug` appended in the parenthetical — this keeps the older slug present as literal, greppable text so any existing `(→ older-slug)` reference elsewhere in the repo (e.g. in `session_context.md`, which gets fully rewritten by the next `/session-historian` run anyway) still resolves to something.
- Keep the newer entry's decision statement and WHY as the operative content — that's what's actually true today.
- Compress the older entry down to one clause inside the merged WHY. Do not drop its reasoning entirely; the goal is one entry that tells the whole arc, not a shorter entry that tells half of it.
- Drop the now-redundant "This reverses (→ ...)" sentence — the parenthetical on the header already says that.

## Step 4 — Confirm before writing

Show the user every candidate pair as a before (both original entries) / after (the drafted merge) comparison. Ask which pairs to apply — default to "all", but let the user exclude any. Do not write anything until confirmed.

## Step 5 — Apply and report

For each confirmed pair, replace both original entries with the single merged entry, in the position the newer entry occupied. Leave everything else in the file untouched.

Do not stage or commit the change. Tell the user to review with `git diff diary/architectural_decisions.md` and commit through the normal flow (or `/committer`) — this is an editorial change to diary content, not a session-historian write, and deserves the same review any diary edit gets.

## What NOT to do

- Do not touch `diary/lessons_learned.md` — it has no authored "supersedes" convention today. If one emerges later, that's a separate decision, not something `tidy` should infer on its own.
- Do not touch `diary/session_context.md` — it already self-tidies by being fully rewritten each session.
- Do not merge based on topic, staleness, or entry age — only on explicit `This reverses (→ slug)` language.
- Do not run automatically or suggest running on a cadence; this is a deliberate, user-invoked cleanup pass.
