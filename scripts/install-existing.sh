#!/usr/bin/env bash
# install-existing.sh — Install Memtoad into a project with existing docs and decisions.
# Automates steps 1–3, configures git tracking, then prints the Claude prompts
# for steps 4–8 in order.
#
# Usage:
#   ./scripts/install-existing.sh <target> [doc1 doc2 ...]
#   ./scripts/install-existing.sh --private <target> ARCHITECTURE.md docs/design.md
#
# Optional doc paths (relative to target) are substituted into the Claude prompts.
# If omitted, defaults to CLAUDE.md and README.md.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEMTOAD_ROOT="$(dirname "$SCRIPT_DIR")"

# ── Parse arguments ────────────────────────────────────────────────────────────

GIT_MODE=""
TARGET=""
EXTRA_DOCS=()

for arg in "$@"; do
  case "$arg" in
    --shared)  GIT_MODE="shared" ;;
    --hybrid)  GIT_MODE="hybrid" ;;
    --private) GIT_MODE="private" ;;
    -*)        echo "Unknown flag: $arg"; exit 1 ;;
    *)
      if [[ -z "$TARGET" ]]; then
        TARGET="$arg"
      else
        EXTRA_DOCS+=("$arg")
      fi
      ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 [--shared|--hybrid|--private] <target-project-directory> [doc1 doc2 ...]"
  exit 1
fi

if [[ ! -d "$TARGET" ]]; then
  echo "Error: directory not found: $TARGET"
  exit 1
fi

TARGET="$(cd "$TARGET" && pwd)"
PROJECT_NAME="$(basename "$TARGET")"
TODAY="$(date '+%B %d, %Y')"

[[ ${#EXTRA_DOCS[@]} -gt 0 ]] && DOC_LIST="${EXTRA_DOCS[*]}" || DOC_LIST="CLAUDE.md, README.md"

echo "Installing Memtoad (existing project) into: $TARGET"
echo

# ── Helpers ────────────────────────────────────────────────────────────────────

green() { printf '\033[32m%s\033[0m' "$*"; }
dim()   { printf '\033[2m%s\033[0m' "$*"; }
bold()  { printf '\033[1m%s\033[0m' "$*"; }

is_git_repo() { git -C "$1" rev-parse --git-dir &>/dev/null 2>&1; }

detect_git_mode() {
  local gitignore="$1/.gitignore"
  if [[ -f "$gitignore" ]]; then
    local line
    line="$(grep "^# Memtoad \[mode:" "$gitignore" 2>/dev/null | head -1)"
    [[ -n "$line" ]] && echo "$line" | sed 's/# Memtoad \[mode: *\([a-z]*\)\].*/\1/' && return
  fi
  echo ""
}

ask_git_mode() {
  local current="${1:-}"
  local default_num="2" default_name="hybrid"
  if [[ -n "$current" ]]; then
    case "$current" in
      shared)  default_num="1"; default_name="shared" ;;
      hybrid)  default_num="2"; default_name="hybrid" ;;
      private) default_num="3"; default_name="private" ;;
    esac
  fi

  echo >&2
  echo "  How should diary files be tracked in git?" >&2
  echo >&2
  echo "    1) Shared  — track all three diary files" >&2
  echo "                 Best for: solo projects or a single active contributor" >&2
  echo "    2) Hybrid  — track decisions + lessons, ignore session_context.md" >&2
  echo "                 Best for: teams (shared knowledge, private work state)" >&2
  echo "    3) Private — ignore entire diary/ directory" >&2
  echo "                 Best for: each contributor manages their own diary locally" >&2
  echo >&2
  [[ -n "$current" ]] && echo "  Current mode: $(bold "$current")" >&2
  read -r -p "  Choice [$default_num / $default_name]: " choice
  choice="${choice:-$default_num}"
  case "$choice" in
    1|s|shared)  echo "shared"  ;;
    2|h|hybrid)  echo "hybrid"  ;;
    3|p|private) echo "private" ;;
    *)           echo "$default_name" ;;
  esac
}

