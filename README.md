# Memtoad

Persistent, readable project memory for Claude Code. Three markdown files. Three skills. No database, no cloud sync, no archiving.

---

## What it is

Memtoad gives Claude persistent project memory across sessions without depending on provider-side memory features, external storage, or complex tooling. It stores three things:

- **What's happening now** — current work state and open items
- **Why things are the way they are** — architectural decisions with their reasoning
- **What to never repeat** — anti-patterns and hard-won lessons

### Design philosophy

Claude already has access to your code, your git history, and your file system. What it cannot reconstruct from those sources is the *narrative arc* of the project: the design choices that weren't obvious, the failure modes you discovered the hard way, the deferred work and why it was deferred.

Memtoad fills exactly that gap. The diary is not a substitute for git history, inline comments, or documentation — it supplements them by capturing context that wouldn't survive in any of those places.

The system is designed to stay lean. Sessions that produced no new decisions or lessons write one file. Sessions that did produce something new write up to three. There is no archiving, no fourth file, no spawned agent for the historian. The files grow slowly, remain readable, and load in full on every session.

### Why named Memtoad

The name is a portmanteau of *Memento* and *Toad*. Memento — the film — encodes memory into persistent physical artifacts (tattoos, polaroids, notes) because short-term recall can't be trusted across sessions. Toad — from Arnold Lobel's *Frog and Toad* — is the deliberate one: the list-maker, the keeper of plans, the character who writes things down so he doesn't forget. Frog improvises. Toad remembers.

Claude is Frog. The diary is Toad's list.

---

## Requirements

- **bash** 3.2+ (pre-installed on macOS and Linux)
- **git** (for `.gitignore` configuration and the `--update` detection)
- **perl** (pre-installed on macOS and most Linux distros — used for placeholder substitution and `.gitignore` section replacement)

---

## Quick start

Clone this repo once, then apply it to as many projects as you like:

```bash
git clone https://github.com/your-username/memtoad.git
~/path/to/memtoad/install.sh /path/to/your-project
```

`install.sh` detects whether the target has existing code and runs the appropriate init path. It creates the target directory if needed (with confirmation), installs skills and commands, injects the `CLAUDE.md` Project Memory section, configures `.gitignore` git tracking, and — for existing projects — writes `MEMTOAD_INIT.md` containing the Claude prompts for steps 5–9.

To update skills and commands in a project that already has Memtoad installed (e.g., after pulling a new version):

```bash
~/path/to/memtoad/install.sh --update /path/to/your-project
```

This overwrites `.claude/skills/` and `.claude/commands/` but never touches `diary/` or `CLAUDE.md`.

---

## File structure

In any target project:

```
project-root/
├── diary/
│   ├── session_context.md          # current state, open items
│   ├── architectural_decisions.md  # WHY things are designed the way they are
│   └── lessons_learned.md          # anti-patterns, failure modes, hard-won rules
├── CLAUDE.md                       # add a Project Memory section pointing to diary/
└── .claude/
    ├── skills/
    │   ├── startup/
    │   │   └── SKILL.md            # reads 3 diary files, synthesizes briefing
    │   ├── session-historian/
    │   │   └── SKILL.md            # writes to diary files inline at session end
    │   ├── grill-me/
    │   │   └── SKILL.md            # interrogates a plan informed by project context
    │   └── bootstrap/
    │       └── SKILL.md            # populates diary on a freshly installed project
    └── commands/
        ├── startup.md              # /startup command
        ├── session-historian.md    # /session-historian command
        ├── grill-me.md             # /grill-me command
        └── bootstrap.md            # /bootstrap command
```

The `diary/` files are the runtime artifacts. The `.claude/` files are the instructions that operate on them. The `templates/` directory in this repo contains ready-to-copy blank starters for the diary files.

**Memtoad repo structure** (what you clone):

