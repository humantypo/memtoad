#!/usr/bin/env bash
# install-new.sh — Install Memtoad into a new project (no existing docs or decisions).
# Automates steps 1–3 from README ## Init: new project, configures git tracking,
# then prints the bootstrap prompt.
#
# Usage:
#   ./scripts/install-new.sh <target>
#   ./scripts/install-new.sh --hybrid <target>   # skip git mode question

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEMTOAD_ROOT="$(dirname "$SCRIPT_DIR")"

# ── Parse arguments ────────────────────────────────────────────────────────────

GIT_MODE=""
TARGET=""

for arg in "$@"; do
  case "$arg" in
    --shared)  GIT_MODE="shared" ;;
    --hybrid)  GIT_MODE="hybrid" ;;
    --private) GIT_MODE="private" ;;
    -*)        echo "Unknown flag: $arg"; exit 1 ;;
    *)         TARGET="$arg" ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 [--shared|--hybrid|--private] <target-project-directory>"
  exit 1
fi

if [[ ! -d "$TARGET" ]]; then
  echo "Error: directory not found: $TARGET"
  exit 1
fi

TARGET="$(cd "$TARGET" && pwd)"
PROJECT_NAME="$(basename "$TARGET")"
TODAY="$(date '+%B %d, %Y')"

echo "Installing Memtoad (new project) into: $TARGET"
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
    private) entries+=$'\n'"diary/" ;;
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
- [\`diary/lessons_learned.md\`](diary/lessons_learned.md) — anti-patterns and hard-won insights"

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

# ── Done: print bootstrap prompt ──────────────────────────────────────────────

cat << 'EOF'

════════════════════════════════════════════════════════════════
 Installation complete — steps 1–4 done.
════════════════════════════════════════════════════════════════

Step 5: Open Claude Code in the project directory and paste this
        bootstrap prompt:

────────────────────────────────────────────────────────────────
I just initialized Memtoad in this project. Please read CLAUDE.md
and any existing README or design docs, then write a first draft
of the three diary files based on what you find.

- diary/session_context.md: describe the current state of the
  project in one paragraph. Leave Most Recent Sessions empty.
  Populate Open Items with any deferred work found in the docs.

- diary/architectural_decisions.md: write one entry for the most
  important design choice already made, using the
  ## slug-based-header (Month YYYY) format.

- diary/lessons_learned.md: leave it with just the header —
  no entries yet.
────────────────────────────────────────────────────────────────

Step 6: Run /startup to verify Claude can synthesize the diary
        into a coherent briefing.

EOF
