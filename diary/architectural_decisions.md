# Architectural Decisions

Design principles and the reasoning behind non-obvious choices. Add an entry when a future
engineer would reasonably ask "why did they do it this way?" — and the answer isn't obvious
from the code.

Most recent decisions at top. No archiving.

---

## committer-owns-commit-discipline (June 2026)

The `committer` skill owns the session-historian invocation and commit workflow; `session-historian` no longer instructs users to run it before committing.

**Why**: When `/session-historian` said "run me before every commit," users had to remember two commands in the right order. The `committer` skill makes the diary update and commit a single atomic operation — it calls session-historian internally, stages diary changes, confirms the file list, and commits. Session-historian invoked directly (outside a commit context) always runs FULL and is appropriate for mid-session documentation. The split removes the manual coordination burden while keeping both skills composable.

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

In private mode, the install scripts add `CLAUDE.md` to `.gitignore` alongside `diary/`.

**Why**: In private mode each contributor manages their own diary locally — but the CLAUDE.md Project Memory section now contains Memtoad-specific workflow instructions (`/session-historian`, `/grill-me`, the 3-step commit order). Pushing that content to teammates who haven't installed Memtoad produces confusing slash commands that don't exist for them and a pre-commit instruction they can't follow. Gitignoring CLAUDE.md in private mode keeps Memtoad's footprint fully local to the contributor who chose private tracking. Shared and hybrid modes commit CLAUDE.md normally because the team is presumed to share the tooling. (→ pre-commit-workflow-in-claude-md)

---

## pre-commit-workflow-in-claude-md (June 2026)

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