```
install.sh                            # smart entry point — detects new vs existing
scripts/
  install-new.sh                    # low-level primitive: new project
  install-existing.sh               # low-level primitive: existing project
templates/                          # skeleton starters for diary files
.claude/skills/                     # installable SKILL.md files
.claude/commands/                   # installable command wrappers
```

---

## The three diary files

### `diary/session_context.md`

**Purpose**: The current state of the project. Always rewritten, never stale.

**Sections**:
- **Current State** — one paragraph: production status, key system facts, active test counts, infrastructure state. Not a feature list — a snapshot.
- **Most Recent Sessions** — reverse-chronological entries. Each: date, what was done (WHY-focused narrative, not a file list), cross-refs to lessons or decisions if any.
- **Open Items** — numbered list of deferred work with enough context to resume.
- **Key Diary Files** — links to the other two files.

**What belongs**: narrative description of work done (the reasoning behind it, not just the outcome), deferred items with their deferral rationale, cross-references to new decisions or lessons.

**What doesn't belong**:
- Per-file change lists ("modified `foo.py` at line 34 to add param `bar`")
- Code snippets
- "Status: COMPLETE" announcements
- Verification steps ("tests pass", "build green")
- Commit hashes, dates, or file paths of changes (git has those)

**Update rule**: Always rewritten by `/session-historian`. This is the one file that changes every session.

---

### `diary/architectural_decisions.md`

**Purpose**: The non-obvious design choices and the reasoning behind them. Entries survive long after the person who made them is gone.

**Entry format**:

```markdown
## decision-slug (Month YYYY)

One sentence: the decision itself.

**Why**: The constraint, tradeoff, or failure mode that drove this choice.
What was rejected and why? What would break if this decision were reversed?

Optional: a brief code snippet only if it makes the WHY concrete.
```

**What belongs**: choices a future engineer would be surprised by, choices that required rejecting an obvious alternative, design invariants that look like bugs if you don't know the reasoning.

**What doesn't belong**: standard practices, things enforceable by tooling, decisions whose WHY is "because we always do it this way."