update_gitignore() {
  local target="$1" mode="$2"
  local gitignore="$target/.gitignore"

  local entries="MEMTOAD_INIT.md"
  case "$mode" in
    hybrid)  entries+=$'\n'"diary/session_context.md" ;;
    private) entries+=$'\n'"diary/"$'\n'"CLAUDE.md" ;;
  esac

  local action="Created"
  local existing=""

  if [[ -f "$gitignore" ]]; then
    action="Updated"
    if grep -q "^# Memtoad \[mode:" "$gitignore" 2>/dev/null; then
      existing="$(perl -0pe 's/\n?# Memtoad \[mode:[^\n]*\n.*?# End Memtoad\n?//s' "$gitignore")"
    else
      existing="$(cat "$gitignore")"
    fi
    existing="$(printf '%s' "$existing" | perl -0pe 's/\s+$//')"
  fi

  {
    [[ -n "$existing" ]] && printf '%s\n' "$existing"
    printf '\n# Memtoad [mode: %s]\n%s\n# End Memtoad\n' "$mode" "$entries"
  } > "$gitignore"

  echo "  $(green "$action  .gitignore (diary tracking: $mode)")"
}

# ── Step 1: diary/ ────────────────────────────────────────────────────────────

echo "Step 1/4  Creating diary/ with skeleton files ..."
mkdir -p "$TARGET/diary"

for f in session_context.md architectural_decisions.md lessons_learned.md; do
  dest="$TARGET/diary/$f"
  if [[ -f "$dest" ]]; then
    echo "          $(dim "Skipping diary/$f — already exists")"
  else
    cp "$MEMTOAD_ROOT/templates/$f" "$dest"
    perl -pi -e "s/\[Project Name\]/$PROJECT_NAME/g; s/\[Date\]/$TODAY/g" "$dest"
    echo "          $(green "Created  diary/$f")"
  fi
done

# ── Step 2: .claude/ skills and commands ──────────────────────────────────────

echo "Step 2/4  Installing skills and command wrappers ..."
mkdir -p \
  "$TARGET/.claude/skills/startup" \
  "$TARGET/.claude/skills/session-historian" \
  "$TARGET/.claude/skills/grill-me" \
  "$TARGET/.claude/commands"

for skill in startup session-historian grill-me; do
  dest="$TARGET/.claude/skills/$skill/SKILL.md"
  if [[ -f "$dest" ]]; then
    echo "          $(dim "Skipping .claude/skills/$skill/SKILL.md — already exists")"
  else
    cp "$MEMTOAD_ROOT/.claude/skills/$skill/SKILL.md" "$dest"
    echo "          $(green "Created  .claude/skills/$skill/SKILL.md")"
  fi
done

for cmd in startup session-historian grill-me; do
  dest="$TARGET/.claude/commands/$cmd.md"
  if [[ -f "$dest" ]]; then
    echo "          $(dim "Skipping .claude/commands/$cmd.md — already exists")"
  else
    cp "$MEMTOAD_ROOT/.claude/commands/$cmd.md" "$dest"
    echo "          $(green "Created  .claude/commands/$cmd.md")"
  fi
done

# ── Step 3: CLAUDE.md ─────────────────────────────────────────────────────────

echo "Step 3/4  Updating CLAUDE.md ..."
CLAUDE_FILE="$TARGET/CLAUDE.md"
PROJECT_MEMORY_BLOCK="## Project Memory

