# Architectural Decisions

Design principles and the reasoning behind non-obvious choices. Add an entry when a future
engineer would reasonably ask "why did they do it this way?" — and the answer isn't obvious
from the code.

Most recent decisions at top. Nothing is deleted: an entry that stops applying gets a label in its
heading, `(Month YYYY; superseded by <slug>)` or `(Month YYYY; retired <Mon YYYY>: <reason>)`.

Last full review: November 18, 2026

---

## store-compatibility-from-migrations (November 18, 2026)

memstore decides whether the installed chromadb may open a store from chromadb's own `migrations` table in `chroma.sqlite3`, not from the version string.
- **How:** it reads the table with `sqlite3` before chromadb touches the store, and compares it with the migrations the installed chromadb writes into a throwaway empty store. That set is cached per version in `~/.cache/memstore`.
- **Outcomes:**
  - same format: opens, after a read probe of a copy when the version differs from the one that created the store;
  - the installed chromadb would add migrations: refused until a deliberate `upgrade-store`, committed with a raised chromadb floor;
  - the store has migrations the installed chromadb lacks: refused.
- **Requirements:** projects bound chromadb (`>=<floor>,<2`) instead of pinning it exactly.

**Why**: the exact-version guard broke on every chromadb release, although most change nothing on disk. Worse, it ran after `PersistentClient` had already opened the store, and opening is what migrates it (→ check-before-the-side-effect). Experiments on scratch copies settled the rest:
- chromadb 1.5.9 opened a store carrying an unknown future migration without complaint, so memstore must catch a newer store itself.
- chromadb 1.x applies migrations that the Python package ships no files for, so the known set has to come from chromadb's actual behaviour.
- `collection.modify` refuses `hnsw:space` and drops it when it is left out, so the recorded "created with" version is never rewritten. The probe is fast enough to run on every open instead.

One gap is accepted and documented: a newer release with the same migrations could write data an older one cannot read. The worst case is a read error, and the earlier store stays in git.

---

## labels-not-deletion (November 18, 2026)

An entry that stops being true keeps its text and gets a label inside its heading's date parenthetical: `superseded by <slug>` (the target may be in either file) or `retired <Mon YYYY>: <reason>` (one clause, at most 120 characters, no parentheses). An unlabelled entry is in force; there is no `active` status. Labels are applied at two moments only: by `session-historian` when it writes an entry, after asking whether the new entry replaces, retires or amends an existing one (an amendment corrects the old entry and leaves it in force); and by `/tidy` on demand. There are no profiles, schedules, counters or age rules, and no purge. With enhanced memory the label lives in the markdown only, the Index lists labelled entries last under "No longer in force", and `memstore set-label` applies one.

**Why**: the owner had cleaned stale material out of diaries by hand for years, and the cost that drove it was correctness, not size: an entry that still reads as a current rule after a reversal or a removal misleads every later session. Deleting it would lose the record of what was tried and why it stopped working, which is half of what the diary is for. Deleting from the store would not even shrink the repository, since git keeps the old blobs. A first design (lifecycle states, four evidence tiers, five triggers, Archive/Balanced/Lean profiles) was red-teamed by a second model and cut down. A positive `active` status goes stale on its own. Age plus disuse needs per-machine state and is how the predecessor lost its early lessons (→ archive-files-are-never-read). A prompt at the end of the historian run arrives just before a commit, where it gets rubber-stamped. With the session-log rule fixed and capture depth free under the store, there was nothing left for a profile to set. The capture-time question is the strongest signal because the session that made a change knows what it replaced. Labels work in plain mode too, since a label deletes nothing.

---

## tidy-curates-with-evidence (November 18, 2026)

`/tidy` curates both `architectural_decisions.md` and `lessons_learned.md`. It looks for four kinds of candidate:
- an explicit `This reverses (→ slug)` pair;
- supersession that was never written down, which it must quote from the later entry;
- retirement, with the check that proves the subject is gone named;
- an owner-stated retirement.

It can also propose a minimal correction to an entry still in force. Lessons get stricter rules: retire one only when the hazard itself can no longer occur, prefer `superseded by` when a later entry carries its rule forward, and never retire one that another entry references. Every proposal comes with evidence and is applied only on confirmation. It never acts on age or topic similarity, and never runs on a schedule or at the end of another skill. In a plain diary it still folds reversal pairs. With enhanced memory it labels the older entry instead, and never folds or deletes a digest. This reverses (→ tidy-consolidates-not-archives).

**Why**: the narrow 1.3 scope (explicit reversal pairs, decisions only) missed most of what goes stale. In this repo, two decisions still prescribed install scripts that no longer existed, and a later decision had replaced an approach without naming it. Neither shows up as a `This reverses` pair. Requiring evidence, and a quote for unrecorded supersession, keeps it from guessing on topic similarity, which was the original reason for the narrow scope. Folding is unsafe with the store: the older entry is already archived, and removing its digest leaves an archived entry that only a lucky search reaches, which `check-pointers` now reports as an error.

---

## session-log-is-active-work (November 18, 2026)

