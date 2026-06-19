# CLAUDE.md — Memtoad

This repo is the reference implementation for the Memtoad project memory plugin. It is a Claude Code plugin: skills and commands live in `skills/` and `commands/` at the repo root, and the plugin manifest is at `.claude-plugin/plugin.json`.

## Project Memory
<!-- memtoad:version:2 -->
- [diary/session_context.md](diary/session_context.md) — current state and recent work
- [diary/architectural_decisions.md](diary/architectural_decisions.md) — design principles and non-negotiable patterns
- [diary/lessons_learned.md](diary/lessons_learned.md) — anti-patterns and hard-won insights

**Before any git commit**, run `/committer` — it updates the diary and crafts the commit message in one step.

Commit workflow:
1. Tests pass
2. `/committer` — updates diary + commits

## Repo structure

```
.claude-plugin/
  plugin.json                         — plugin manifest
skills/
  bootstrap/SKILL.md                  — project setup + diary population
  startup/SKILL.md                    — session context loader
  session-historian/SKILL.md          — diary writer
  grill-me/SKILL.md                   — plan interrogator
  committer/SKILL.md                  — session-historian + commit orchestrator
  context-capture/SKILL.md            — WIP state snapshot
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
