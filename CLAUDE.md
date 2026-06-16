# CLAUDE.md — Memtoad

This repo is the reference implementation and documentation for the Memtoad project memory system. It contains the installable skill files, command wrappers, skeleton templates, and full documentation for deploying Memtoad into any Claude Code project.

## Project Memory

This repo uses Memtoad itself:
- [diary/session_context.md](diary/session_context.md) — current state and recent work
- [diary/architectural_decisions.md](diary/architectural_decisions.md) — design principles and non-negotiable patterns
- [diary/lessons_learned.md](diary/lessons_learned.md) — anti-patterns and hard-won insights

**Before making any git commit**, always run `/session-historian` first to update the diary with what was accomplished. The diary is the primary context source for future sessions and for `/grill-me` — skipping this step means the next session starts blind.

Commit workflow:
1. Tests pass
2. `/session-historian` — update diary
3. `git commit` — with a message informed by what `/session-historian` recorded

## Repo structure

```
README.md                           — full documentation (the primary artifact)
templates/                          — blank diary starters for target projects
  session_context.md
  architectural_decisions.md
  lessons_learned.md
diary/                              — this repo's own diary
.claude/
  skills/
    startup/SKILL.md
    session-historian/SKILL.md
    grill-me/SKILL.md
  commands/
    startup.md
    session-historian.md
    grill-me.md
```

## Working in this repo

- The README.md is the primary artifact. Keep it accurate with the actual skill files.
- When editing a skill or command, update the corresponding code block in README.md in the same session.
- Run `/session-historian` at the end of any session that changes the system design.
- Do not add files beyond the documented structure without updating README.md and the design principles section.