Cross-project decisions, lessons, and current work live in [\`diary/\`](diary/):
- [\`diary/session_context.md\`](diary/session_context.md) — current state and recent work
- [\`diary/architectural_decisions.md\`](diary/architectural_decisions.md) — design principles and non-negotiable patterns
- [\`diary/lessons_learned.md\`](diary/lessons_learned.md) — anti-patterns and hard-won insights

**Before making any git commit**, always run \`/session-historian\` first to update the diary with what was accomplished. The diary is the primary context source for future sessions and for \`/grill-me\` — skipping this step means the next session starts blind.

Commit workflow:
1. Tests pass
2. \`/session-historian\` — update diary
3. \`git commit\` — with a message informed by what \`/session-historian\` recorded"

if [[ -f "$CLAUDE_FILE" ]]; then
  if grep -q "## Project Memory" "$CLAUDE_FILE"; then
    echo "          $(dim "CLAUDE.md already has a '## Project Memory' section — skipping")"
  else
    printf '\n\n%s\n' "$PROJECT_MEMORY_BLOCK" >> "$CLAUDE_FILE"
    echo "          $(green "Appended Project Memory section to existing CLAUDE.md")"
  fi
else
  printf '%s\n' "$PROJECT_MEMORY_BLOCK" > "$CLAUDE_FILE"
  echo "          $(green "Created CLAUDE.md with Project Memory section")"
fi

# ── Step 4: git tracking ──────────────────────────────────────────────────────

echo "Step 4/4  Configuring git tracking ..."
if is_git_repo "$TARGET"; then
  if [[ -z "$GIT_MODE" ]]; then
    current="$(detect_git_mode "$TARGET")"
    GIT_MODE="$(ask_git_mode "$current")"
    echo
  fi
  update_gitignore "$TARGET" "$GIT_MODE"
else
  echo "          $(dim "Not a git repository — skipping")"
  echo "          $(dim "(Re-run after 'git init' to configure .gitignore)")"
fi

# ── Done: print extraction prompts ────────────────────────────────────────────

cat << EOF

════════════════════════════════════════════════════════════════
 Installation complete — steps 1–4 done.
════════════════════════════════════════════════════════════════

Open Claude Code in the project directory, then run steps 5–9
in sequence in the same session.

Docs Claude will read: $DOC_LIST

────────────────────────────────────────────────────────────────
 Step 5 of 9 — Extract architectural decisions
────────────────────────────────────────────────────────────────
Read $DOC_LIST. For each non-obvious architectural decision you
find — a choice where a future engineer would ask "why did they
do it this way?" and the answer is not obvious from the code —
write a dated entry in diary/architectural_decisions.md using
the ## slug-based-header (Month YYYY) format. Extract the
decision and its reasoning; do not copy text verbatim. Skip
anything that is obvious best practice or already enforced by
tooling.

────────────────────────────────────────────────────────────────
 Step 6 of 9 — Extract lessons learned
────────────────────────────────────────────────────────────────
Read the same docs. For each anti-pattern, failure mode, or
hard-won rule you find — things learned through experience, not
from a manual — write an entry in diary/lessons_learned.md using
the ## slug-based-header (Month YYYY) format with a one-sentence
Rule: and a Why: section. Skip general advice; focus on
project-specific lessons with a specific incident or failure
behind them.

────────────────────────────────────────────────────────────────
 Step 7 of 9 — Write session_context.md
────────────────────────────────────────────────────────────────
Based on what you have read, write diary/session_context.md. The
Current State section should be one paragraph describing what the
system is and what state it is in right now. Leave Most Recent
Sessions empty — that will be filled in going forward. Populate
Open Items with any known deferred work you found in the docs.

────────────────────────────────────────────────────────────────
 Step 8 of 9 — Prune (manual)
────────────────────────────────────────────────────────────────
Read all three diary files yourself and remove:
  - Anything obvious from the code or standard in the framework
  - Anything already enforced by tests, linters, or CI
  - Any entry whose Why is "because we always do it this way"
  - Any entry without a specific incident or reasoning behind it

────────────────────────────────────────────────────────────────
 Step 9 of 9 — Verify
────────────────────────────────────────────────────────────────
Run /startup to confirm Claude synthesizes the diary into a
coherent briefing that a new contributor would find useful.

EOF
