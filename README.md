# Memtoad

Persistent, readable project memory for Claude Code. Three markdown files. Nine skills. No cloud sync, nothing archived out of reach; an optional git-tracked archive (enhanced memory) for diaries too big to read whole. Integrated with `/grill-me` logic to bring real-world longitudinal awareness to Claude Code interactions.

---

## What it is

Memtoad gives Claude persistent project memory across sessions without depending on provider-side memory features, external storage, or complex tooling. It stores three things:

- **What's happening now** — current work state and open items
- **Why things are the way they are** — architectural decisions with their reasoning
- **What to never repeat** — anti-patterns and hard-won lessons

### Design philosophy

Claude already has access to your code, your git history, and your file system. What it cannot reconstruct from those sources is the *narrative arc* of the project: the design choices that weren't obvious, the failure modes you discovered the hard way, the deferred work and why it was deferred.

Memtoad fills exactly that gap. The diary is not a substitute for git history, inline comments, or documentation — it supplements them by capturing context that wouldn't survive in any of those places.

The system is designed to stay lean. Sessions that produced no new decisions or lessons write one file. Sessions that did produce something new write up to three. There is no archiving, no fourth file. The files grow slowly, remain readable, and load in full on every session. When a diary outgrows that, enhanced memory (below) keeps the files as an Index plus digests with every full entry one pointer away.

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
│   ├── tidy/SKILL.md               # consolidates superseded architectural-decision entries
│   └── list/SKILL.md               # lists all available memtoad commands
└── commands/
    ├── bootstrap.md
    ├── startup.md
    ├── session-historian.md
    ├── grill-me.md
    ├── committer.md
    ├── context-capture.md
    ├── skill-inventory.md
    ├── tidy.md
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
- Exception: `/tidy` may fold an entry and the entry it explicitly reverses (`This reverses (→ slug)`) into a single current entry. Nothing is deleted or archived — the older entry's reasoning is compressed into the merged entry's WHY, and its slug stays present as a `(supersedes slug)` header annotation so existing cross-references still resolve.

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

## Enhanced memory (optional): the memstore

A diary that is read whole every session works until it doesn't: in the project this was built in, the two big files reached 560 KB (about 140k tokens) and could no longer be loaded. Enhanced memory keeps the three files and changes what the two big ones hold:

| Tier | Holds | Read |
| :--- | :--- | :--- |
| **Index** (top of `architectural_decisions.md` and `lessons_learned.md`) | one line per entry: title, date, status; newest first | every session, first |
| **Digests** (below the Index, same order) | one paragraph per entry: the rule, the exact names, the reason, the prohibitions, ending in a `mem:diary/<file>#<slug>` pointer | when an Index line is relevant |
| **Store** (`diary/memstore/`, a chroma database tracked in git) | the exact full text of every entry, plus searchable chunks | on demand: `get <pointer>`, `search "<query>"` |
| **Git history** | every earlier version of the files | last resort |

In that project, 560 KB became about 210 KB, of which the two Indexes are 23 KB: about 6k tokens for the whole landscape. Nothing is archived out of reach. `compact` refuses to replace an entry unless the store already holds its exact text, `ingest` never deletes an entry, and the store cannot be dropped while it holds archived entries.

It is **opt-in** (`/bootstrap` step 0d) and stays out of the way when it is off: every skill checks for the `<!-- memtoad:store -->` block in `CLAUDE.md` and behaves exactly as before without it. With it on, and the package unavailable, the skills say so and stop; there is no silent fallback.

