# CLAUDE.md — Memtoad

This repo is the reference implementation for the Memtoad project memory plugin. It is a Claude Code plugin: skills and commands live in `skills/` and `commands/` at the repo root, and the plugin manifest is at `.claude-plugin/plugin.json`.

## Project Memory
<!-- memtoad:version:3 -->
- [diary/session_context.md](diary/session_context.md) — current state and recent work
- [diary/architectural_decisions.md](diary/architectural_decisions.md) — design principles and non-negotiable patterns
- [diary/lessons_learned.md](diary/lessons_learned.md) — anti-patterns and hard-won insights

Commits that touch more than documentation are gated on `diary/` being staged — a plugin hook denies `git commit` otherwise. Run `/committer` first to update and stage the diary.

## Repo structure

```
.claude-plugin/
  plugin.json                         — plugin manifest
hooks/
  hooks.json                          — registers the two hooks below
  check-diary-staged.sh               — PreToolUse: denies git commit until diary/ is staged
  record-commit.sh                    — PostToolUse: updates historian_state.json after a real commit
skills/
  bootstrap/SKILL.md                  — project setup + diary population
  startup/SKILL.md                    — session context loader
  session-historian/SKILL.md          — diary writer
  grill-me/SKILL.md                   — plan interrogator
  committer/SKILL.md                  — updates + stages diary before a commit
  context-capture/SKILL.md            — WIP state snapshot
  skill-inventory/SKILL.md            — skill/plugin audit
  tidy/SKILL.md                       — consolidates superseded decision entries
  list/SKILL.md                       — command listing
commands/
  bootstrap.md / startup.md / ...     — slash command wrappers
diary/                                — this repo's own diary
README.md                             — full documentation (the primary artifact)
```

## Working in this repo

- The README.md is the primary artifact. Keep it accurate with the actual skill files.
- When editing a skill or command, update the corresponding section in README.md in the same session.
- Skills live in `skills/`, not `.claude/skills/` — the plugin system serves them globally.
- Run `/committer` at the end of any session that changes the system design.
- Do not add files beyond the documented structure without updating README.md.
