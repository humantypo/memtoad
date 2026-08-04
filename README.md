# Memtoad

Persistent, readable project memory for Claude Code. Three markdown files. Eight skills. No database, no cloud sync, no archiving. Integrated with `/grill-me` logic to bring real-world longitudinal awareness to Claude Code interactions.

---

## What it is

Memtoad gives Claude persistent project memory across sessions without depending on provider-side memory features, external storage, or complex tooling. It stores three things:

- **What's happening now** — current work state and open items
- **Why things are the way they are** — architectural decisions with their reasoning
- **What to never repeat** — anti-patterns and hard-won lessons

### Design philosophy

Claude already has access to your code, your git history, and your file system. What it cannot reconstruct from those sources is the *narrative arc* of the project: the design choices that weren't obvious, the failure modes you discovered the hard way, the deferred work and why it was deferred.

Memtoad fills exactly that gap. The diary is not a substitute for git history, inline comments, or documentation — it supplements them by capturing context that wouldn't survive in any of those places.

The system is designed to stay lean. Sessions that produced no new decisions or lessons write one file. Sessions that did produce something new write up to three. There is no archiving, no fourth file. The files grow slowly, remain readable, and load in full on every session.

### Why named Memtoad

The name is a portmanteau of *Memento* and *Toad*. Memento — the film — encodes memory into persistent physical artifacts (tattoos, polaroids, notes) because short-term recall can't be trusted across sessions. Toad — from Arnold Lobel's *Frog and Toad* — is the deliberate one: the list-maker, the keeper of plans, the character who writes things down so he doesn't forget. Frog improvises. Toad remembers.

Claude is Frog. The diary is Toad's list.

---

## Installation

Memtoad is a Claude Code plugin, distributed via its own marketplace manifest (`.claude-plugin/marketplace.json`). Install it once and it's available in every project. It's a two-step process: register the marketplace, then install the plugin from it.

```
/plugin marketplace add humantypo/memtoad
/plugin install memtoad@memtoad
```

No shell scripts, no per-project file copying. Skills and commands are available globally in all Claude Code sessions once the plugin is installed.

### Set up a new project

Open Claude Code in any project directory and run:

```
/bootstrap
```

Bootstrap handles everything: creates the `diary/` directory, writes the three starter files, injects a `## Project Memory` section into `CLAUDE.md`, configures `.gitignore`, then inspects the codebase and populates the diary entries. One command, full setup.

---

## File structure

In any target project after `/bootstrap`:

```
project-root/
├── diary/
│   ├── session_context.md          # current state, open items
│   ├── architectural_decisions.md  # WHY things are designed the way they are
│   └── lessons_learned.md          # anti-patterns, failure modes, hard-won rules
└── CLAUDE.md                       # gets a ## Project Memory section pointing to diary/
```

**Memtoad plugin structure** (the repo):

```
memtoad/
├── .claude-plugin/
│   └── plugin.json                 # plugin manifest
├── hooks/
│   ├── hooks.json                  # registers the two hooks below
│   ├── check-diary-staged.sh       # PreToolUse: denies `git commit` until diary/ is staged
│   └── record-commit.sh            # PostToolUse: updates historian_state.json after a real commit
├── skills/
│   ├── bootstrap/SKILL.md          # sets up + populates diary for a project
│   ├── startup/SKILL.md            # reads 3 diary files, synthesizes a briefing
│   ├── session-historian/SKILL.md  # writes diary entries at end of session
│   ├── grill-me/SKILL.md           # interrogates a plan informed by project context
│   ├── committer/SKILL.md          # updates + stages the diary before a commit
│   ├── context-capture/SKILL.md    # captures WIP state for context continuity
│   ├── skill-inventory/SKILL.md    # audits all visible skills — local, plugin, built-in
│   └── list/SKILL.md               # lists all available memtoad commands
└── commands/
    ├── bootstrap.md
    ├── startup.md
    ├── session-historian.md
    ├── grill-me.md
    ├── committer.md
    ├── context-capture.md
    ├── skill-inventory.md
    └── list.md
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

**Update rule**: Always rewritten by `/session-historian` and `/committer`. This is the one file that changes every session.

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

### `bootstrap` — sets up and populates a project

Run once in any project directory after installing the plugin. Bootstrap is the complete project initialization tool: it sets up the diary filesystem, injects the CLAUDE.md section, configures `.gitignore`, inspects the codebase and available docs, then conducts a targeted Q&A to surface what code inspection alone cannot reveal.

**Phase 0 — Project setup** (idempotent, safe to re-run):
1. Creates `diary/` with three starter files containing sentinel markers if not already present
2. Injects `## Project Memory` section into CLAUDE.md (or creates CLAUDE.md) if not already present
3. Asks which gitignore mode to use and configures `.gitignore`:
   - **Shared** — all diary files tracked; best for solo projects
   - **Hybrid** — tracks decisions + lessons, ignores `session_context.md`; recommended for teams
   - **Private** — ignores entire `diary/` and `CLAUDE.md`; each contributor manages diary locally

