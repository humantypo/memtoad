#!/bin/bash
# PreToolUse hook (Bash matcher). Denies `git commit` until diary/ is staged,
# unless every staged path is documentation-only (mirrors the skip-list in
# skills/committer/SKILL.md) or the project hasn't adopted Memtoad's diary
# convention at all.

input=$(cat)
command=$(jq -r '.tool_input.command // empty' <<<"$input")
cwd=$(jq -r '.cwd // empty' <<<"$input")

if [[ -z "$command" || -z "$cwd" ]]; then
  exit 0
fi

# Only act on `git commit` invocations.
if [[ ! "$command" =~ (^|[[:space:];\&\|])git[[:space:]]+commit([[:space:]]|$) ]]; then
  exit 0
fi

if ! cd "$cwd" 2>/dev/null; then
  exit 0
fi

# Project hasn't adopted the diary convention — don't gate it.
if [[ ! -d diary ]]; then
  exit 0
fi

staged=$(git diff --cached --name-only 2>/dev/null)

if [[ -z "$staged" ]]; then
  exit 0
fi

diary_staged=false
non_doc_staged=false

while IFS= read -r path; do
  if [[ -z "$path" ]]; then
    continue
  fi
  case "$path" in
    diary/*)
      diary_staged=true
      ;;
    CLAUDE.md|.claude/*)
      : # doc-only, always allowed
      ;;
    *.md)
      # Root-level *.md is doc-only; nested *.md (commands/, skills/, etc.)
      # is not, matching the skip-list in skills/committer/SKILL.md.
      if [[ "$path" == */* ]]; then
        non_doc_staged=true
      fi
      ;;
    *)
      non_doc_staged=true
      ;;
  esac
done <<<"$staged"

if [[ "$diary_staged" == true || "$non_doc_staged" == false ]]; then
  exit 0
fi

jq -n '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: "Diary files are not staged. Run /memtoad:committer first to update and stage diary/, then commit."
  }
}'
exit 0
