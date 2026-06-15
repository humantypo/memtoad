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
    │   └── grill-me/
    │       └── SKILL.md            # interrogates a plan informed by project context
    └── commands/
        ├── startup.md              # /startup command
        ├── session-historian.md    # /session-historian command
        └── grill-me.md             # /grill-me command
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

## Command wrappers

Install these in `.claude/commands/` to enable `/startup`, `/session-historian`, and `/grill-me` as slash commands.

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

**Quick path**: `install.sh /path/to/your/project` — detects the project type, runs steps 1–4 automatically (creates diary, installs skills, updates CLAUDE.md, configures `.gitignore`), then prints the bootstrap prompt. Steps 5–6 remain manual. The lower-level `scripts/install-new.sh` is available if you want to bypass detection and run new-project init directly.

**Manual steps**:

1. **Create the diary directory and copy the skeleton files from `templates/`**:
   ```bash
   mkdir -p diary
   cp path/to/memtoad/templates/*.md diary/
   ```
   Edit each file to replace `[Project Name]` and `[Date]`.

2. **Install the skills**:
   ```bash
   mkdir -p .claude/skills/startup .claude/skills/session-historian .claude/skills/grill-me .claude/commands
   ```
   Copy `SKILL.md` for each skill from the `.claude/skills/` directory of this repo.
   Copy the three command wrappers from `.claude/commands/` of this repo.

3. **Add the Project Memory section to your root `CLAUDE.md`** (create it if it doesn't exist).

4. **Configure git tracking** — add a Memtoad section to `.gitignore`. Choose a mode:
   - **Shared**: track all diary files (solo project or single active contributor)
   - **Hybrid**: track `architectural_decisions.md` + `lessons_learned.md`, ignore `session_context.md` (recommended for teams)
   - **Private**: ignore entire `diary/` (each contributor manages their own diary locally)

5. **Run a bootstrap session** — open Claude Code in the project and give it this prompt:

   > "I just initialized Memtoad in this project. Please read CLAUDE.md and any existing README or design docs, then write a first draft of the three diary files based on what you find. For `diary/session_context.md`, describe the current state of the project. For `diary/architectural_decisions.md`, write one entry for the most important design choice already made. Leave `diary/lessons_learned.md` with just the header — no entries yet."

6. **Verify**: run `/startup` to confirm Claude can load and synthesize the diary into a coherent briefing.

---

## Init: existing project

For a project with existing documentation, past decisions, and accumulated knowledge. The challenge here is that existing docs may be scattered — README files, design docs, inline comments, old ADRs. This is a distillation exercise, not a copy exercise.

**Quick path**: `install.sh /path/to/your/project` — detects existing code, runs steps 1–4 automatically (creates diary, installs skills, updates CLAUDE.md, configures `.gitignore`), auto-discovers doc files (`README.md`, `CLAUDE.md`, `docs/`), and writes `MEMTOAD_INIT.md` in the project root with all five Claude prompts ready to paste. Steps 5–9 remain manual. The lower-level `scripts/install-existing.sh` accepts explicit doc paths if you want to override auto-detection.

**Manual steps**:

1. **Create the diary directory and copy skeleton files** (same as new project, step 1).

2. **Install the skills and commands** (same as new project, step 2).

3. **Add the Project Memory section to `CLAUDE.md`** (same as new project, step 3).

4. **Configure git tracking** (same as new project, step 4).

5. **Populate `diary/architectural_decisions.md` from existing docs**:

   Open Claude Code and provide the prompt:
   > "Read [list your main docs: CLAUDE.md, README.md, design docs, etc.]. For each non-obvious architectural decision you find — a choice where a future engineer would ask 'why did they do it this way?' and the answer isn't obvious from the code — write a dated entry in `diary/architectural_decisions.md` using the `## slug-based-header (Month YYYY)` format. Extract the decision and its reasoning; do not copy text verbatim. Skip anything that is obvious best practice or already enforced by tooling."

6. **Populate `diary/lessons_learned.md` from existing docs**:

   > "Read the same docs. For each anti-pattern, failure mode, or hard-won rule you find — things the team learned through experience, not from a manual — write an entry in `diary/lessons_learned.md` using the `## slug-based-header` format with a one-sentence **Rule** and a **Why** section. Skip general advice; focus on project-specific lessons with a specific incident or failure behind them."

7. **Write `diary/session_context.md`**:

   > "Based on what you've read, write `diary/session_context.md`. The Current State section should be one paragraph describing what the system is and what state it's in right now. Leave Most Recent Sessions empty — that will be filled in going forward. Populate Open Items with any known deferred work you found in the existing docs."

8. **Prune**: read all three files yourself. Remove:
   - Anything obvious from the code or standard in the framework
   - Anything already enforced by tests, linters, or CI
   - Any entry whose WHY section is "because we always do it this way"
   - Any entry without a specific incident or reasoning behind it

9. **Run `/startup`** to confirm the briefing makes sense and captures what a new contributor would actually need to know.

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

```

*(Leave empty below the header. The bootstrap session or first real session will add the first entry.)*

---

### `diary/lessons_learned.md`

```markdown
# Lessons Learned

Anti-patterns, failure modes, and hard-won rules. Most recent at top. Add an entry only when
a lesson is non-obvious — if it's standard practice or documented in the framework, skip it.

Cross-references use (→ slug-name) notation.

---

```

*(Leave empty below the header.)*

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
