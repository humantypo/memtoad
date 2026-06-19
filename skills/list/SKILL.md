---
name: list
description: List all available Memtoad slash commands. Use when the user asks what commands are available, what Memtoad can do, or mentions "what commands do I have".
---

Output the following list of available Memtoad commands directly — do not spawn an agent, do not read any files.

```
Available Memtoad commands
────────────────────────────────────────
  /bootstrap          Set up Memtoad for this project and populate the diary
  /startup            Load full project context at session start
  /committer          Update diary + commit staged changes atomically
  /session-historian  Write diary entries for the current session (runs inline)
  /grill-me           Stress-test a plan with diary-informed questions
  /context-capture    Checkpoint current WIP state to the diary
  /list               Show this list
────────────────────────────────────────
Type /command-name to invoke. Skills are provided by the Memtoad plugin.
```
