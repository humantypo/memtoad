---
name: bootstrap
description: Populate the diary from scratch on a project that just had Memtoad installed. Inspects existing code and docs, asks targeted questions about what the code can't reveal, then writes first-draft entries into all three diary files. Safe to run on partially-initialized diaries — detects which files need population via a sentinel marker.
---

Populate the Memtoad diary for this project. Run **inline in the main conversation** (do not spawn an agent).

## Phase 0: Detect state

Read all three diary files:
1. `diary/session_context.md`
2. `diary/architectural_decisions.md`
3. `diary/lessons_learned.md`

For each file, check whether it contains `<!-- memtoad:uninitialized -->`. Build a list of which files are uninitialized (sentinel present) vs. already populated (no sentinel).

- **All uninitialized**: proceed to Phase 1 without prompting.
- **Some uninitialized, some not**: note which files already have entries. Proceed to populate only the uninitialized ones.
- **All initialized**: use the **AskUserQuestion** tool to ask the user whether to proceed in merge mode (add new entries without overwriting existing ones) or abort. If they choose to abort, stop here.

## Phase 1: Inspect codebase

Read whatever exists, in this order (skip any not present):
1. `CLAUDE.md`
2. `README.md`
3. Package manifest — whichever is present: `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `Gemfile`, `Makefile`
4. Up to 5 files in `docs/` or `doc/`

Also run: `git log --oneline -30` to understand project history and timeline (if not a git repo, skip).

After reading, form an internal picture of what the project does, its stack, its maturity, and any decisions or patterns visible in the code or docs. Do not output anything to the user yet — this phase is silent.

## Phase 2: Targeted Q&A

Ask the user questions to surface what code inspection alone cannot reveal. Ask **one at a time** and wait for each answer before proceeding.

For binary or categorical choices, use the **AskUserQuestion** tool. For follow-up questions that need free-form description, ask as plain text.

**Q1 — Current state gaps** (informs `session_context.md`):

Use AskUserQuestion:
> "I've read the available docs. Is there anything about the current project state not captured there?"

Options:
- "Nothing to add — docs reflect current state"
- "There's active in-progress work to note"
- "There are known blockers or deferred items"
- Other (custom)

If the user indicates there's something to capture, ask as plain text: "Briefly describe what's in-progress or deferred — enough that you could pick it back up without re-reading the full history."

**Q2 — Architectural decisions** (informs `architectural_decisions.md`):

Use AskUserQuestion:
> "Are there non-obvious design decisions on this project that aren't captured in the docs — choices a new engineer would be surprised by?"

Options:
- "Yes — there are decisions worth capturing"
- "Not yet — project is too early"
- "Already in the docs you read"
- Other (custom)

If yes, ask as plain text: "Describe the key decision: what was chosen, what was the alternative, and what constraint or failure mode drove the choice?"

**Q3 — Lessons learned** (informs `lessons_learned.md`):

Use AskUserQuestion:
> "Are there failure modes, anti-patterns, or hard-won rules specific to this project — things that aren't obvious from the code?"

Options:
- "Yes — there are lessons worth capturing"
- "Not yet — too early to have hard-won lessons"
- "Already in the docs you read"
- Other (custom)

If yes, ask as plain text: "Describe what happened and what the one-sentence rule would be for a future engineer."

## Phase 3: Write diary files

Write or update each file that is uninitialized (or confirmed for merge in Phase 0). Remove `<!-- memtoad:uninitialized -->` from every file you write.

**`diary/session_context.md`**:
- **Current State**: one paragraph synthesizing Phase 1 findings plus any gaps the user named in Q1. Describe what the system is, its production status, key tech facts.
- **Most Recent Sessions**: leave empty — this is populated by `/session-historian` going forward.
- **Open Items**: populate from any deferred work found in existing docs, plus anything the user described in Q1.
- **Key Diary Files**: standard links to the other two files.
- Update the `[Date]` placeholder with today's date if still present.

**`diary/architectural_decisions.md`**:
- If decisions were found in docs (Phase 1) or the user described one (Q2): write entries using `## slug-based-header (Month YYYY)` format. One sentence stating the decision, then a **Why** section for the reasoning.
- If no decisions exist yet: write a single minimal entry noting when the diary was initialized, to be expanded as decisions are made.
- Remove `<!-- memtoad:uninitialized -->`.

**`diary/lessons_learned.md`**:
- If the user described lessons in Q3: write entries using `## slug-based-header (Month YYYY)` format with a **Rule** and **Why** section.
- If no lessons yet: leave the file with just the header (no entries) and remove only the sentinel.
- Remove `<!-- memtoad:uninitialized -->`.

After writing all files, output a brief summary: which files were written, how many entries were added to each, and remind the user to run `/startup` to verify the briefing reads coherently.