**Format rules**:
- Slug-based headers, not numbers (slugs survive reordering; numbers don't)
- Most recent at top
- Append-only — no archiving

---

### `diary/lessons_learned.md`

**Purpose**: Anti-patterns, failure modes, and hard-won rules. The things that bit you and must not bite again.

**Entry format**:

```markdown
## lesson-slug (Month YYYY)

**Rule**: One sentence — the actionable takeaway.

**Why**: What happened, what it cost, and why the lesson isn't obvious.
A brief code snippet is acceptable only if it makes the lesson clearer.
```

**What belongs**: non-obvious lessons — things you couldn't have known from reading the docs, failures that seemed impossible until they happened, subtle invariants that break silently if violated.

**What doesn't belong**: standard best practices, anything documented in the framework's official docs, lessons whose rule is "write tests" or "read the docs first."

**Format rules**:
- Slug-based headers
- Most recent at top
- Cross-references use `(→ slug-name)` notation, never numbers
- Append-only — no archiving

---

## The skills

### `startup` — loads diary at session start

Spawns a subagent to read all three diary files and synthesize a briefing. Runs from cold — the main conversation has no context yet, so spawning is appropriate here.

**File**: `.claude/skills/startup/SKILL.md`

```markdown
---
name: startup
description: Load full project context at the start of a session — reads architectural decisions, current implementation state, and session context to establish a complete picture before beginning work.
---

Use the Agent tool to spawn the `startup` subagent with this prompt:

"Load full project context. Read diary/architectural_decisions.md, diary/lessons_learned.md, and diary/session_context.md in order. Synthesize the current state, active priorities, and any open questions, then report a concise briefing."
```

**When to invoke**: at the start of any non-trivial session, or when the user asks "what were we working on?"

---

### `session-historian` — writes diary at session end

Runs **inline in the main conversation** (no agent spawn). The main conversation already has full session context; spawning an agent to re-derive it is the expensive path.

**File**: `.claude/skills/session-historian/SKILL.md`

```markdown
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
```

**When to invoke**: at the end of any session with meaningful work, or after a significant decision or discovery.

---

### `grill-me` — interrogates a plan using project context

Interviews the user about a plan or design until reaching shared understanding. Uniquely, it reads the diary first — so the interrogation is grounded in current constraints, past decisions, and known failure modes before the first question is asked.

This is the key integration between the historian and the interviewer: grill-me can surface "we already made this decision" or "we learned this lesson the hard way" before the user has a chance to repeat a mistake.

**File**: `.claude/skills/grill-me/SKILL.md`

```markdown
---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Reads project diary first to surface relevant constraints. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---

Interview the user relentlessly about every aspect of their plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one.

## Phase 0: Load project context

Before asking any questions, read these three files in order:
1. `diary/architectural_decisions.md`
2. `diary/lessons_learned.md`
3. `diary/session_context.md`

After reading, output 1–2 sentences naming any constraints, decisions, or patterns from the diary that are directly relevant to the stated task. This lets the user correct misreadings before the interrogation begins. If nothing in the diary bears on the task, skip this acknowledgment and proceed silently.

## How to ask questions

Use the **AskUserQuestion tool** for every question you ask. Never pose questions as plain text in your response — always use the multiple-choice popup so the user can quickly select an answer or type a custom one.

Ask **one question at a time**. Wait for the user's answer before moving to the next question. This keeps the conversation focused and prevents overwhelm.

For each question, provide 2–4 concrete multiple-choice options representing the most likely answers or directions. Think about what the user would realistically choose — generic options like "Yes" / "No" aren't helpful unless the question is genuinely binary. The user always has the "Other" field available to write something custom.

## Flow

1. After receiving an answer, briefly acknowledge the decision (1–2 sentences max), then immediately ask the next question via AskUserQuestion.
2. If a question can be answered by exploring the codebase or files, explore them yourself instead of asking the user.
3. Continue until all branches of the design tree are resolved.
4. When finished, provide a concise summary of all decisions made.
```

**When to invoke**: when stress-testing a plan, before starting a significant new feature, or when the user says "grill me on this."

---

### `bootstrap` — populates the diary after installation

Run once after installing Memtoad on an existing project (or a new project with some initial docs). Inspects the codebase and available documentation, then conducts a short targeted Q&A to surface what code inspection alone cannot reveal — the non-obvious decisions, the failure modes, the deferred work. Writes first-draft entries into all three diary files.

The skill detects which files need population by checking for a `<!-- memtoad:uninitialized -->` sentinel that the install templates include. Files that already have entries are left alone unless the user explicitly confirms merge mode.

**File**: `.claude/skills/bootstrap/SKILL.md`

```markdown
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
```

**When to invoke**: once, immediately after `install.sh` runs on an existing project. For new projects, run it after writing the first few lines of a README or CLAUDE.md so the skill has something to inspect.

---

## Command wrappers

Install these in `.claude/commands/` to enable `/startup`, `/session-historian`, `/grill-me`, and `/bootstrap` as slash commands.

**`.claude/commands/startup.md`**:

```markdown
---
description: Load full project context at session start — architecture, decisions, current state
---

Use the Agent tool to spawn the `startup` subagent with this prompt:

"Load full project context. Read diary/architectural_decisions.md, diary/lessons_learned.md, and diary/session_context.md in order. Synthesize the current state, active priorities, and any open questions, then report a concise briefing."
```

**`.claude/commands/session-historian.md`**:

```markdown
---
description: Document session accomplishments, decisions, and lessons to diary (runs inline)
---

Run the session-historian skill inline. Do not spawn an agent. You already have full session context.

Review what was accomplished this session. Then:
- Always rewrite diary/session_context.md with the current state.
- Only if a new architectural decision was made: append to diary/architectural_decisions.md.
- Only if a new lesson was learned: append to diary/lessons_learned.md.
```

**`.claude/commands/grill-me.md`**:

```markdown
---
description: Stress-test a plan or design — reads project diary first, then interrogates relentlessly
---

Invoke the grill-me skill. First read all three files in diary/ to load project context and surface relevant constraints. Then interview me about my plan or design using the AskUserQuestion tool, one question at a time, until all branches of the decision tree are resolved.
```

**`.claude/commands/bootstrap.md`**:

```markdown
---
description: Populate diary files from scratch — inspects codebase, asks targeted questions, writes first-draft entries
---

Invoke the bootstrap skill. Check diary files for the uninitialized sentinel, inspect the codebase and docs, ask targeted questions about what the code can't reveal, then write first-draft entries into all three diary files. Safe on partially-initialized diaries — only writes to files that still contain the sentinel (or are confirmed for merge).
```

---

## CLAUDE.md integration

Add this block near the top of the root `CLAUDE.md` in any target project:

```markdown
## Project Memory

Cross-project decisions, lessons, and current work live in [`diary/`](diary/):
- [`diary/session_context.md`](diary/session_context.md) — current state and recent work
- [`diary/architectural_decisions.md`](diary/architectural_decisions.md) — design principles and non-negotiable patterns
- [`diary/lessons_learned.md`](diary/lessons_learned.md) — anti-patterns and hard-won insights
```

For component-level `CLAUDE.md` files (inside a subdirectory like `frontend/` or `api/`), use relative paths:

```markdown
## Project Memory

- [diary/session_context.md](../diary/session_context.md) — current state and recent work
- [diary/architectural_decisions.md](../diary/architectural_decisions.md) — design principles and non-negotiable patterns
- [diary/lessons_learned.md](../diary/lessons_learned.md) — anti-patterns and hard-won insights
```

---

## Init: new project

For a project with no existing documentation or captured decisions.

**Quick path**: `install.sh /path/to/your/project` — detects the project type, runs steps 1–4 automatically (creates diary, installs skills, updates CLAUDE.md, configures `.gitignore`), then prompts you to run `/bootstrap`. Step 6 (verify) remains manual.

**Manual steps**:

1. **Create the diary directory and copy the skeleton files from `templates/`**:
   ```bash
   mkdir -p diary
   cp path/to/memtoad/templates/*.md diary/
   ```
   Edit each file to replace `[Project Name]` and `[Date]`.

2. **Install the skills**:
   ```bash
   mkdir -p .claude/skills/startup .claude/skills/session-historian .claude/skills/grill-me .claude/skills/bootstrap .claude/commands
   ```
   Copy `SKILL.md` for each skill from the `.claude/skills/` directory of this repo.
   Copy the four command wrappers from `.claude/commands/` of this repo.

3. **Add the Project Memory section to your root `CLAUDE.md`** (create it if it doesn't exist).

4. **Configure git tracking** — add a Memtoad section to `.gitignore`. Choose a mode:
   - **Shared**: track all diary files (solo project or single active contributor)
   - **Hybrid**: track `architectural_decisions.md` + `lessons_learned.md`, ignore `session_context.md` (recommended for teams)
   - **Private**: ignore entire `diary/` (each contributor manages their own diary locally)

5. **Run `/bootstrap`** — open Claude Code in the project directory and run `/bootstrap`. This inspects the codebase, asks targeted questions about what the code can't reveal, and writes first-draft diary entries.

6. **Verify**: run `/startup` to confirm Claude can load and synthesize the diary into a coherent briefing.

---

## Init: existing project

For a project with existing documentation, past decisions, and accumulated knowledge. The challenge here is that existing docs may be scattered — README files, design docs, inline comments, old ADRs. This is a distillation exercise, not a copy exercise.

**Quick path**: `install.sh /path/to/your/project` — detects existing code, runs steps 1–4 automatically (creates diary, installs skills, updates CLAUDE.md, configures `.gitignore`), auto-discovers doc files (`README.md`, `CLAUDE.md`, `docs/`), and writes `MEMTOAD_INIT.md` with the `/bootstrap` prompt and post-bootstrap steps. Steps 5–7 remain manual.

**Manual steps**:

1. **Create the diary directory and copy skeleton files** (same as new project, step 1).

2. **Install the skills and commands** (same as new project, step 2).

3. **Add the Project Memory section to `CLAUDE.md`** (same as new project, step 3).

4. **Configure git tracking** (same as new project, step 4).

5. **Run `/bootstrap`** — open Claude Code in the project directory and run `/bootstrap`. The skill auto-detects your docs, reads the codebase, asks targeted questions about decisions and lessons that aren't in the docs, then writes first-draft entries into all three diary files.

6. **Prune**: read all three files yourself. Remove:
   - Anything obvious from the code or standard in the framework
   - Anything already enforced by tests, linters, or CI
   - Any entry whose WHY section is "because we always do it this way"
   - Any entry without a specific incident or reasoning behind it

7. **Run `/startup`** to confirm the briefing makes sense and captures what a new contributor would actually need to know.

---

## Skeleton templates

These are the blank starters that `install.sh` and the install scripts copy into `diary/` and fill in automatically. They are also available in the `templates/` directory of this repo for manual installation.

---

### `diary/session_context.md`

```markdown
# Session Context — [Project Name]

**Last Updated**: [Date]

---

## Current State

[One paragraph: what the system is, production status, key facts a new engineer needs to orient.
Not a feature list — a snapshot of where things stand right now.]

---

## Most Recent Sessions

[Entries added here by /session-historian. Most recent first.
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

---

### `diary/architectural_decisions.md`

```markdown
# Architectural Decisions

Design principles and the reasoning behind non-obvious choices. Add an entry when a future
engineer would reasonably ask "why did they do it this way?" — and the answer isn't obvious
from the code.

Most recent decisions at top. No archiving.

---

<!-- memtoad:uninitialized -->
```

*(The `<!-- memtoad:uninitialized -->` sentinel tells `/bootstrap` that this file needs population. It is removed when the first entries are written.)*

---

### `diary/lessons_learned.md`

```markdown
# Lessons Learned

Anti-patterns, failure modes, and hard-won rules. Most recent at top. Add an entry only when
a lesson is non-obvious — if it's standard practice or documented in the framework, skip it.

Cross-references use (→ slug-name) notation.

---

<!-- memtoad:uninitialized -->
```

*(Sentinel removed when the first entries are written, or when `/bootstrap` determines there are no lessons to capture yet.)*

---

## Design principles for Memtoad itself

These constrain how the system evolves. If you fork or extend it, respect them.

**Supplement, don't duplicate.** The diary captures what git history and code cannot: the narrative arc and the non-obvious WHY. Implementation details belong in the code. Timelines belong in git log. The diary is not a substitute for either.

**Three files, no more.** The archive explosion that Memtoad was designed to replace happened because files multiplied without bound. Resist the urge to add a fourth file for bugs, a fifth for refactoring history. Bugs worth remembering become lessons. Refactors worth remembering become decisions. If it doesn't fit the three files, it probably doesn't belong in the diary.

**Inline, not spawned — except startup.** The session-historian runs in the main conversation, which already has the session context. Spawning an agent to re-derive context you already have is the expensive path. The startup skill spawns because it genuinely starts cold with no session context. Grill-me runs inline because it needs the interactive AskUserQuestion tool, which agents cannot use.

**No archiving.** The old system archived files when they grew large. Modern context windows make this obsolete, and archived files are never read. Let the files grow.

**Conditional writes.** Session-historian always updates `session_context.md`. It only touches the other two files when something genuinely new was decided or learned. Most sessions produce only one update.

**Documentation commits with the code, not after.** Run `/session-historian` before staging the commit. Stage `diary/` alongside the code changes. Commit everything together. Do not reference the commit hash in diary entries — it isn't known yet, and git log is the authoritative record.

**Slugs, not numbers.** Numbered lessons rot when you reorder or delete entries. Slugs are self-describing and survive restructuring. `(→ null-key-defers-failure)` tells you what it is; `(→ Lesson 228)` tells you nothing.
