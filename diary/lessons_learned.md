# Lessons Learned

Anti-patterns, failure modes, and hard-won rules. Most recent at top. Add an entry only when
a lesson is non-obvious — if it's standard practice or documented in the framework, skip it.

Cross-references use (→ slug-name) notation.

---

## archive-files-are-never-read (June 2026)

**Rule**: Do not archive diary files by date or size — archived content is never read and accumulates silently.

**Why**: Our experience with predecessor system archived diary files when they exceeded a size threshold, producing 35 files and 1.8MB of content. The startup skill was hardcoded to load only three files. No skill ever loaded the archive files. The content that most needed to persist — lessons from early decisions — was exactly the content most likely to be archived and never retrieved. The archive gave the illusion of preservation while providing none of the benefit. (→ three-files-no-archiving)