**Phase 1 — Inspect**: reads CLAUDE.md, README.md, package manifests, docs directory, and recent git log.

**Phase 2 — Q&A**: three targeted questions about current state gaps, non-obvious architectural decisions, and hard-won lessons.

**Phase 3 — Write**: populates all three diary files with first-draft entries. Removes sentinel markers from files it writes.

The skill detects which files already have entries (via the `<!-- memtoad:uninitialized -->` sentinel) and skips or merges accordingly. Safe on partially-initialized diaries.

**File**: `skills/bootstrap/SKILL.md`

```markdown
---
name: bootstrap
description: Set up Memtoad for a project and populate the diary. Creates diary/ directory and files, injects CLAUDE.md Project Memory section, configures .gitignore, then inspects the codebase and asks targeted questions to write first-draft diary entries. Run once after installing the plugin in a new project. Safe to re-run — idempotent setup, sentinel-based population.
---
```

**When to invoke**: once, immediately after installing the plugin in any project.

---

### `startup` — loads diary at session start

Spawns a subagent to read all three diary files and synthesize a briefing. Runs from cold — the main conversation has no context yet, so spawning is appropriate here.

**File**: `skills/startup/SKILL.md`

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

Supports two modes (decision logic handled by `/committer`):
- **FULL** — updates all three files as appropriate; used for sessions with code changes or significant work
- **LIGHTWEIGHT** — updates only `session_context.md`; used for documentation-only commits

Direct `/session-historian` invocations always run FULL.

**File**: `skills/session-historian/SKILL.md`

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
```

**When to invoke**: directly at the end of any significant session; or via `/committer` which decides the mode for you before a commit.

---

### `committer` — updates and stages the diary before a commit

Checks what's staged, decides whether to run a FULL or LIGHTWEIGHT session-historian pass, updates the diary accordingly, and stages `diary/`. Runs inline, no agent spawn.

**FULL** mode runs if any staged file has a code file extension (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.rb`, `.java`, `.rs`, `.cs`, `.cpp`, `.c`, `.swift`, `.kt`, `.sh`, `.bash`), if any staged file has added or deleted status (`A` or `D`), if `commits_since_last_full ≥ 5`, or if the last full run was more than 3 days ago.

**LIGHTWEIGHT** mode runs for documentation-only commits (only `diary/`, `CLAUDE.md`, `.claude/`, or `.md` files staged) — or skips the diary update entirely if every staged path is already documentation-only.

`committer` does not draft a commit message or run `git commit` itself — that's redundant with what any agent harness already does unprompted. It stops once the diary is updated and staged. The `commits_since_last_full` / `last_full_run_date` state at `~/.claude/projects/<project-path>/historian_state.json` is now written by the `record-commit` hook (see below), not by `committer`, since `committer` no longer knows when — or whether — a commit actually happens.

**File**: `skills/committer/SKILL.md`

**When to invoke**: before committing, when staged changes include more than documentation. Tests should pass before invoking.

---

### Hooks — enforcing the diary update at the harness level

A CLAUDE.md instruction to "run `/committer` before committing" is advisory: committing is a default behavior agent harnesses already know how to do unprompted, so the instruction is easy to silently skip. Memtoad instead ships two hooks (`hooks/hooks.json`) that register automatically for every project with the plugin installed — no per-project setup, and they travel with `claude plugin update` exactly like skills do.

**`check-diary-staged.sh`** (`PreToolUse`, matched on `Bash`): inspects any `git commit` invocation. If the project has no `diary/` directory, or every staged file is documentation-only, or `diary/` already has staged changes, it allows the commit silently. Otherwise it denies the commit with a reason pointing back to `/memtoad:committer`.