"Most Recent Sessions" in `session_context.md` keeps only the current session and the one before it, counted by date (a second run on the same day updates that note), plus any older note whose work is still in flight. A new **Arc** section, one line per milestone, records where the project has been. Before a note drops off, anything durable becomes a decision or lesson (allowed even in a LIGHTWEIGHT run) or an Open Item. When the file is untracked, the historian lists the dropped notes before rewriting.

**Why**: the owner's goal is a diary that shows where the project has been, the guidelines it followed and what did and did not work, without becoming a verbose journal of work done. A growing session log is exactly that journal, and its durable content belongs in the other two files. The red team found that in hybrid and private mode the file is untracked, so "git has the rest" is false and a silent trim is permanent; hence the listing. It also found that counting historian runs as sessions would make n-1 an hour old, since `/committer` runs the historian per commit. This repo's log already had a duplicated same-day heading. Without the Arc, trimming the log would have left no record of the project's path.

---

## review-cadence-from-git-marker (November 18, 2026)

The FULL/LIGHTWEIGHT cadence is no longer stored per machine. Every FULL historian run sets a `Last full review: <Month D, YYYY>` line near the top of this file. `/committer` counts commits since the last commit that changed that line (`git log -1 -G'^Last full review:' -- diary/architectural_decisions.md`, then `git rev-list --count`).
- A missing line or a shallow clone means "never", which forces FULL.
- In private mode, where the diary is untracked, it counts commits since the line's date instead.
- `hooks/record-commit.sh` and `historian_state.json` were removed. This amends (→ committer-diary-prep-only).

**Why**: the owner wanted the capture state shared and coordinated across contributors. Committing `historian_state.json` as it was would have caused three problems:
- The PostToolUse hook rewrites it after every commit, so the working tree would always be dirty.
- Under `diary/`, staging it alone would satisfy the commit gate with no real diary update.
- Its counter would conflict on every merge.

Deriving from "the last commit touching `diary/`" was approved first, then found broken before it was built: the gate forces `diary/` into nearly every commit, so the count would stay near zero and the 5-commit and 3-day triggers would never fire (→ gated-paths-make-bad-change-signals). A dedicated line changes only on FULL runs, so curation edits to the same file don't reset it. The private-mode date fallback errs toward FULL. `skill_inventory_state.json` stays per machine on purpose: it describes that machine's installed skills.

---

## optional-memstore-archive (November 17, 2026)

Memtoad ships an optional Python package, `memstore/`, ported from the project it was built in, for diaries too big to read whole. It turns `architectural_decisions.md` and `lessons_learned.md` into a newest-first Index plus one-paragraph digests, with the exact full text of every entry in a chroma database tracked in git at `diary/memstore/`. It is opt-in through `/bootstrap` step 0d. A project is "on" only when its `CLAUDE.md` carries a `<!-- memtoad:store -->` block naming the project's memstore command. Every skill checks that block: without it nothing changes; with it and the package missing, the skill says so and stops. The package is installed into the project's own Python environment from this repository's `memstore/` subdirectory with `pip install git+...#subdirectory=memstore`, not from the plugin cache. The parser reads memtoad's own format only: in both files an entry is a `##` heading and any deeper heading is a sub-section of it; the originating project's `###`-lesson peers, month dividers and `Lesson N:` titles were deliberately not carried over.

**Why**: in the originating project the two big files reached 560 KB and could no longer be read each session, which broke the premise of (→ three-files-no-archiving) without any rule being violated. The store keeps that decision's intent, nothing read-dead, because each entry's digest stays in the file every session reads and points at the exact text (→ archive-files-are-never-read is about files nobody opens; a digest is opened every time). An explicit sentinel, not the digest-region marker, decides "on": a freshly bootstrapped project has no digests yet but must already follow the store flow. The package cannot be installed from the plugin cache, because that path changes with every plugin version. Naming the command in `CLAUDE.md` means no skill assumes a Python environment.

---

## tidy-consolidates-not-archives (August 2026; superseded by tidy-curates-with-evidence)

`tidy` is a ninth skill that merges an architectural-decision entry with the earlier entry it explicitly reverses (`This reverses (→ slug)`) into one entry, in place. It matches only that authored phrase — never topic similarity or entry age — skips any pair where the older slug is still referenced elsewhere in the file, drafts the merge, and requires explicit user confirmation per pair before writing anything. It runs inline, not spawned, and only ever touches `architectural_decisions.md`.

**Why**: as the diary matures, `architectural_decisions.md` and `lessons_learned.md` are permanently append-only (→ three-files-no-archiving) — archiving by date or size was already tried once and rejected because archived content stopped being read (→ archive-files-are-never-read). That rules out pruning or rotating either file to control growth. But a decision-then-reversal pair is a case where two full entries describe one current fact, and collapsing them loses nothing — the reasoning arc survives compressed into a single WHY, and the old slug survives as a header annotation so nothing that referenced it goes stale. Scoping `tidy` to the explicit `reverses` phrase (rather than having it judge topical overlap) keeps it from ever guessing wrong about which entries are safe to fold; scoping it to `architectural_decisions.md` only reflects that `lessons_learned.md` has no equivalent supersession convention today. Inline execution (not spawned, unlike `skill-inventory`) is deliberate: the file it reads is small and bounded by design, and the merge is an editorial call the user should watch happen in the transcript, not receive as a finished diff from a subagent.