**Install** (into the project's own Python environment, 3.12+; `/bootstrap` does this):

```
pip install "memstore @ git+https://github.com/humantypo/memtoad.git#subdirectory=memstore"
```

Append `@<tag or commit>` to `memtoad.git` to pin a version, and pin the installed `chromadb` version in the project's requirements: the store records the chromadb version that wrote it and refuses another (`export` with the old version, `import` with the new, to move). The first use downloads chroma's default embedding model to `~/.cache/chroma`.

**Commands** (`python -m memstore ...`, from the repository root):

| Command | Purpose |
| :--- | :--- |
| `index` | the session-start read: both Indexes, plus full entries not yet digested |
| `get mem:diary/<file>#<slug>` | the exact original entry |
| `search "query" [--where k=v]` | semantic search over entry chunks |
| `ingest diary [--dry-run]` | archive every entry still present in full; idempotent; never deletes an entry |
| `compact <file> --digests FILE.json [--dry-run]` | replace archived entries with digests (`{slug: text}`) and rebuild the Index |
| `check-pointers` | every digest resolves to its exact archived entry, the Index is current, every `mem:` pointer in the repo's markdown resolves |
| `status`, `export --out FILE`, `import FILE`, `reindex` | counts; a text safety copy; refill a fresh store; re-embed after an embedding change |

**What changes in the skills when it is on:** `startup` runs inline and reads the Indexes, not the files; `session-historian` writes new entries below the digest region, then ingests, digests (in the house style, written by the model that has the session context), compacts and checks pointers; `committer` stages `diary/memstore/` with the rest of `diary/`; `grill-me` reads the Index and drills down; `tidy` acts only on full entries.

**Tracked-file notes.** `.gitattributes` marks `diary/memstore/** binary`. Later commits are small (about 20 KB for an edited entry), but any read touches one counter row in `chroma.sqlite3`, so `git status` can show the store modified after a mere `search`. Never run the `chroma` CLI on the store. The package lives in `memstore/` in this repository (`python -m pytest memstore/tests`); a project can register its own sources under the `memstore.sources` entry-point group.

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
4. Offers enhanced memory (opt-in): installs `memstore` into the project's Python environment, adds the `<!-- memtoad:store -->` block to CLAUDE.md, the `.gitattributes` line and an empty digest region to the two big files, and, for an existing diary, offers the first compaction

**Phase 1 — Inspect**: reads CLAUDE.md, README.md, package manifests, docs directory, and recent git log.

**Phase 2 — Q&A**: three targeted questions about current state gaps, non-obvious architectural decisions, and hard-won lessons.

**Phase 3 — Write**: populates all three diary files with first-draft entries. Removes sentinel markers from files it writes.

The skill detects which files already have entries (via the `<!-- memtoad:uninitialized -->` sentinel) and skips or merges accordingly. Safe on partially-initialized diaries.

**File**: `skills/bootstrap/SKILL.md`

```markdown
---
name: bootstrap
description: Set up Memtoad for a project and populate the diary. Creates diary/ directory and files, injects CLAUDE.md Project Memory section, configures .gitignore, optionally enables enhanced memory (the memstore archive), then inspects the codebase and asks targeted questions to write first-draft diary entries. Run once after installing the plugin in a new project. Safe to re-run — idempotent setup, sentinel-based population.
---
```

**When to invoke**: once, immediately after installing the plugin in any project.

---

### `startup` — loads diary at session start

Spawns a subagent to read all three diary files and synthesize a briefing. Runs from cold — the main conversation has no context yet, so spawning is appropriate here.

With enhanced memory on, it runs **inline** instead: `index` prints both Indexes, it reads `session_context.md` and any not-yet-digested `[FULL]` entries, and it drills into a digest or `get <pointer>` only when an Index line bears on the task. If the memstore command fails it says so and stops.

**File**: `skills/startup/SKILL.md`

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
- Most recent entries at the top in all three files (with enhanced memory: new full entries go directly below the digest region, see below)
- Cross-references use `(→ slug-name)` notation, not numbers
- Nothing is archived out of reach: without the store the files grow without rotation; with it, every entry stays one pointer away
```

With enhanced memory on, the skill then archives each new entry (`ingest diary`), writes its digest in the house style, runs `compact` (dry run first) and `check-pointers` (0 errors), and proofreads each digest against its entry before staging. The full steps and the digest style are in `skills/session-historian/SKILL.md`.

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

### `tidy` — consolidates superseded architectural decisions

Runs **inline in the main conversation** (no agent spawn) — the target file is small by design, and the merge decisions benefit from being visible to the user as they're made, not returned as a finished diff from a subagent.

`architectural_decisions.md` and `lessons_learned.md` are deliberately append-only — archiving by date or size was tried once in a predecessor system and rejected, because archived content stopped being read (→ three-files-no-archiving, → archive-files-are-never-read). `tidy` doesn't reopen that decision. It solves a narrower problem: over time, a decision and its later reversal both stay in the file as two full entries, even though only the current one is operative. `tidy` scans for the explicit `This reverses (→ slug)` phrase, pairs each reversal with the entry it reverses, and — for pairs where the older slug isn't relied on elsewhere in the file — drafts a single merged entry that keeps the current decision as the operative text and compresses the older entry into one clause of the WHY, rather than dropping it. The older slug survives as a `(supersedes slug)` annotation on the merged header, so it stays literal, greppable text.

It never merges on inferred topic similarity, never touches `lessons_learned.md` (no authored supersession convention exists there) or `session_context.md` (already fully rewritten every session), and never runs automatically. It shows every candidate pair as a before/after comparison and applies only the ones the user confirms, then leaves the change unstaged for normal review.

**File**: `skills/tidy/SKILL.md`

**When to invoke**: on demand, once a project's `architectural_decisions.md` has accumulated a few reversal pairs and is starting to feel repetitive to read in full.

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
| `/tidy` | Consolidate superseded architectural-decision entries |
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

With enhanced memory on, bootstrap adds a `<!-- memtoad:store -->` block after that list. It says the two big files are Index + digests and names the **memstore command** for this project (the environment activation plus `python -m memstore`). Every skill reads its command from there, so nothing in the plugin assumes a particular Python environment.

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

**No archiving.** The old system archived files when they grew large. Modern context windows make this obsolete, and archived files are never read. Let the files grow. Enhanced memory is not archiving in that sense: every entry keeps a digest in the file that is read every session, and the digest points at the exact full text.

**Conditional writes.** Session-historian always updates `session_context.md`. It only touches the other two files when something genuinely new was decided or learned. Most sessions produce only one update.

**Commit with the code, not after.** Use `/committer` to update and stage `diary/` before you commit — don't leave the diary for a follow-up commit. A plugin hook (`hooks/check-diary-staged.sh`) enforces this at the harness level rather than relying on a CLAUDE.md instruction the model might skip. Do not reference the commit hash in diary entries — it isn't known yet, and git log is the authoritative record.

**Slugs, not numbers.** Numbered lessons rot when you reorder or delete entries. Slugs are self-describing and survive restructuring. `(→ null-key-defers-failure)` tells you what it is; `(→ Lesson 228)` tells you nothing.

**Plugin, not installed.** Skills are firmware — they should improve without requiring per-project updates. The plugin architecture delivers skills globally; only the `diary/` files are per-project. When Memtoad improves, update the plugin once and all projects benefit.