**`record-commit.sh`** (`PostToolUse`, matched on `Bash`): after a `git commit` that actually created a new commit (detected by comparing `HEAD` against the last commit hash it saw), updates `historian_state.json` — incrementing `commits_since_last_full`, or resetting it and recording `last_full_run_commit`/`last_full_run_date` if the commit touched `diary/architectural_decisions.md`.

Both scripts no-op immediately for any project without a `diary/` directory, so installing the plugin never gates commits in projects that haven't adopted Memtoad's diary convention.

---

### `grill-me` — interrogates a plan using project context

Interviews the user about a plan or design until reaching shared understanding. Reads all three diary files first, then outputs 1–2 sentences naming any constraints, decisions, or patterns directly relevant to the stated task — letting the user correct misreadings before the interrogation begins. If nothing in the diary bears on the task, it skips this acknowledgment and proceeds silently.

Uses `AskUserQuestion` for every question (not just binary choices), with 2–4 concrete multiple-choice options per question. Asks one question at a time and waits for the answer before proceeding.

This is the key integration between the historian and the interviewer: grill-me can surface "we already made this decision" or "we learned this lesson the hard way" before the user has a chance to repeat a mistake.

**File**: `skills/grill-me/SKILL.md`

```markdown
---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Reads project diary first to surface relevant constraints. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---
```

**When to invoke**: when stress-testing a plan, before starting a significant new feature, or when the user says "grill me on this."

---

### `context-capture` — preserves WIP state across context events

Spawns a subagent to update `diary/session_context.md` with the current work-in-progress state. Use when Claude Code's context is about to be compressed, when switching tasks mid-session, or to checkpoint significant progress before it's lost.

**File**: `skills/context-capture/SKILL.md`

```markdown
---
name: context-capture
description: Capture current work-in-progress state to diary/session_context.md for continuity across compact events. Use after significant progress, before context might be lost, or to check what was previously being worked on.
---
```

**When to invoke**: proactively after significant progress, or reactively when context compression is expected.

---

### `skill-inventory` — audits every visible skill

Spawns a subagent to sweep the current environment for skills — this project's own skills, skills from installed plugins (resolved via `~/.claude/plugins/installed_plugins.json` and their cached `skills/*/SKILL.md` files), and provider built-ins that have no backing file (`/compact`, `/clear`, etc.). Runs as a spawn for the same reason `startup` does: it's a cold filesystem sweep unrelated to the conversation so far, and doing the file reading inline would burn the main context window for no benefit.

Classifies every skill found as **local**, **plugin** (with plugin name, version, commit, and whether the marketplace has moved past that commit), or **built-in**, then reports:

- an inventory table of everything found
- what's new since the last run (see state file below)
- overlapping skills that cover the same ground
- gaps against a fixed software-development-lifecycle checklist (planning, coding, testing, code review, security review, docs, dependency management, deployment, incident response, memory/context continuity)
- hard stops (unconditional gating language, e.g. "always ask before...") vs soft stops (gating conditional on mode, settings, or staged files)
- each skill's tool/permission footprint, from `allowed-tools:` frontmatter when present or a best-effort text scan otherwise
- a composition graph of which skills invoke other skills or subagents
- staleness — plugins with an available update, or local skill files referencing paths that no longer exist

Tracks first/last-seen dates and a description hash per skill in a state file at `~/.claude/projects/<project-path>/skill_inventory_state.json` — the same per-project path convention `committer` uses for `historian_state.json`. This is bookkeeping, not diary content, so it lives outside `diary/` entirely.

**File**: `skills/skill-inventory/SKILL.md`

**When to invoke**: on demand, when auditing skills/plugins or checking what's new since the last audit. Never runs automatically at session start.

---

### `list` — shows available commands

Lists all Memtoad slash commands with one-line descriptions. Useful when you can't remember what's available.

**File**: `skills/list/SKILL.md`

**When to invoke**: any time you want to see what Memtoad commands are available.

---

## Command wrappers

Each skill has a corresponding command wrapper in `commands/` that enables it as a slash command. The wrappers are intentionally thin — they exist to expose the skill via the `/command-name` interface, not to duplicate the skill logic.

