#!/bin/bash
# PostToolUse hook (Bash matcher). After a `git commit` that actually created
# a new commit, updates historian_state.json bookkeeping that skills/committer
# and skills/session-historian use to decide FULL vs LIGHTWEIGHT mode. This
# replaces the bookkeeping that used to live in committer's (now removed)
# commit step.

input=$(cat)
command=$(jq -r '.tool_input.command // empty' <<<"$input")
cwd=$(jq -r '.cwd // empty' <<<"$input")

if [[ -z "$command" || -z "$cwd" ]]; then
  exit 0
fi

if [[ ! "$command" =~ (^|[[:space:];\&\|])git[[:space:]]+commit([[:space:]]|$) ]]; then
  exit 0
fi

if ! cd "$cwd" 2>/dev/null; then
  exit 0
fi

if [[ ! -d diary ]]; then
  exit 0
fi

current_head=$(git rev-parse HEAD 2>/dev/null)
if [[ -z "$current_head" ]]; then
  exit 0
fi

state_dir=~/.claude/projects/$(pwd | tr '/' '-' | sed 's/^-//')
state_file="$state_dir/historian_state.json"

if [[ -f "$state_file" ]]; then
  state=$(cat "$state_file")
else
  state='{"last_full_run_date":"1970-01-01","last_full_run_commit":null,"commits_since_last_full":0,"last_seen_commit":null}'
fi

last_seen=$(jq -r '.last_seen_commit // empty' <<<"$state")

if [[ "$current_head" == "$last_seen" ]]; then
  # Hook fired but no new commit landed (e.g. "nothing to commit", or a
  # pre-commit hook rejected it) — nothing to record.
  exit 0
fi

full_run=false
if git show --name-only --pretty=format: HEAD 2>/dev/null | grep -qx 'diary/architectural_decisions.md'; then
  full_run=true
fi

today=$(date +%Y-%m-%d)

if [[ "$full_run" == true ]]; then
  new_state=$(jq -n \
    --arg commit "$current_head" \
    --arg date "$today" \
    '{last_full_run_date: $date, last_full_run_commit: $commit, commits_since_last_full: 0, last_seen_commit: $commit}')
else
  new_state=$(jq \
    --arg commit "$current_head" \
    '.last_seen_commit = $commit | .commits_since_last_full = ((.commits_since_last_full // 0) + 1)' \
    <<<"$state")
fi

mkdir -p "$state_dir"
printf '%s\n' "$new_state" > "$state_file"

exit 0
