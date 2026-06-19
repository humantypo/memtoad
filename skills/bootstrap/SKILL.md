---
name: bootstrap
description: Set up Memtoad for a project and populate the diary. Creates diary/ directory and files, injects CLAUDE.md Project Memory section, configures .gitignore, then inspects the codebase and asks targeted questions to write first-draft diary entries. Run once after installing the plugin in a new project. Safe to re-run — idempotent setup, sentinel-based population.
---

Set up Memtoad for this project and populate the diary. Run **inline in the main conversation** (do not spawn an agent).

## Phase 0: Project setup (idempotent)

### 0a — Create diary files

Check whether `diary/` exists in the current working directory. If it does not, create it. Then for each of the three diary files, create it if it does not yet exist, using the templates below. Replace `[Project Name]` with the actual project name (derive from directory name or the title in README.md if available) and `[Date]` with today's date.

**Template for `diary/session_context.md`**:
```
# Session Context — [Project Name]

**Last Updated**: [Date]

---

## Current State

[One paragraph: what the system is, production status, key facts a new engineer needs to orient.
Not a feature list — a snapshot of where things stand right now.]

---

## Most Recent Sessions

[Entries added here by /committer or /session-historian. Most recent first.
Each entry: date, what was done (WHY-focused), any cross-refs to lessons or decisions.]

---

## Open Items

[Deferred work. Each item: enough context to resume without re-reading history.]

---

## Key Diary Files

- [architectural_decisions.md](architectural_decisions.md) — design principles, non-negotiable patterns
- [lessons_learned.md](lessons_learned.md) — anti-patterns and hard-won insights (most recent at top)

<!-- memtoad:uninitialized -->
```

**Template for `diary/architectural_decisions.md`**:
```
# Architectural Decisions

Design principles and the reasoning behind non-obvious choices. Add an entry when a future
engineer would reasonably ask "why did they do it this way?" — and the answer isn't obvious
from the code.

Most recent decisions at top. No archiving.

---

<!-- memtoad:uninitialized -->
```

**Template for `diary/lessons_learned.md`**:
```
# Lessons Learned

Anti-patterns, failure modes, and hard-won rules. Most recent at top. Add an entry only when
a lesson is non-obvious — if it's standard practice or documented in the framework, skip it.

Cross-references use (→ slug-name) notation.

---

<!-- memtoad:uninitialized -->
```

### 0b — Inject CLAUDE.md section

Read `CLAUDE.md` in the current directory (create it if it doesn't exist). If it does NOT already contain `<!-- memtoad:version:` anywhere in the file, prepend the following block at the very top (before any existing content):

```
## Project Memory
<!-- memtoad:version:2 -->
- [diary/session_context.md](diary/session_context.md) — current state and recent work
- [diary/architectural_decisions.md](diary/architectural_decisions.md) — design principles and non-negotiable patterns
- [diary/lessons_learned.md](diary/lessons_learned.md) — anti-patterns and hard-won insights

**Before any git commit**, run `/committer` — it updates the diary and crafts the commit message in one step.

Commit workflow:
1. Tests pass
2. `/committer` — updates diary + commits

```

If CLAUDE.md already has `<!-- memtoad:version:` the Project Memory section is present — skip injection.

### 0c — Configure .gitignore

Use **AskUserQuestion** to ask the user which git tracking mode to use:

> "How should diary files be tracked in git?"

Options:
- **Shared** — Track all three diary files. Best for solo projects or single active contributors.
- **Hybrid** — Track decisions + lessons, ignore session_context.md. Recommended for teams: shared knowledge, private work state.
- **Private** — Ignore entire diary/ and CLAUDE.md. Each contributor manages diary locally.

After the user answers, check `.gitignore` for an existing `# Memtoad` section. If one exists, skip. Otherwise append the appropriate block:

**Shared**: Add a comment only (all files tracked by default):
```
# Memtoad
# diary/ is fully tracked (shared mode)
```

**Hybrid**:
```
# Memtoad
diary/session_context.md
```

**Private**:
```
# Memtoad
diary/
CLAUDE.md
```

---

## Phase 0 complete — detect diary population state

Read all three diary files and check for `<!-- memtoad:uninitialized -->` in each.

- **All uninitialized**: proceed to Phase 1 without prompting.
- **Some uninitialized, some not**: note which files already have entries. Proceed to populate only the uninitialized ones.
- **All initialized**: use **AskUserQuestion** to ask whether to proceed in merge mode (add new entries without overwriting existing ones) or abort. If they choose to abort, stop here.

---

## Phase 1: Inspect codebase

Read whatever exists, in this order (skip any not present):
1. `CLAUDE.md`
2. `README.md`
3. Package manifest — whichever is present: `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `Gemfile`, `Makefile`
4. Up to 5 files in `docs/` or `doc/`

Also run: `git log --oneline -30` to understand project history and timeline (if not a git repo, skip).

After reading, form an internal picture of what the project does, its stack, its maturity, and any decisions or patterns visible in the code or docs. Do not output anything to the user yet — this phase is silent.

---

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

---

## Phase 3: Write diary files

Write or update each file that is uninitialized (or confirmed for merge in Phase 0). Remove `<!-- memtoad:uninitialized -->` from every file you write.

**`diary/session_context.md`**:
- **Current State**: one paragraph synthesizing Phase 1 findings plus any gaps the user named in Q1. Describe what the system is, its production status, key tech facts.
- **Most Recent Sessions**: leave empty — this is populated by `/committer` or `/session-historian` going forward.
- **Open Items**: populate from any deferred work found in existing docs, plus anything the user described in Q1.
- **Key Diary Files**: standard links to the other two files.
- Replace `[Date]` with today's date and `[Project Name]` with the actual project name.

**`diary/architectural_decisions.md`**:
- If decisions were found in docs (Phase 1) or the user described one (Q2): write entries using `## slug-based-header (Month YYYY)` format. One sentence stating the decision, then a **Why** section for the reasoning.
- If no decisions exist yet: write a single minimal entry noting when the diary was initialized, to be expanded as decisions are made.
- Remove `<!-- memtoad:uninitialized -->`.

**`diary/lessons_learned.md`**:
- If the user described lessons in Q3: write entries using `## slug-based-header (Month YYYY)` format with a **Rule** and **Why** section.
- If no lessons yet: leave the file with just the header (no entries) and remove only the sentinel.
- Remove `<!-- memtoad:uninitialized -->`.

After writing all files, output a brief summary: which files were written, how many entries were added to each, and remind the user to run `/startup` to verify the briefing reads coherently.