| Command | What it does |
|---|---|
| `/bootstrap` | Set up + populate diary for this project |
| `/startup` | Load full project context at session start |
| `/committer` | Update + stage the diary before a commit |
| `/session-historian` | Write diary entries for the current session |
| `/grill-me` | Stress-test a plan with diary-informed questions |
| `/context-capture` | Checkpoint WIP state to the diary |
| `/skill-inventory` | Audit all visible skills — local, plugin, built-in |
| `/list` | Show all available Memtoad commands |

---

## CLAUDE.md integration

Bootstrap injects this block near the top of the root `CLAUDE.md` in any target project:

```markdown
## Project Memory
<!-- memtoad:version:3 -->
- [diary/session_context.md](diary/session_context.md) — current state and recent work
- [diary/architectural_decisions.md](diary/architectural_decisions.md) — design principles and non-negotiable patterns
- [diary/lessons_learned.md](diary/lessons_learned.md) — anti-patterns and hard-won insights

Commits that touch more than documentation are gated on `diary/` being staged — a plugin hook denies `git commit` otherwise. Run `/committer` first to update and stage the diary.
```

The `<!-- memtoad:version:3 -->` marker allows future bootstrap runs to detect and offer to refresh stale sections.

For component-level `CLAUDE.md` files (inside a subdirectory like `frontend/` or `api/`), use relative paths for the diary links:

```markdown
## Project Memory
<!-- memtoad:version:3 -->
- [diary/session_context.md](../diary/session_context.md) — current state and recent work
- [diary/architectural_decisions.md](../diary/architectural_decisions.md) — design principles and non-negotiable patterns
- [diary/lessons_learned.md](../diary/lessons_learned.md) — anti-patterns and hard-won insights
```

---

## Diary file templates

Bootstrap creates these files with sentinel markers when setting up a new project. They are embedded directly in `skills/bootstrap/SKILL.md`.

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

### `diary/lessons_learned.md`

```markdown
# Lessons Learned

Anti-patterns, failure modes, and hard-won rules. Most recent at top. Add an entry only when
a lesson is non-obvious — if it's standard practice or documented in the framework, skip it.

Cross-references use (→ slug-name) notation.

---

<!-- memtoad:uninitialized -->
```

---

## Design principles

These constrain how the system evolves. If you fork or extend it, respect them.

**Supplement, don't duplicate.** The diary captures what git history and code cannot: the narrative arc and the non-obvious WHY. Implementation details belong in the code. Timelines belong in git log. The diary is not a substitute for either.

**Three files, no more.** The archive explosion that Memtoad was designed to replace happened because files multiplied without bound. Resist the urge to add a fourth file for bugs, a fifth for refactoring history. Bugs worth remembering become lessons. Refactors worth remembering become decisions. If it doesn't fit the three files, it probably doesn't belong in the diary.

**Inline, not spawned — except startup, context-capture, and skill-inventory.** Session-historian and committer run in the main conversation, which already has session context. Spawning an agent to re-derive context you already have is the expensive path. Startup spawns because it genuinely starts cold. Context-capture spawns to snapshot state independently of the current conversation thread. Skill-inventory spawns for the same reason as startup — it's a cold sweep over plugin caches and marketplace clones that has nothing to do with the conversation so far, and doing that reading inline would waste the main context window. Grill-me runs inline because it needs AskUserQuestion, which agents cannot use.

**No archiving.** The old system archived files when they grew large. Modern context windows make this obsolete, and archived files are never read. Let the files grow.

**Conditional writes.** Session-historian always updates `session_context.md`. It only touches the other two files when something genuinely new was decided or learned. Most sessions produce only one update.

**Commit with the code, not after.** Use `/committer` to update and stage `diary/` before you commit — don't leave the diary for a follow-up commit. A plugin hook (`hooks/check-diary-staged.sh`) enforces this at the harness level rather than relying on a CLAUDE.md instruction the model might skip. Do not reference the commit hash in diary entries — it isn't known yet, and git log is the authoritative record.

**Slugs, not numbers.** Numbered lessons rot when you reorder or delete entries. Slugs are self-describing and survive restructuring. `(→ null-key-defers-failure)` tells you what it is; `(→ Lesson 228)` tells you nothing.

**Plugin, not installed.** Skills are firmware — they should improve without requiring per-project updates. The plugin architecture delivers skills globally; only the `diary/` files are per-project. When Memtoad improves, update the plugin once and all projects benefit.
