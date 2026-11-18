---
name: committer
description: Update the project diary before a commit — review staged files, determine LIGHTWEIGHT vs FULL session-historian mode based on what's staged, write the diary entry, and stage the diary changes. Does not create the commit; a plugin hook enforces that diary files are staged before `git commit` runs.
---

Run the following steps **inline in the main conversation**. Never spawn an agent.

## Step 1 — Check working state

Run both commands:
```bash
git diff --cached --name-only
git status --short
```

If there are no staged files AND no modified/untracked files: stop. Tell the user there is nothing to commit.

Display the current state to the user: which files are staged, which are modified-but-not-staged.

## Step 2 — Assess session-historian mode

From Step 1's output, determine the mode.

**Skip session-historian entirely** if every staged path is documentation-only:
- `diary/`
- `CLAUDE.md`
- `.claude/` (skills, commands, agents)
- Any `.md` file at the repo root

In that case, tell the user the staged changes are documentation-only and no diary update is needed, then stop.

Otherwise determine the historian state file path dynamically:
```bash
STATE_FILE=~/.claude/projects/$(pwd | tr '/' '-' | sed 's/^-//')/historian_state.json
cat "$STATE_FILE" 2>/dev/null || echo '{"last_full_run_date":"1970-01-01","commits_since_last_full":0}'
```

Choose **FULL** mode if ANY of the following are true:
- Any staged file has a code extension: `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.rb`, `.java`, `.rs`, `.cs`, `.cpp`, `.c`, `.swift`, `.kt`, `.sh`, `.bash`
- Any staged file has `A` (added) or `D` (deleted) status
- `commits_since_last_full` ≥ 5
- `last_full_run_date` is more than 3 days before today

Otherwise: **LIGHTWEIGHT** mode.

## Step 3 — Run session-historian and stage diary changes

Run session-historian **inline** using the rules in the `session-historian` skill:

**LIGHTWEIGHT**: Update only `diary/session_context.md`. Append to `diary/lessons_learned.md` only if something non-obvious was learned this session. Do not touch `diary/architectural_decisions.md`.

**FULL**: Update `diary/session_context.md`. Append to `diary/architectural_decisions.md` only if a new architectural decision was made. Append to `diary/lessons_learned.md` only if a new lesson was learned.

Do not reference the commit hash in diary entries — it isn't known yet, and this skill does not create the commit.

With enhanced memory on (`CLAUDE.md` contains `<!-- memtoad:store -->`), session-historian also archives each new entry in the store and replaces it with its digest; `check-pointers` must report 0 errors before staging.

After writing, stage the diary changes:
```bash
git add diary/
```

With enhanced memory this also stages `diary/memstore/`, the tracked store. That is intended: the store is the only full copy of compacted entries. (Any read of the store changes one counter row in its sqlite file, so it can show as modified after a mere `search`; staging it then is harmless.)

Report to the user that the diary is updated and staged. Do not commit — a plugin `PreToolUse` hook checks that `diary/` is staged before any `git commit` runs, and denies the commit with a pointer back to `/memtoad:committer` if it isn't. Once diary changes are staged, the user's normal commit flow (or the harness's own commit drafting) can proceed.
