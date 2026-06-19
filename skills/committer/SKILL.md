---
name: committer
description: Document the current session via session-historian, review staged files, then commit atomically. Run after tests pass. Handles LIGHTWEIGHT vs FULL diary update automatically based on what is staged.
---

Run the following steps **inline in the main conversation**. Do not spawn an agent until Step 5.

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

**Skip session-historian entirely** (go straight to Step 4) if every staged path is documentation-only:
- `diary/`
- `CLAUDE.md`
- `.claude/` (skills, commands, agents)
- Any `.md` file at the repo root

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

Do not reference the commit hash in diary entries — it isn't known yet.

After writing, stage any diary changes:
```bash
git add diary/
```

## Step 4 — Review staged files and get confirmation

Run:
```bash
git diff --cached --name-only
git status --short
```

Show the user the final staged file list as plain text. Then use **AskUserQuestion** with these options:

> "Ready to commit. What would you like to do?"

- **Commit staged files** — proceed with exactly what is staged
- **Stage all modified files too** — run `git add -u`, then proceed
- **Cancel** — stop without committing

If the user types specific file paths in the "Other" field, run `git add <those paths>` and proceed.

## Step 5 — Commit

Use the Agent tool to spawn a subagent with this prompt:

"Commit the currently staged changes. Verify staged files exist with `git diff --cached --name-only`. Analyze what changed and why by reading the diff. Draft a concise commit message focused on the 'why' not the 'what'. Create the commit. Report the commit hash in your final output."

Capture the commit hash from the subagent's output.

## Step 6 — Update historian state file

Compute the state file path:
```bash
STATE_FILE=~/.claude/projects/$(pwd | tr '/' '-' | sed 's/^-//')/historian_state.json
```

Read the current state (or use defaults if file doesn't exist), then write updated state:

**After documentation-only commit (session-historian skipped)**: increment `commits_since_last_full` by 1, keep other fields unchanged.

**After LIGHTWEIGHT**: increment `commits_since_last_full` by 1, keep `last_full_run_date` and `last_full_run_commit` unchanged.

**After FULL**: write:
```json
{"last_full_run_commit": "<HASH>", "last_full_run_date": "<YYYY-MM-DD>", "commits_since_last_full": 0}
```

Ensure the parent directory exists before writing:
```bash
mkdir -p "$(dirname "$STATE_FILE")"
```
