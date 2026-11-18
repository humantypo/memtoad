---
name: tidy
description: Curate diary/architectural_decisions.md and diary/lessons_learned.md so what reads as in force is in force — fold a decision into the later entry that explicitly reverses it, label entries that are superseded or retired, and correct wording that names a mechanism since replaced. Proposes every change with its evidence and writes nothing until the user confirms. Never deletes reasoning, never archives, never acts on age alone. Run on demand, never on a schedule.
---

Run the following steps **inline in the main conversation**. Never spawn an agent: each change is an editorial call the user should watch being made, not receive as a finished diff.

## Why this exists

The two files are append-only (→ three-files-no-archiving), and archiving by date or size was tried and rejected because archived content stops being read (→ archive-files-are-never-read). So `tidy` never removes an entry from what is read. What it fixes is **correctness**: over time some entries stop being true. A later decision reverses them, the code they govern is removed, or the mechanism they name is replaced. A stale entry that still reads as in force misleads every future session. `tidy` makes that visible with a **label**, and keeps the entry's text, because what was tried and why it stopped applying is half of what the diary is for.

`session-historian` already labels what a *new* entry supersedes, at the moment it is written. `tidy` is for what that missed: an existing diary, or changes that happened without a diary entry naming the old one.

## The label grammar

A label goes inside the entry's date parenthetical, exactly in one of these forms:

```
## old-slug (June 2026; superseded by new-slug)
## old-slug (June 2026; retired Nov 2026: the install scripts were removed in the plugin conversion)
```

- The target of `superseded by` may be in either file: a lesson can be superseded by a decision.
- The reason is one clause, at most 120 characters, with no parentheses.
- An unlabelled entry is in force. There is no `active` label.
- Labelling changes the heading only. The slug, the date and every `(→ slug)` reference stay valid.

## Step 1 — Read

Read both files in full. With enhanced memory (`CLAUDE.md` contains `<!-- memtoad:store -->`), read the Index with the memstore command's `index`, then the digests, and `get` the full entry for anything you are about to propose a change to.

## Step 2 — Find candidates

There are four kinds. Only these four count.

1. **Reversal pairs.** An entry contains `This reverses (→ slug)`, and the entry it names is still unlabelled. In plain mode, propose **folding** the pair (below). With enhanced memory, propose **labelling** the older entry `superseded by <newer-slug>` instead. Folding there would leave the older entry's archived text with no digest, which `check-pointers` reports as an error.
2. **Supersession that was never written down.** A later entry replaces an earlier one in substance without naming it. For example, a hook replaced an advisory instruction that an older entry prescribes. Propose `superseded by <later-slug>`. Quote the sentence in the later entry that does the replacing; if you cannot quote one, it is not a candidate.
3. **Retirement.** What the entry governs no longer exists, and nothing replaced it. Evidence is required: name what you checked (a grep for the file, function, flag or command it names, the README, `git log --diff-filter=D`) and what you found. A renamed thing is not a gone thing, so search for where it went before proposing.
4. **Owner-stated.** The user says "retire X because Y", or "X is replaced by Z". Propose exactly that label.

Also flag, as a fifth kind, a **correction**. An entry still in force whose wording names a replaced mechanism (for example "the install scripts add …" when `/bootstrap` now does it) gets the smallest edit that makes it true again. Never change its decision or its reasoning.

**Stricter rules for lessons.** A lesson records something that went wrong, and is often most valuable long after the code it names has gone.
- Retire a lesson only when the *hazard itself* can no longer occur, not merely when the file it names is gone.
- When a later entry carries the lesson's rule forward in a new form, prefer `superseded by <that-slug>`, so the lesson keeps a pointer to where its rule lives now.
- Never retire a lesson that another entry references with `(→ slug)`.

**Never a candidate on age alone,** and never on topic similarity: "these two entries are about the same thing" is not evidence.

## Step 3 — Draft

For each candidate, show it like this:
- the entry's current heading, or the digest lead with enough of the body to judge;
- the proposed heading, lead or correction;
- the evidence, one or two lines.

**Folding** (plain mode, reversal pairs only) drafts a single replacement entry:

```markdown
## newer-slug (Month YYYY, supersedes older-slug)

<the newer entry's decision statement, unchanged>

**Why**: <the newer entry's WHY, unchanged or lightly trimmed>. Originally (older Month YYYY) <one compressed sentence: what the older entry decided and the core reason it was reconsidered — drawn from the older entry's own WHY, not invented>.
```

The surviving header keeps the newer slug and date, and appends `, supersedes older-slug` to its parenthetical, so the older slug stays greppable. Drop the now-redundant "This reverses (→ ...)" sentence. Skip a fold when the older slug is referenced anywhere outside the reversing entry, or when the older entry is itself part of a chain of three or more; label it `superseded by` instead.

## Step 4 — Confirm before writing

Show every proposal. Ask which to apply, defaulting to "all" but letting the user exclude any. Do not write anything until the user confirms.

## Step 5 — Apply and report

- **Plain mode:** edit the headings, apply the corrections, and replace each folded pair with its merged entry in the position the newer one held. Leave everything else untouched.
- **With enhanced memory:**
  - A digested entry gets `<memstore command> set-label mem:diary/<file>#<slug> --superseded-by <slug>` (or `--retired "Mon YYYY: <reason>"`). This edits its lead and moves it to the Index's "No longer in force" list.
  - A full entry below the digest region is edited in place.
  - A correction to a digested entry is a correction to its digest text only; its archived original stays as written.
  - Then run `<memstore command> check-pointers`, which must report 0 errors.

Do not stage or commit. Tell the user to review with `git diff diary/` and commit through the normal flow (`/committer`). This is an editorial change and deserves the same review any diary edit gets.

## What NOT to do

- Do not delete an entry, a digest, or any of an entry's reasoning. Labelling keeps the text; folding compresses the older entry into one clause of the merged WHY.
- Do not act on age, staleness without evidence, or topic similarity.
- Do not touch `diary/session_context.md`. session-historian already keeps it to active work.
- Do not run automatically or on a schedule, and do not propose a pass at the end of another skill. The user invokes `tidy`.
