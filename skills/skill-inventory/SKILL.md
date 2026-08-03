---
name: skill-inventory
description: Inventory every skill visible in this environment — classify each as local project, installed plugin, or provider built-in, evaluate what it does, and report overlaps, software-development lifecycle gaps, hard vs soft stop behavior, tool footprint, composition between skills, and staleness. Tracks first/last-seen dates in a state file so newly-appeared skills are called out. Use when the user wants a skill/plugin audit, asks "what skills do I have", wants to find redundant or conflicting skills, or wants to manage a growing set of plugins.
---

Use the Agent tool to spawn a `general-purpose` subagent with the prompt below. This is a
cold filesystem sweep independent of the current conversation — spawning protects the
main context window from the volume of files read, the same reason `startup` spawns
rather than running inline.

Prompt to give the subagent:

---

Audit every Claude Code skill visible on this machine for the current project and produce
a report. Work entirely read-only except for the one state file named at the end. Follow
these phases:

**Phase 1 — Gather.**

1. *Currently visible skills*: note the names and one-line descriptions of whatever skills
   are listed as available in your own system context for this session.
2. *Local project skills*: check for `.claude/skills/*/SKILL.md` in the current working
   directory (and, if the project itself defines skills at a repo-root `skills/` directory
   the way a plugin source repo does, include those too). Read each in full.
3. *Installed plugins*: read `~/.claude/plugins/installed_plugins.json`. For every plugin
   entry whose `projectPath` matches the current working directory (or `git rev-parse
   --show-toplevel` if cwd is a subdirectory), or that has no project scoping at all
   (global/user-scoped), resolve its `installPath` and read every `skills/*/SKILL.md`
   under it in full.
4. *Marketplace drift*: for each installed plugin found in step 3, locate its marketplace
   clone under `~/.claude/plugins/marketplaces/<marketplace-name>/` and run `git
   rev-parse HEAD` there. Compare against the `gitCommitSha` recorded in
   `installed_plugins.json` for that install. A mismatch means an update is available —
   note it, but do not run any `claude plugin update` command yourself.
5. *Provider built-ins*: name known CLI-native commands with no backing SKILL.md (e.g.
   `/compact`, `/clear`, `/help`, `/resume`) as a distinct category. Caveat this list
   explicitly as best-effort and worth spot-checking against `/help`, since it isn't
   file-backed and can drift across CLI versions.

**Phase 2 — Classify.** Tag every skill found in steps 1-3 as exactly one of:
- **local** — defined in this project's own skills directory
- **plugin** — resolved via `installed_plugins.json`; annotate with plugin name, version,
  commit, and whether step 4 found an update available
- **built-in** — from step 5, provider-native, no file

**Phase 3 — Evaluate and report.** For each skill, form a one-line judgment of its actual
purpose from its description and (for local/plugin skills) its body content. Then produce
these sections, in order:

1. **Inventory table** — name, classification, one-line purpose, plugin+version where
   applicable.
2. **New since last run** — see the state-file step below; list any skill present now that
   wasn't in the last recorded snapshot.
3. **Overlap** — group skills whose stated purpose or trigger conditions cover materially
   the same ground (e.g. two skills that both want to own the commit workflow, two that
   both do security review). Name the skills in each group and what they overlap on. This
   is a flag for human judgment, not a recommendation to delete anything.
4. **Software-development-lifecycle gaps** — check coverage against this fixed checklist:
   planning/spec, scaffolding, coding, testing, code review, security review,
   documentation, dependency/version management, deployment/release, incident/debugging,
   memory/context continuity. Mark each covered or not-covered based on what's in the
   inventory, and name which skill covers it when it is.
5. **Hard stops vs. soft stops** — scan each skill body for gating language. **Hard stop**:
   unconditional language like "always ask before", "MUST confirm", "never do X without
   asking", or a call to `AskUserQuestion` that isn't behind a conditional. **Soft stop**:
   conditional gating — behavior that branches on staged files, a mode/setting, or a
   `disable-model-invocation` frontmatter flag (e.g. a skill with a FULL vs LIGHTWEIGHT
   split). List which skills have which, and quote the specific triggering phrase.
6. **Tool/permission footprint** — for skills with an `allowed-tools:` frontmatter field,
   report it directly. For skills without one, do a best-effort text scan for mentions of
   Bash, Write, Edit, WebFetch, or similar, and report those findings labeled explicitly as
   a heuristic guess, not a guarantee.
7. **Composition graph** — list any skill whose body instructs spawning another named
   skill or subagent (e.g. one skill that invokes another internally), so it's clear which
   skills are user-facing entry points versus internal building blocks.
8. **Staleness** — plugins flagged as update-available in Phase 1 step 4, plus any local
   skill file that references a path or file that no longer exists on disk.

**State file — new-skill tracking.** Compute:
`STATE_FILE=~/.claude/projects/$(pwd | tr '/' '-' | sed 's/^-//')/skill_inventory_state.json`
Read it if present (default to `{"last_run_date": null, "skills": {}}` if not). Key every
skill found in Phase 1/2 as `"<classification>:<plugin-name-or-project>:<skill-name>"`.
Diff current keys against the stored `skills` map to compute the "New since last run"
section. Hash each skill's description string (sha1 is fine) to detect changes to
existing skills if useful context for the report. After the report is assembled, overwrite
`STATE_FILE` with the fresh snapshot (`first_seen` preserved from the old entry when the
key already existed, `last_seen` set to today, `description_hash` updated) and today's
date as `last_run_date`. Create the parent directory first if it doesn't exist.

Report the full findings back as your final output — this is what gets shown to the user.

---

**When to invoke**: on demand, when the user wants to audit their skills/plugins, find
redundant tooling, or check what's new since the last audit. Never auto-triggered at
session start — that is `startup`'s job.
