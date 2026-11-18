# Memtoad

Persistent, readable project memory for Claude Code. Three markdown files. Nine skills. No cloud sync. Integrated with `/grill-me` logic to bring real-world longitudinal awareness to Claude Code interactions.

> **2.0: a diary that stays trustworthy for the life of a project**
> - **Enhanced memory (optional, since 1.4).** A local, git-tracked database (`diary/memstore/`) keeps the exact full text of every architectural decision and lesson. Each session reads a compact Index instead of the whole diary and fetches a full entry only when it needs one. Entries can stay detailed, and the diary can keep growing for the life of the project without overflowing the context window. It is off by default. Turn it on with `/bootstrap`; see [Enable enhanced memory](#enable-enhanced-memory-optional).
> - **New in 2.0: a diary that stays current.**
>   - Entries that stop applying are [labelled](#keeping-the-diary-current-labels) `superseded by` or `retired` instead of deleted. This happens when a new entry replaces one, or with evidence during a `/tidy` pass.
>   - The session log keeps only active work, and a short Arc records where the project has been.
>   - The review cadence is shared through git rather than kept on each machine.
>   - Upgrading an existing project? See [Upgrading from 1.x](#upgrading-from-1x).

---

## What it is

Memtoad gives Claude persistent project memory across sessions without depending on provider-side memory features, external storage, or complex tooling. It stores three things:

- **What's happening now** — current work state and open items
- **Why things are the way they are** — architectural decisions with their reasoning
- **What to never repeat** — anti-patterns and hard-won lessons

Entries are never deleted. One that stops applying is labelled `superseded by` or `retired` in its heading, so the diary stays trustworthy while still showing what was tried and what did not work.

By default all three are plain markdown files that load in full each session. With **enhanced memory** turned on, decisions and lessons are also archived word for word in a local, git-tracked database. Only a one-line-per-entry Index and short digests stay in the files, so the diary can grow far past what a session could read whole.

### Design philosophy

Claude already has access to your code, your git history, and your file system. What it cannot reconstruct from those sources is the *narrative arc* of the project: the design choices that weren't obvious, the failure modes you discovered the hard way, the deferred work and why it was deferred.

Memtoad fills exactly that gap. The diary is not a substitute for git history, inline comments, or documentation — it supplements them by capturing context that wouldn't survive in any of those places.

The system is designed to stay lean. Sessions that produced no new decisions or lessons write one file. Sessions that did produce something new write up to three. There is no fourth diary file. The files grow slowly, remain readable, and load in full on every session. A long-lived or detail-heavy diary eventually outgrows that. [Enhanced memory](#enhanced-memory-optional-the-memstore) then keeps the same three files, holding an Index plus digests, and puts every full entry in a store one pointer away. Nothing is lost or hidden; it is just no longer all read up front.

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

Bootstrap handles everything: creates the `diary/` directory, writes the three starter files, injects a `## Project Memory` section into `CLAUDE.md`, configures `.gitignore`, then inspects the codebase and populates the diary entries. One command, full setup. Bootstrap also asks whether to enable enhanced memory (below); "Not now" gives you the plain three-file diary.

### Enable enhanced memory (optional)

Enhanced memory is worth turning on when you want long, detailed decision and lesson entries, or when the diary has grown big enough that loading it each session is slow or no longer fits. It changes only `architectural_decisions.md` and `lessons_learned.md`; `session_context.md` stays as it is.

**Prerequisites**
- Python 3.12+ in the project's environment (venv, conda, or the `python` on PATH)
- Network access once, to install the `memstore` package (it pulls in `chromadb`) and to download chroma's default embedding model to `~/.cache/chroma` on first use

**New project:** run `/bootstrap`. At step 0d, choose **Enable**.

**Existing Memtoad project:** run `/bootstrap` again. Setup is idempotent:
1. It asks the git tracking question again. Pick your current mode; an existing `# Memtoad` block in `.gitignore` is left untouched.
2. At step 0d, choose **Enable** and name the project's Python environment. Bootstrap then:
   - installs `memstore`;
   - adds a `<!-- memtoad:store -->` block to `CLAUDE.md` and a `diary/memstore/** binary` line to `.gitattributes`;
   - archives your existing entries;
   - offers the **first compaction**, which rewrites both files as Index plus digests. It runs only with your go-ahead and only for entries already archived verbatim.
3. When it asks whether to merge new entries into the already-populated diary, choose abort if you only came to enable enhanced memory.

**Afterwards:**
- Bound chromadb in the project's requirements, with the installed version as the floor, e.g. `chromadb>=1.5.9,<2`, not an exact pin. Any version that keeps the store's format opens it (see [chromadb versions](#chromadb-versions)).
- Commit `diary/memstore/` along with the rest of `diary/` (`/committer` stages it). Unless you chose Private tracking, that database is shared with everyone who clones the repo.
- Nothing else changes in how you work: `/startup`, `/session-historian`, `/committer`, `/grill-me` and `/tidy` detect the `CLAUDE.md` block and switch to the Index-and-store flow automatically.

There is no automated way back. To turn it off:
1. Put each full entry back in the file, using `get <pointer>` or the pre-compaction version in git history.
2. Remove the `<!-- memtoad:store -->` block from `CLAUDE.md`.

If you skip step 1, the files hold only digests.

Details, commands and guarantees: [Enhanced memory (optional): the memstore](#enhanced-memory-optional-the-memstore).

### Upgrading from 1.x

2.0 removes a hook and changes how three skills write the diary, so read this before the first session on an existing project.

1. **Update the plugin** on each machine: `claude plugin marketplace update`, then `claude plugin update`, then restart Claude Code. Installed plugins are pinned copies, so pushing a new version does not reach them on its own.
2. **If the project uses enhanced memory,** upgrade its `memstore` package too. The 2.0 skills call `set-label` and `restore`, which memstore 0.2.0 does not have, and re-running `/bootstrap` does not reinstall it:
   ```
   pip install --upgrade "memstore @ git+https://github.com/humantypo/memtoad.git@v2.0.1#subdirectory=memstore"
   ```
   If the project's requirements pin `chromadb==<version>` exactly (the 1.x advice), loosen it to `chromadb>=<version>,<2`. Since memstore 0.3.1 any chromadb with the same store format works ([chromadb versions](#chromadb-versions)).
3. **Keep a copy of your session history if you want it.** The first 2.0 historian run trims "Most Recent Sessions" to the current session and the one before it. It lists what it drops when the file is untracked (hybrid and private mode), but those notes then exist nowhere else. Copy `diary/session_context.md` aside first if you want to keep them.
4. **Expect the first `/committer` run to be FULL.** The `Last full review:` line does not exist yet, which reads as "never". That run adds the line.
5. **Run `/tidy` once.** A 1.x diary has stale entries that no capture-time check ever labelled. The review pass proposes labels and corrections with evidence, and you confirm each.

Nothing else needs doing:
- `~/.claude/projects/<project-path>/historian_state.json` is no longer read and can be deleted.
- Existing digest leads ending in `, active` are harmless; `set-label` removes the word when it labels one.

---

## File structure

In any target project after `/bootstrap`:

```
project-root/
├── diary/
│   ├── session_context.md          # current state, open items
│   ├── architectural_decisions.md  # WHY things are designed the way they are
│   ├── lessons_learned.md          # anti-patterns, failure modes, hard-won rules
│   └── memstore/                   # enhanced memory only: chroma store, full text of every entry (tracked)
├── .gitattributes                  # enhanced memory only: diary/memstore/** binary
└── CLAUDE.md                       # gets a ## Project Memory section pointing to diary/
                                    #   (+ a <!-- memtoad:store --> block when enhanced memory is on)
```

**Memtoad plugin structure** (the repo):

```
memtoad/
├── .claude-plugin/
│   ├── plugin.json                 # plugin manifest
│   └── marketplace.json            # marketplace manifest (for /plugin marketplace add)
├── hooks/
│   ├── hooks.json                  # registers the hook below
│   └── check-diary-staged.sh       # PreToolUse: denies `git commit` until diary/ is staged
├── skills/
│   ├── bootstrap/SKILL.md          # sets up + populates diary for a project
│   ├── startup/SKILL.md            # reads 3 diary files, synthesizes a briefing
│   ├── session-historian/SKILL.md  # writes diary entries at end of session
│   ├── grill-me/SKILL.md           # interrogates a plan informed by project context
│   ├── committer/SKILL.md          # updates + stages the diary before a commit
│   ├── context-capture/SKILL.md    # captures WIP state for context continuity
│   ├── skill-inventory/SKILL.md    # audits all visible skills — local, plugin, built-in
│   ├── tidy/SKILL.md               # labels superseded/retired entries, folds reversals, with evidence
│   └── list/SKILL.md               # lists all available memtoad commands
├── commands/
│   ├── bootstrap.md
│   ├── startup.md
│   ├── session-historian.md
│   ├── grill-me.md
│   ├── committer.md
│   ├── context-capture.md
│   ├── skill-inventory.md
│   ├── tidy.md
│   └── list.md
└── memstore/                       # optional enhanced-memory package (pip install from this subdirectory)
    ├── pyproject.toml
    ├── src/memstore/               # store (chroma, guards), diary adapter (ingest, compact, index), check-pointers, CLI
    └── tests/                      # python -m pytest memstore/tests (stub embedder, no model download)
```

---

## The three diary files

### `diary/session_context.md`

**Purpose**: The current state of the project and the work in progress. Always rewritten, never stale, never a history.

**Sections**:
- **Arc** — one line per milestone (a version or phase): what changed and why it mattered. This is the record of where the project has been, so the session log does not have to be.
- **Current State** — one paragraph: production status, key system facts, active test counts, infrastructure state. Not a feature list — a snapshot.
- **Most Recent Sessions** — the current session and the one before it, counted by date, plus any older note whose work is still in flight. Each: date, what was done (WHY-focused narrative, not a file list), cross-refs to lessons or decisions if any. Before a note drops off, anything durable in it moves to a decision, a lesson or Open Items; when the file is untracked (hybrid and private mode), the historian lists what it drops.
- **Open Items** — numbered list of deferred work with enough context to resume.
- **Key Diary Files** — links to the other two files.

**What belongs**: narrative description of work done (the reasoning behind it, not just the outcome), deferred items with their deferral rationale, cross-references to new decisions or lessons.

**What doesn't belong**:
- Per-file change lists ("modified `foo.py` at line 34 to add param `bar`")
- Code snippets
- "Status: COMPLETE" announcements
- Verification steps ("tests pass", "build green")
- Commit hashes, dates, or file paths of changes (git has those)

**Update rule**: Always rewritten by `/session-historian` and `/committer`. This is the one file that changes every session. A second run on the same day updates that day's note rather than adding another.

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
- Append-only — no archiving, no deleting. An entry that stops applying gets a [label](#keeping-the-diary-current-labels) in its heading.
- A `Last full review: <Month D, YYYY>` line near the top, set by every FULL historian run. `/committer` reads it to decide when the next FULL run is due.
- Exception: in a plain diary, `/tidy` may fold an entry and the entry it explicitly reverses (`This reverses (→ slug)`) into a single current entry. Nothing is deleted or archived — the older entry's reasoning is compressed into the merged entry's WHY, and its slug stays present as a `(…, supersedes slug)` header annotation so existing cross-references still resolve.

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
- Append-only — no archiving, no deleting; a lesson that no longer applies is labelled like a decision

---

## Keeping the diary current (labels)

Over years, some entries stop being true. A later decision reverses one, the code another governs is removed, the mechanism a third names is replaced. A stale entry that still reads as a current rule misleads every session after it. Deleting it would lose what it recorded about what was tried and why it stopped working. So Memtoad **labels** it instead, inside the heading's date parenthetical:

```markdown
## pre-commit-workflow-in-claude-md (June 2026; superseded by committer-diary-prep-only)
## old-sync-queue (March 2025; retired Nov 2026: the queue was removed with the v1 API)
```

- An unlabelled entry is in force. There is no `active` label, because a positive status goes stale on its own.
- The target of `superseded by` may be in either file.
- A retirement reason is one clause, at most 120 characters, with no parentheses.
- Labelling changes the heading only: the slug, the date, every `(→ slug)` reference and every `mem:` pointer stay valid, and no text is removed.
- `/startup` and `/grill-me` treat a labelled entry as history and as a record of what did not work, never as a current rule. With enhanced memory, the Index lists labelled entries last, under **No longer in force**, each with its reason or successor.

Labels are applied at two moments only:

1. **At capture.** For every new decision or lesson, `/session-historian` asks one question: does this replace or retire an existing entry? If so, it writes `This reverses (→ old-slug)` in the new entry and labels the old one. This is the most reliable moment, because the session that made the change knows what it replaced.
2. **On demand, with `/tidy`.** A review pass for what capture missed, including a diary that predates 2.0. Every proposal comes with evidence, and nothing is written until you confirm.

There are no schedules, counters or age rules. Age alone never retires anything: the predecessor system lost its most valuable early lessons by archiving by age (→ `archive-files-are-never-read`). There is also no purge. With enhanced memory the store is tracked in git, so deleting from it would not even shrink the repository.

---

## Enhanced memory (optional): the memstore

A diary that is read whole every session works until it doesn't: in the project this was built in, the two big files reached 560 KB (about 140k tokens) and could no longer be loaded. Enhanced memory removes that ceiling. You can write decisions and lessons at whatever length they deserve and keep them for the life of the project, because a session reads only the Index and pulls a full entry when it needs one. It keeps the three files and changes what the two big ones hold:

| Tier | Holds | Read |
| :--- | :--- | :--- |
| **Index** (top of `architectural_decisions.md` and `lessons_learned.md`) | one line per entry: title and date, newest first; then, under **No longer in force**, labelled entries with their label | every session, first |
| **Digests** (below the Index, same order) | one paragraph per entry: the rule, the exact names, the reason, the prohibitions, ending in a `mem:diary/<file>#<slug>` pointer | when an Index line is relevant |
| **Store** (`diary/memstore/`, a chroma database tracked in git) | the exact full text of every entry, plus searchable chunks | on demand: `get <pointer>`, `search "<query>"` |
| **Git history** | every earlier version of the files | last resort |

In that project, 560 KB became about 210 KB, of which the two Indexes are 23 KB: about 6k tokens for the whole landscape. Nothing is archived out of reach. `compact` refuses to replace an entry unless the store already holds its exact text, `ingest` never deletes an entry, and the store cannot be dropped while it holds archived entries.

It is **opt-in** (`/bootstrap` step 0d; see [Enable enhanced memory](#enable-enhanced-memory-optional) for the walkthrough) and stays out of the way when it is off: every skill checks for the `<!-- memtoad:store -->` block in `CLAUDE.md` and behaves exactly as before without it. With it on, and the package unavailable, the skills say so and stop; there is no silent fallback.

**Install** (into the project's own Python environment, 3.12+; `/bootstrap` does this):

```
pip install "memstore @ git+https://github.com/humantypo/memtoad.git#subdirectory=memstore"
```

Append `@<tag or commit>` to `memtoad.git` to pin a version, and bound `chromadb` in the project's requirements: the installed version as the floor, `<2` as the ceiling. The first use downloads chroma's default embedding model to `~/.cache/chroma`.

#### chromadb versions

chromadb migrates a store's on-disk format when it opens it, and the migration is one way. The store is tracked in git and shared, so if one contributor's newer chromadb migrated it and they committed, everyone on the older version would be locked out. memstore guards against that without tying the project to one exact chromadb release:

- **Compatibility is decided from the format, not the version number.** chromadb records each format step in the store's `migrations` table. Before chromadb opens the store, memstore reads that table with `sqlite3` and compares it with the steps the installed chromadb applies, taken from a throwaway empty store and cached per version in `~/.cache/memstore`.
- **Same format:** it opens, whatever the version number. When the number differs from the one that created the store, memstore first opens and reads a throwaway copy, to prove this version can read it. Most chromadb releases fall here.
- **The installed chromadb would migrate it:** refused, with nothing changed. Either install the version the requirements name, or move the whole project forward deliberately: run `upgrade-store` and raise the chromadb floor in the same commit.
- **The store is newer than the installed chromadb:** refused, because chromadb itself would open it without complaint. Upgrade chromadb.

`status` reports which case applies. A move to chromadb 2 is outside this scheme: `export` with the old version, then `import` with the new.

One gap remains. The copy-read probe proves that a newer chromadb can read an older store, not the reverse. A newer release with the same migrations could in principle write data files an older one cannot read. The older contributor would then get a read error, not data loss, and git history still holds the earlier store. Keeping everyone within the same requirements range is what closes it.

**Commands** (`python -m memstore ...`, from the repository root):

| Command | Purpose |
| :--- | :--- |
| `index [--budget N]` | the session-start read: both Indexes, plus full entries not yet digested; a one-line notice when the Indexes exceed about N tokens (default 8000) |
| `get mem:diary/<file>#<slug>` | the exact original entry |
| `search "query" [--where k=v]` | semantic search over entry chunks; a labelled entry's hits say `NOT IN FORCE` |
| `ingest diary [--dry-run]` | archive every entry still present in full; idempotent; never deletes an entry |
| `compact <file> --digests FILE.json [--dry-run]` | replace archived entries with digests (`{slug: text}`) and rebuild the Index |
| `set-label mem:diary/<file>#<slug> (--superseded-by SLUG \| --retired "Mon YYYY: reason" \| --clear)` | label a digest (or a full entry's heading) as no longer in force and rebuild the Index; markdown only, never the store |
| `restore mem:diary/<file>#<slug>` | put an archived entry that lost its digest (renamed or deleted after `ingest`) back below the region, to be compacted again with a label |
| `check-pointers` | every digest resolves to its exact archived entry, every archived entry still has a digest or full entry, labels are well formed, the Index is current, every `mem:` pointer in the repo's markdown resolves |
| `upgrade-store [--dry-run]` | let the installed chromadb migrate the store's format; one way, committed with a raised chromadb floor ([chromadb versions](#chromadb-versions)) |
| `status`, `export --out FILE`, `import FILE`, `reindex` | counts and format compatibility; a text safety copy; refill a fresh store; re-embed after an embedding change |

**What changes in the skills when it is on:** `startup` runs inline and reads the Indexes, not the files; `session-historian` writes new entries below the digest region, then ingests, digests (in the house style, written by the model that has the session context), compacts and checks pointers; labels what each new entry supersedes with `set-label`; `committer` stages `diary/memstore/` with the rest of `diary/`; `grill-me` reads the Index and drills down; `tidy` labels digested entries with `set-label` and never folds or deletes a digest (its archived entry would be left with no digest, which `check-pointers` reports as an error).

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

Spawns a subagent to read all three diary files and synthesize a briefing. Runs from cold — the main conversation has no context yet, so spawning is appropriate here. Entries labelled `superseded by` or `retired` are read as history, never as current rules.

With enhanced memory on, it runs **inline** instead: `index` prints both Indexes, it reads `session_context.md` and any not-yet-digested `[FULL]` entries, and it drills into a digest or `get <pointer>` only when an Index line bears on the task. When the Indexes are over their size budget it says so in one line and suggests `/tidy`. If the memstore command fails it says so and stops.

**File**: `skills/startup/SKILL.md`

**When to invoke**: at the start of any non-trivial session, or when the user asks "what were we working on?"

---

### `session-historian` — writes diary at session end

Runs **inline in the main conversation** (no agent spawn). The main conversation already has full session context; spawning an agent to re-derive it is the expensive path.

Supports two modes (decision logic handled by `/committer`):
- **FULL** — updates all three files as appropriate and sets the `Last full review:` line; used for sessions with code changes or significant work
- **LIGHTWEIGHT** — updates only `session_context.md` (plus a lesson if one was learned); used for documentation-only commits. It may still write a decision promoted from a session note that is dropping off: if it is worth writing, it is still relevant.

Direct `/session-historian` invocations always run FULL.

What it does on every run:
- **Rewrites `session_context.md`** with an **Arc** line when a milestone is completed, and a session log of only the current session and the one before it, counted by date. Before an older note drops off, anything durable moves into a decision, a lesson or Open Items. When the file is untracked, the historian lists the dropped notes first, because they exist nowhere else.
- **Appends a decision or lesson** only when something genuinely new was decided or learned, in the `## slug (Month YYYY)` format with its **Why**.
- **Asks, for each new entry, whether it replaces or retires an existing one.** If so, it writes `This reverses (→ old-slug)` and [labels](#keeping-the-diary-current-labels) the old entry. Each label applied is shown in its report.
- **Never writes** per-file change lists, "Status: COMPLETE" announcements, verification steps, or anything git already holds (commit hashes, changed file paths).

With enhanced memory on, the skill then archives each new entry (`ingest diary`), writes its digest in the house style (no status word; a label, when there is one, goes in the lead's date parenthetical), runs `compact` (dry run first), labels superseded digests with `set-label`, runs `check-pointers` (0 errors), and proofreads each digest against its entry before staging. The full steps and the digest style are in `skills/session-historian/SKILL.md`.

**File**: `skills/session-historian/SKILL.md`

**When to invoke**: directly at the end of any significant session; or via `/committer` which decides the mode for you before a commit.

---

### `committer` — updates and stages the diary before a commit

Checks what's staged, decides whether to run a FULL or LIGHTWEIGHT session-historian pass, updates the diary accordingly, and stages `diary/`. Runs inline, no agent spawn.

**FULL** mode runs if any staged file has a code file extension (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.rb`, `.java`, `.rs`, `.cs`, `.cpp`, `.c`, `.swift`, `.kt`, `.sh`, `.bash`), if any staged file has added or deleted status (`A` or `D`), if 5 or more commits have landed since the last full review, or if the last full review was more than 3 days ago (or never).

**LIGHTWEIGHT** mode runs for documentation-only commits (only `diary/`, `CLAUDE.md`, `.claude/`, or `.md` files staged) — or skips the diary update entirely if every staged path is already documentation-only.

`committer` does not draft a commit message or run `git commit` itself — that's redundant with what any agent harness already does unprompted. It stops once the diary is updated and staged.

**The review cadence is shared through git, not stored per machine.** Every FULL run sets a `Last full review: <Month D, YYYY>` line in `architectural_decisions.md`. `committer` counts the commits since the last commit that changed that line (`git log -G'^Last full review:'`), so every contributor gets the same answer and curation edits to the file don't reset it.
- A missing line, or a shallow clone that cannot count, means "never", which forces FULL.
- In private mode, where the diary is untracked, it counts commits since the line's date instead. That errs toward FULL sooner.
- Before 2.0 this state lived in `~/.claude/projects/<project-path>/historian_state.json`, written by a `PostToolUse` hook. That file is no longer read.

**File**: `skills/committer/SKILL.md`

**When to invoke**: before committing, when staged changes include more than documentation. Tests should pass before invoking.

---

### Hooks — enforcing the diary update at the harness level

A CLAUDE.md instruction to "run `/committer` before committing" is advisory: committing is a default behavior agent harnesses already know how to do unprompted, so the instruction is easy to silently skip. Memtoad instead ships a hook (`hooks/hooks.json`) that registers automatically for every project with the plugin installed — no per-project setup, and they travel with `claude plugin update` exactly like skills do.

**`check-diary-staged.sh`** (`PreToolUse`, matched on `Bash`): inspects any `git commit` invocation. If the project has no `diary/` directory, or every staged file is documentation-only, or `diary/` already has staged changes, it allows the commit silently. Otherwise it denies the commit with a reason pointing back to `/memtoad:committer`.

Before 2.0 a second hook, `record-commit.sh` (`PostToolUse`), kept the review cadence in a per-machine state file. It was removed: the cadence is now derived from git (see `committer` above), so contributors share it.

The hook no-ops immediately for any project without a `diary/` directory, so installing the plugin never gates commits in projects that haven't adopted Memtoad's diary convention.

---

### `grill-me` — interrogates a plan using project context

Interviews the user about a plan or design until reaching shared understanding. Reads all three diary files first, then outputs 1–2 sentences naming any constraints, decisions, or patterns directly relevant to the stated task — letting the user correct misreadings before the interrogation begins. If nothing in the diary bears on the task, it skips this acknowledgment and proceeds silently. Labelled entries are not current constraints; it raises one only when the plan would repeat what it records as not having worked.

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

Spawns a subagent to update `diary/session_context.md` with the current work-in-progress state, under the same session-log rule as `session-historian` (the current session and the one before it, by date). Use when Claude Code's context is about to be compressed, when switching tasks mid-session, or to checkpoint significant progress before it's lost.

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

Tracks first/last-seen dates and a description hash per skill in a state file at `~/.claude/projects/<project-path>/skill_inventory_state.json`. It stays per machine on purpose: it describes the skills installed on that machine, not shared project state. This is bookkeeping, not diary content, so it lives outside `diary/` entirely.

**File**: `skills/skill-inventory/SKILL.md`

**When to invoke**: on demand, when auditing skills/plugins or checking what's new since the last audit. Never runs automatically at session start.

---

### `tidy` — curates the diary so what reads as in force is in force

Runs **inline in the main conversation** (no agent spawn): each change is an editorial call the user should watch being made, not receive as a finished diff.

`architectural_decisions.md` and `lessons_learned.md` are append-only, and archiving by date or size was tried once in a predecessor system and rejected, because archived content stopped being read (→ three-files-no-archiving, → archive-files-are-never-read). `tidy` keeps to that: it never removes an entry from what is read. What it fixes is **correctness**. `session-historian` labels what a new entry supersedes when it writes it; `tidy` finds what that missed, including a whole diary written before 2.0.

It looks for four kinds of candidate, and only these:
1. **An explicit reversal pair** (`This reverses (→ slug)`). In a plain diary it folds the pair into one entry: the current decision stays the operative text, the older one is compressed into one clause of the WHY, and the older slug survives as a `(…, supersedes slug)` header annotation. With enhanced memory it labels the older entry `superseded by` instead, because folding would leave its archived entry without a digest.
2. **Supersession that was never written down.** It must quote the sentence in the later entry that does the replacing.
3. **Retirement.** What the entry governs no longer exists, with the evidence named: what was grepped or checked, and what was found. A renamed thing is not a gone thing.
4. **Owner-stated.** "Retire X because Y."

It can also propose a **correction**: the smallest edit to an entry still in force whose wording names a replaced mechanism.

**Lessons get stricter rules.** A lesson is retired only when the hazard itself can no longer occur. When a later entry carries its rule forward, `superseded by` is preferred, so the lesson keeps a pointer to where its rule lives now. A lesson another entry references is never retired.

`tidy` never acts on age alone or on topic similarity, never deletes reasoning, never touches `session_context.md`, and never runs on a schedule or at the end of another skill. It shows every proposal with its evidence, applies only what the user confirms, and leaves the change unstaged for normal review.

**File**: `skills/tidy/SKILL.md`

**When to invoke**: on demand. Good moments:
- once after upgrading an existing diary to 2.0;
- after a refactor that removed or replaced something the diary describes;
- when `/startup` reports that the Index is over budget.

---

### `list` — shows available commands

Lists all Memtoad slash commands with one-line descriptions, plus a reminder that enhanced memory is enabled through `/bootstrap`. Useful when you can't remember what's available.

**File**: `skills/list/SKILL.md`

**When to invoke**: any time you want to see what Memtoad commands are available.

---

## Command wrappers

Each skill has a corresponding command wrapper in `commands/` that enables it as a slash command. The wrappers are intentionally thin — they exist to expose the skill via the `/command-name` interface, not to duplicate the skill logic.

| Command | What it does |
|---|---|
| `/bootstrap` | Set up + populate diary for this project; opt in to enhanced memory |
| `/startup` | Load full project context at session start |
| `/committer` | Update + stage the diary before a commit |
| `/session-historian` | Write diary entries for the current session |
| `/grill-me` | Stress-test a plan with diary-informed questions |
| `/context-capture` | Checkpoint WIP state to the diary |
| `/skill-inventory` | Audit all visible skills — local, plugin, built-in |
| `/tidy` | Curate the diary: label superseded/retired entries, fold reversals |
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

## Arc

[One line per milestone (a version or phase): what changed and why it mattered. This, not the
session log, is the record of where the project has been.]

---

## Current State

[One paragraph: what the system is, production status, key facts a new engineer needs to orient.
Not a feature list — a snapshot of where things stand right now.]

---

## Most Recent Sessions

[Entries added here by /committer or /session-historian. Most recent first. Only the current
session and the one before it, plus any still in flight: context on active work, not a history.
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

Most recent decisions at top. Nothing is deleted: an entry that stops applying gets a label in its
heading, `(Month YYYY; superseded by <slug>)` or `(Month YYYY; retired <Mon YYYY>: <reason>)`.

Last full review: [Date]

---

<!-- memtoad:uninitialized -->
```

### `diary/lessons_learned.md`

```markdown
# Lessons Learned

Anti-patterns, failure modes, and hard-won rules. Most recent at top. Add an entry only when
a lesson is non-obvious — if it's standard practice or documented in the framework, skip it.

Cross-references use (→ slug-name) notation. A lesson that no longer applies is labelled in its
heading like a decision, never deleted.

---

<!-- memtoad:uninitialized -->
```

---

## Design principles

These constrain how the system evolves. If you fork or extend it, respect them.

**Supplement, don't duplicate.** The diary captures what git history and code cannot: the narrative arc and the non-obvious WHY. Implementation details belong in the code. Timelines belong in git log. The diary is not a substitute for either.

**Three files, no more.** The archive explosion that Memtoad was designed to replace happened because files multiplied without bound. Resist the urge to add a fourth file for bugs, a fifth for refactoring history. Bugs worth remembering become lessons. Refactors worth remembering become decisions. If it doesn't fit the three files, it probably doesn't belong in the diary. Enhanced memory respects this: the store is not a fourth file you write to. It is a verbatim archive of entries from the same two files, maintained by the skills.

**Inline, not spawned — except startup, context-capture, and skill-inventory.** Session-historian and committer run in the main conversation, which already has session context. Spawning an agent to re-derive context you already have is the expensive path. Startup spawns because it genuinely starts cold. Context-capture spawns to snapshot state independently of the current conversation thread. Skill-inventory spawns for the same reason as startup — it's a cold sweep over plugin caches and marketplace clones that has nothing to do with the conversation so far, and doing that reading inline would waste the main context window. Grill-me runs inline because it needs AskUserQuestion, which agents cannot use.

**No archiving.** The old system archived files when they grew large. Modern context windows make this obsolete, and archived files are never read. Let the files grow. Enhanced memory is not archiving in that sense: every entry keeps a digest in the file that is read every session, and the digest points at the exact full text.

**Label, don't delete.** An entry that stops being true keeps its text and gets a `superseded by` or `retired` label in its heading. What was tried and why it stopped working is half of what the diary is for, and a deleted lesson is the one most likely to be repeated. Labels are applied when a new entry replaces an old one, or by `/tidy` with evidence and confirmation. They are never applied on a schedule or on age alone.

**A session log, not a journal.** `session_context.md` holds the current session and the one before it, plus work still in flight. Where the project has been lives in its Arc and in the two other files; the rest is in git. A diary that grows a long history of what was done has become the verbose journal Memtoad exists to avoid.

**Shared state lives in git.** The review cadence is one dated line in `architectural_decisions.md`, counted with `git log`, not a per-machine file. Every contributor gets the same answer, with nothing to merge.

**Conditional writes.** Session-historian always updates `session_context.md`. It only touches the other two files when something genuinely new was decided or learned. Most sessions produce only one update.

**Commit with the code, not after.** Use `/committer` to update and stage `diary/` before you commit — don't leave the diary for a follow-up commit. A plugin hook (`hooks/check-diary-staged.sh`) enforces this at the harness level rather than relying on a CLAUDE.md instruction the model might skip. Do not reference the commit hash in diary entries — it isn't known yet, and git log is the authoritative record.

**Slugs, not numbers.** Numbered lessons rot when you reorder or delete entries. Slugs are self-describing and survive restructuring. `(→ null-key-defers-failure)` tells you what it is; `(→ Lesson 228)` tells you nothing.

**Plugin, not installed.** Skills are firmware — they should improve without requiring per-project updates. The plugin architecture delivers skills globally; only the `diary/` files are per-project. When Memtoad improves, update the plugin once and all projects benefit.
