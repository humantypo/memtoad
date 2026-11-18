# Lessons Learned

Anti-patterns, failure modes, and hard-won rules. Most recent at top. Add an entry only when
a lesson is non-obvious — if it's standard practice or documented in the framework, skip it.

Cross-references use (→ slug-name) notation. A lesson that no longer applies is labelled in its
heading like a decision, never deleted.

---

## gated-paths-make-bad-change-signals (November 18, 2026)

**Rule**: Never derive "when did X last happen" from changes to a path that another mechanism forces into every commit. Check which hooks, gates or tools touch the path before using its history as a signal; use a marker that changes only when X happens.

**Why**: the plan for a shared historian cadence was "the last commit touching `diary/`", and it was approved before anyone noticed the conflict. The commit gate (`check-diary-staged.sh`) denies any non-doc commit unless `diary/` is staged, and with enhanced memory a mere `search` dirties the store's sqlite file. So nearly every commit touches `diary/`, the count since stays near zero, and the time-based FULL triggers silently never fire. Nothing would have errored; capture would just have quietly thinned. The fix was a dedicated `Last full review:` line (→ review-cadence-from-git-marker).

---

## untracked-diary-files-are-the-only-copy (November 18, 2026)

**Rule**: Before trimming or rewriting a diary file, check whether git tracks it (`git ls-files --error-unmatch`). In hybrid mode `session_context.md` is untracked, and in private mode the whole `diary/` is, so whatever a rewrite drops is gone for good. Show the user what will be dropped.

**Why**: the first curation proposal said dropped session notes were safe because "everything else lives in git". The red team pointed at this repo's own `.gitignore`, which ignores `diary/session_context.md`. The recommended team mode is exactly the one where the claim is false. An automatic, unconfirmed trim would have lost notes with nobody seeing it (→ session-log-is-active-work).

---

## ported-tests-can-run-against-the-original (November 2026)

**Rule**: Verify a package ported from another repo in a fresh virtualenv (or with `PYTHONPATH=src`), never in the originating project's environment. The working env had the originating project's own `memstore` installed editable, so `python -m pytest memstore/tests` here imported the original's source tree and went 39/40 green against the *wrong code*. The one failure only surfaced because the original's extra ingest source, registered as an entry point, leaked into a test.

**Why**: Same package name, same module layout: nothing about a passing run tells you which copy was imported. A green run in the host env says nothing about the port. Check `python -c "import memstore; print(memstore.__file__)"` before trusting results. Also tell users that `python -m memstore` in that env still runs the original.

---

## port-checklists-miss-data-conventions (November 2026)

**Rule**: When porting code out of a host project, look for the host's *data formats* as well as its named specifics (paths, env names, sources). The memstore port checklist removed every name from the originating project, but the diary parser still encoded that project's diary habits: `###` lessons as peer entries, `**Month YYYY Lessons**` dividers, `Lesson N:` title prefixes. Memtoad has never used any of them, and the `###`-peer rule actively split memtoad lessons that have sub-headings.

**Why**: Format tolerances look generic ("it just accepts more"), so a name-based sweep passes them. A tolerance that changes how a valid input of the target format is parsed is a bug, not leniency. Check each parser rule against the target project's own templates (here, the README and bootstrap templates).

---

## plugin-installs-are-pinned-not-live (August 2026)

**Rule**: Never describe pushing to GitHub as updating already-installed copies of the plugin. Each install is pinned to a `version` + `gitCommitSha` in `~/.claude/plugins/installed_plugins.json`, and the code actually read at runtime is a cached copy under `~/.claude/plugins/cache/`. Propagating a change requires `claude plugin marketplace update` then `claude plugin update` per machine, followed by a restart. Critically, `claude plugin update` gates on the `version` field in `.claude-plugin/plugin.json` changing — a content-only push with the version left unbumped will not be picked up as an available update, even though the commit sha moved. Bump the version (semver: new skill/feature = minor, fix = patch) as part of any commit that should actually reach installed copies.

**Why**: It's easy to assume the plugin model behaves like a live symlink to the GitHub repo, especially since the whole point of the plugin conversion (→ plugin-not-installed) was to kill the "frozen firmware" problem of copy-in-project installs. It's a real improvement — one update command per machine instead of a re-install per project — but it is not automatic, and documentation or user-facing claims that imply push-to-deploy would be wrong.

---

## install-script-is-the-last-enforcement-point (June 2026; superseded by committer-diary-prep-only)

**Rule**: Any workflow step that must happen before every commit belongs in CLAUDE.md — written there by the install script, not just documented in the README.

**Why**: After a fresh Memtoad install the user did a full work session and committed without running `/session-historian` — because CLAUDE.md had no instruction to do so. The README documented the workflow clearly, but README is read once at install time. CLAUDE.md is loaded into every session. The install script is the only moment where Memtoad can guarantee the instruction is placed where it will be seen. If the install script doesn't write it, no amount of documentation fixes the gap — the next session starts blind. (→ pre-commit-workflow-in-claude-md)

---

## archive-files-are-never-read (June 2026)

**Rule**: Do not archive diary files by date or size — archived content is never read and accumulates silently.

**Why**: Our experience with predecessor system archived diary files when they exceeded a size threshold, producing 35 files and 1.8MB of content. The startup skill was hardcoded to load only three files. No skill ever loaded the archive files. The content that most needed to persist — lessons from early decisions — was exactly the content most likely to be archived and never retrieved. The archive gave the illusion of preservation while providing none of the benefit. (→ three-files-no-archiving)