---

## committer-diary-prep-only (August 2026, supersedes committer-owns-commit-discipline)

`committer` no longer drafts commit messages or runs `git commit`. It does Steps 1–3 only — assess FULL/LIGHTWEIGHT mode, update the diary, stage `diary/` — then stops. Enforcement that the diary gets staged before a commit moves to a plugin-shipped hook (`hooks/check-diary-staged.sh`, `PreToolUse` on `Bash`) that denies `git commit` until `diary/` has staged changes (or the commit is documentation-only). The FULL/LIGHTWEIGHT cadence that `committer`'s removed commit step used to record went first to a companion `PostToolUse` hook writing a per-machine `historian_state.json`. Since 2.0 it is a `Last full review:` line in this file, counted with git (→ review-cadence-from-git-marker).

**Why**: drafting and executing `git commit` was scope creep — every agent harness already knows how to commit unprompted, so that half of `committer` was redundant, dead weight relative to Memtoad's stated mission of capturing project *why*, not orchestrating git. Worse, the only thing that had been guaranteeing the diary got updated before a commit was an advisory line in each project's `CLAUDE.md` ("run `/committer` before committing") — easy to silently skip precisely because committing is a default behavior models reach for without being told. A plugin hook enforces the same guarantee at the harness level instead of at the model-compliance level, and (unlike CLAUDE.md instructions) it ships and updates with the plugin itself via `claude plugin update` — no per-project injection required. Originally (June 2026) `committer` owned the full session-historian-then-commit workflow as a single atomic operation, because a two-command manual order (`/session-historian` then `git commit`) was easy for users to get wrong — but that problem turned out to be better solved by the hook than by folding commit execution into the skill.

---

## skill-inventory-spawns-like-startup (August 2026)

`skill-inventory` spawns a subagent rather than running inline, joining `startup` and `context-capture` as exceptions to the "inline, not spawned" default.

**Why**: The inline-by-default rule exists because `session-historian` and `committer` benefit from context already present in the main conversation — spawning would mean expensively re-deriving it. `skill-inventory` has the opposite shape: it's a cold sweep over `~/.claude/plugins/installed_plugins.json`, cached plugin `SKILL.md` files, and marketplace git clones that has no relationship to the current conversation. Running it inline would spend the main context window on file contents nobody in the conversation needs to see. This mirrors exactly why `startup` spawns — the task starts cold regardless of what came before it.

---

## bootstrap-owns-project-init (June 2026)

The `bootstrap` skill handles complete project initialization — creating `diary/`, injecting the CLAUDE.md section, and configuring `.gitignore` — in addition to populating diary content.

**Why**: Before this change, project setup required running `install.sh` (a bash script) before opening Claude Code. With the plugin architecture, there is no install script per project. Bootstrap is already the first command a user runs; extending it with an idempotent Phase 0 setup removes the external dependency and makes the experience purely in-Claude. The setup steps (file creation, CLAUDE.md injection, .gitignore config) are safe to re-run and detect existing state before acting.

---

## plugin-not-installed (June 2026)

Memtoad is distributed as a Claude Code plugin (`skills/` + `commands/` + `.claude-plugin/plugin.json`) rather than an install script that copies files into each project.

**Why**: The copy-in-project model creates a frozen-firmware problem — each installed project has a static snapshot of the skills at install time. When Memtoad improves, existing projects don't benefit without a manual re-install. The plugin system delivers skills globally from one source; updating the plugin once propagates to every project immediately. The only per-project artifacts are the `diary/` files, which are data, not firmware. (→ bootstrap-owns-project-init)

---

## private-mode-gitignores-claude-md (June 2026)

In private mode, `/bootstrap` (step 0c) adds `CLAUDE.md` to `.gitignore` alongside `diary/`.

**Why**: In private mode each contributor manages their own diary locally — but the CLAUDE.md Project Memory section now contains Memtoad-specific workflow instructions (Memtoad slash commands and the commit-gate note). Pushing that content to teammates who haven't installed Memtoad produces confusing slash commands that don't exist for them and a pre-commit instruction they can't follow. Gitignoring CLAUDE.md in private mode keeps Memtoad's footprint fully local to the contributor who chose private tracking. Shared and hybrid modes commit CLAUDE.md normally because the team is presumed to share the tooling. (→ pre-commit-workflow-in-claude-md)

---

## pre-commit-workflow-in-claude-md (June 2026; superseded by committer-diary-prep-only)

The install scripts inject a 3-step pre-commit workflow block into the target project's CLAUDE.md as part of the Project Memory section.

**Why**: The workflow (tests → `/session-historian` → `git commit`) is only followed if it's visible at the moment a developer is about to commit. Documenting it in the README or install guide is insufficient — those are read once during setup. CLAUDE.md is loaded into every Claude Code session, making it the right place for any rule that must be enforced before every commit. Without this block, the first session after install ends in a commit that skips `/session-historian` and starts the next session blind. (→ private-mode-gitignores-claude-md)

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
