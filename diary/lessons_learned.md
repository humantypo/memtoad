# Lessons Learned

Anti-patterns, failure modes, and hard-won rules. Most recent at top. Add an entry only when
a lesson is non-obvious — if it's standard practice or documented in the framework, skip it.

Cross-references use (→ slug-name) notation.

---

## install-script-is-the-last-enforcement-point (June 2026)

**Rule**: Any workflow step that must happen before every commit belongs in CLAUDE.md — written there by the install script, not just documented in the README.

**Why**: After a fresh Memtoad install the user did a full work session and committed without running `/session-historian` — because CLAUDE.md had no instruction to do so. The README documented the workflow clearly, but README is read once at install time. CLAUDE.md is loaded into every session. The install script is the only moment where Memtoad can guarantee the instruction is placed where it will be seen. If the install script doesn't write it, no amount of documentation fixes the gap — the next session starts blind. (→ pre-commit-workflow-in-claude-md)

---

## archive-files-are-never-read (June 2026)

**Rule**: Do not archive diary files by date or size — archived content is never read and accumulates silently.

**Why**: Our experience with predecessor system archived diary files when they exceeded a size threshold, producing 35 files and 1.8MB of content. The startup skill was hardcoded to load only three files. No skill ever loaded the archive files. The content that most needed to persist — lessons from early decisions — was exactly the content most likely to be archived and never retrieved. The archive gave the illusion of preservation while providing none of the benefit. (→ three-files-no-archiving)
