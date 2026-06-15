#!/usr/bin/env bash
# install.sh — Apply Memtoad to a project directory.
#
# Detects whether the target has existing code, confirms the init mode,
# installs skills/commands/diary skeleton, injects CLAUDE.md section,
# configures .gitignore tracking, and (for existing projects) writes
# MEMTOAD_INIT.md with the Claude prompts for steps 4–8.
#
# Usage:
#   ./install.sh <target>                          # smart detection, interactive
#   ./install.sh --update <target>                 # refresh skills/commands + ask git mode
#   ./install.sh --hybrid <target>                 # skip git mode question, use hybrid
#   ./install.sh --update --private <target>       # refresh skills and set private tracking

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Parse arguments ────────────────────────────────────────────────────────────

UPDATE=false
GIT_MODE=""   # shared | hybrid | private — set by flag or interactive prompt
TARGET=""

for arg in "$@"; do
  case "$arg" in
    --update)  UPDATE=true ;;
    --shared)  GIT_MODE="shared" ;;
    --hybrid)  GIT_MODE="hybrid" ;;
    --private) GIT_MODE="private" ;;
    -h|--help)
      cat << 'HELP'
install.sh — Apply Memtoad to a project directory

Usage:
  ./install.sh <target>            Install Memtoad (auto-detects new vs existing project)
  ./install.sh --update <target>   Refresh skill and command files only (never touches diary/)

Git tracking flags (skip interactive prompt):
  --shared    Track all diary files in git
  --hybrid    Track decisions + lessons; ignore session_context.md  [team default]
  --private   Ignore entire diary/ directory

Flags can be combined:
  ./install.sh --update --hybrid <target>
HELP
      exit 0 ;;
    -*) echo "Unknown flag: $arg (try --help)"; exit 1 ;;
    *)  TARGET="$arg" ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 [--update] [--shared|--hybrid|--private] <target-project-directory>"
  echo "       $0 --help"
  exit 1
fi

# ── Display helpers ────────────────────────────────────────────────────────────

bold()  { printf '\033[1m%s\033[0m' "$*"; }
green() { printf '\033[32m%s\033[0m' "$*"; }
dim()   { printf '\033[2m%s\033[0m' "$*"; }

confirm() {
  local prompt="$1" default="${2:-y}"
  local yn_hint
  [[ "$default" == "y" ]] && yn_hint="[Y/n]" || yn_hint="[y/N]"
  read -r -p "$(bold "$prompt") $yn_hint " response
  response="${response:-$default}"
  [[ "$response" =~ ^[yY] ]]
}

# ── Project detection helpers ──────────────────────────────────────────────────

is_memtoad_installed() {
  [[ -f "$1/.claude/skills/session-historian/SKILL.md" ]]
}

detect_project_type() {
  local dir="$1"
  [[ -z "$(ls -A "$dir" 2>/dev/null)" ]] && { echo "new"; return; }

  local indicators=(
    ".git" "README.md" "CLAUDE.md"
    "package.json" "requirements.txt" "pyproject.toml"
    "Gemfile" "go.mod" "Cargo.toml" "pom.xml" "Makefile" ".gitignore"
  )
  for f in "${indicators[@]}"; do
    [[ -e "$dir/$f" ]] && { echo "existing"; return; }
  done

  if find "$dir" -maxdepth 3 -type f \( \
      -name "*.py" -o -name "*.js"   -o -name "*.ts"   -o -name "*.tsx" \
      -o -name "*.go" -o -name "*.rb" -o -name "*.java" -o -name "*.sh" \
      -o -name "*.rs" -o -name "*.php" -o -name "*.swift" -o -name "*.kt" \
      -o -name "*.cs" -o -name "*.cpp" -o -name "*.c"    -o -name "*.ex" \
    \) 2>/dev/null | grep -q .; then
    echo "existing"; return
  fi

  echo "new"
}

detect_docs() {
  local dir="$1"
  local docs=() seen=() out=()

  for f in README.md CLAUDE.md ARCHITECTURE.md CONTRIBUTING.md DESIGN.md; do
    [[ -f "$dir/$f" ]] && docs+=("$f")
  done

  for d in docs doc documentation; do
    if [[ -d "$dir/$d" ]]; then
      while IFS= read -r -d '' f; do
        docs+=("${f#"$dir"/}")
      done < <(find "$dir/$d" -maxdepth 2 -name "*.md" -print0 2>/dev/null | sort -z)
    fi
  done

  for item in "${docs[@]+"${docs[@]}"}"; do
    local skip=false
    for s in "${seen[@]+"${seen[@]}"}"; do [[ "$s" == "$item" ]] && skip=true && break; done
    $skip || { seen+=("$item"); out+=("$item"); }
  done

  echo "${out[*]+"${out[*]}"}"
}

# ── Git tracking helpers ───────────────────────────────────────────────────────

is_git_repo() {
  git -C "$1" rev-parse --git-dir &>/dev/null 2>&1
}

detect_git_mode() {
  local gitignore="$1/.gitignore"
  if [[ -f "$gitignore" ]]; then
    local line
    line="$(grep "^# Memtoad \[mode:" "$gitignore" 2>/dev/null | head -1)"
    if [[ -n "$line" ]]; then
      echo "$line" | sed 's/# Memtoad \[mode: *\([a-z]*\)\].*/\1/'
      return
    fi
  fi
  echo ""
}

ask_git_mode() {
  local current="${1:-}"
  local default_num="2"
  local default_name="hybrid"

  if [[ -n "$current" ]]; then
    case "$current" in
      shared)  default_num="1"; default_name="shared" ;;
      hybrid)  default_num="2"; default_name="hybrid" ;;
      private) default_num="3"; default_name="private" ;;
    esac
  fi

  # All display output goes to stderr so command substitution $() captures
  # only the returned mode name, not the menu text.
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

  # Build the entries block for this mode
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
      # Strip the old Memtoad section
      existing="$(perl -0pe 's/\n?# Memtoad \[mode:[^\n]*\n.*?# End Memtoad\n?//s' "$gitignore")"
    else
      existing="$(cat "$gitignore")"
    fi
    # Trim trailing whitespace
    existing="$(printf '%s' "$existing" | perl -0pe 's/\s+$//')"
  fi

  {
    [[ -n "$existing" ]] && printf '%s\n' "$existing"
    printf '\n# Memtoad [mode: %s]\n%s\n# End Memtoad\n' "$mode" "$entries"
  } > "$gitignore"

  echo "  $(green "$action  .gitignore (diary tracking: $mode)")"
}

# ── File installation ──────────────────────────────────────────────────────────

install_files() {
  local target="$1" mode="${2:-normal}"

  if [[ "$mode" != "update" ]]; then
    echo "  Creating diary/ ..."
    mkdir -p "$target/diary"
    local project_name today
    project_name="$(basename "$target")"
    today="$(date '+%B %d, %Y')"

    for f in session_context.md architectural_decisions.md lessons_learned.md; do
      local dest="$target/diary/$f"
      if [[ -f "$dest" ]]; then
        echo "  $(dim "Skipped  diary/$f (already exists)")"
      else
        cp "$SCRIPT_DIR/templates/$f" "$dest"
        perl -pi -e "s/\[Project Name\]/$project_name/g; s/\[Date\]/$today/g" "$dest"
        echo "  $(green "Created  diary/$f")"
      fi
    done
  fi

  echo "  Installing skills and commands ..."
  mkdir -p \
    "$target/.claude/skills/startup" \
    "$target/.claude/skills/session-historian" \
    "$target/.claude/skills/grill-me" \
    "$target/.claude/commands"

  for skill in startup session-historian grill-me; do
    local src="$SCRIPT_DIR/.claude/skills/$skill/SKILL.md"
    local dest="$target/.claude/skills/$skill/SKILL.md"
    if [[ "$src" -ef "$dest" ]]; then
      echo "  $(dim "Skipped  .claude/skills/$skill/SKILL.md (source is destination)")"
    elif [[ -f "$dest" && "$mode" != "update" ]]; then
      echo "  $(dim "Skipped  .claude/skills/$skill/SKILL.md (already exists)")"
    else
      cp "$src" "$dest"
      [[ "$mode" == "update" ]] \
        && echo "  $(green "Updated  .claude/skills/$skill/SKILL.md")" \
        || echo "  $(green "Created  .claude/skills/$skill/SKILL.md")"
    fi
  done

  for cmd in startup session-historian grill-me; do
    local src="$SCRIPT_DIR/.claude/commands/$cmd.md"
    local dest="$target/.claude/commands/$cmd.md"
    if [[ "$src" -ef "$dest" ]]; then
      echo "  $(dim "Skipped  .claude/commands/$cmd.md (source is destination)")"
    elif [[ -f "$dest" && "$mode" != "update" ]]; then
      echo "  $(dim "Skipped  .claude/commands/$cmd.md (already exists)")"
    else
      cp "$src" "$dest"
      [[ "$mode" == "update" ]] \
        && echo "  $(green "Updated  .claude/commands/$cmd.md")" \
        || echo "  $(green "Created  .claude/commands/$cmd.md")"
    fi
  done
}

update_claude_md() {
  local target="$1"
  local claude_file="$target/CLAUDE.md"
  local block
  block="## Project Memory

Cross-project decisions, lessons, and current work live in [\`diary/\`](diary/):
- [\`diary/session_context.md\`](diary/session_context.md) — current state and recent work
- [\`diary/architectural_decisions.md\`](diary/architectural_decisions.md) — design principles and non-negotiable patterns
- [\`diary/lessons_learned.md\`](diary/lessons_learned.md) — anti-patterns and hard-won insights"

  if [[ -f "$claude_file" ]]; then
    if grep -q "## Project Memory" "$claude_file"; then
      echo "  $(dim "Skipped  CLAUDE.md (Project Memory section already present)")"
    else
      printf '\n\n%s\n' "$block" >> "$claude_file"
      echo "  $(green "Updated  CLAUDE.md (appended Project Memory section)")"
    fi
  else
    printf '%s\n' "$block" > "$claude_file"
    echo "  $(green "Created  CLAUDE.md")"
  fi
}

handle_git_tracking() {
  local target="$1"

  if ! is_git_repo "$target"; then
    echo "  $(dim "Not a git repository — skipping tracking setup")"
    echo "  $(dim "(Re-run install.sh after 'git init' to configure .gitignore)")"
    return
  fi

  if [[ -z "$GIT_MODE" ]]; then
    local current
    current="$(detect_git_mode "$target")"
    GIT_MODE="$(ask_git_mode "$current")"
    echo
  fi

  update_gitignore "$target" "$GIT_MODE"
}

write_init_file() {
  local target="$1" docs="$2"
  local out="$target/MEMTOAD_INIT.md"

  cat > "$out" << INITFILE
# Memtoad Initialization Prompts

Run these prompts in Claude Code **in order, in the same session**.
Delete this file when initialization is complete.

**Docs for Claude to reference:** $docs

---

## Step 4 — Extract architectural decisions

Paste into Claude Code:

> Read $docs. For each non-obvious architectural decision you find — a choice where a
> future engineer would ask "why did they do it this way?" and the answer is not obvious
> from the code — write a dated entry in \`diary/architectural_decisions.md\` using the
> \`## slug-based-header (Month YYYY)\` format. Extract the decision and its reasoning;
> do not copy text verbatim. Skip anything that is obvious best practice or already
> enforced by tooling.

---

## Step 5 — Extract lessons learned

Paste into Claude Code (same session):

> Read the same docs. For each anti-pattern, failure mode, or hard-won rule you find —
> things learned through experience, not from a manual — write an entry in
> \`diary/lessons_learned.md\` using the \`## slug-based-header (Month YYYY)\` format
> with a one-sentence **Rule:** and a **Why:** section. Skip general advice; focus on
> project-specific lessons with a specific incident or failure behind them.

---

## Step 6 — Write session_context.md

Paste into Claude Code (same session):

> Based on what you have read, write \`diary/session_context.md\`. The Current State
> section should be one paragraph describing what the system is and what state it is in
> right now. Leave Most Recent Sessions empty — that will be filled in going forward.
> Populate Open Items with any known deferred work you found in the docs.

---

## Step 7 — Prune (you do this, not Claude)

Read all three diary files yourself and remove:
- Anything obvious from the code or standard in the framework
- Anything already enforced by tests, linters, or CI
- Any entry whose Why is "because we always do it this way"
- Any entry without a specific incident or reasoning behind it

---

## Step 8 — Verify

Run \`/startup\` to confirm Claude synthesizes the diary into a coherent briefing
that a new contributor would actually find useful.

---

*Delete this file after initialization is complete.*
INITFILE

  echo "  $(green "Created  MEMTOAD_INIT.md (prompts for steps 4–8)")"
}

# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

# ── Ensure target exists ───────────────────────────────────────────────────────

JUST_CREATED=false
if [[ ! -d "$TARGET" ]]; then
  echo
  echo "$(bold "Directory not found:") $TARGET"
  if confirm "Create it?"; then
    mkdir -p "$TARGET"
    JUST_CREATED=true
    echo "$(green "Created: $TARGET")"
  else
    echo "Aborted."
    exit 0
  fi
fi

TARGET="$(cd "$TARGET" && pwd)"
echo

# ── --update mode ─────────────────────────────────────────────────────────────

if $UPDATE; then
  if ! is_memtoad_installed "$TARGET"; then
    echo "$(bold "Warning:") Memtoad does not appear to be installed in:"
    echo "  $TARGET"
    echo "(No .claude/skills/session-historian/SKILL.md found)"
    echo
    if ! confirm "Install fresh instead of updating?"; then
      echo "Aborted."
      exit 0
    fi
    UPDATE=false
  fi

  if $UPDATE; then
    echo "$(bold "Updating Memtoad in:") $TARGET"
    echo "  (skills and commands only — diary/ and CLAUDE.md untouched)"
    echo
    install_files "$TARGET" "update"
    echo
    handle_git_tracking "$TARGET"
    echo
    echo "$(green "$(bold "Done.")")"
    exit 0
  fi
fi

# ── Detect project type ────────────────────────────────────────────────────────

if $JUST_CREATED; then
  DETECTED="new"
else
  DETECTED="$(detect_project_type "$TARGET")"
fi

if [[ "$DETECTED" == "existing" ]]; then
  echo "$(bold "Detected:") existing project  $(dim "(found code, manifests, or git in $TARGET)")"
  echo "$(bold "Mode:")     existing-project init (steps 1–3 automated; Claude prompts written to MEMTOAD_INIT.md)"
else
  echo "$(bold "Detected:") new / empty project"
  echo "$(bold "Mode:")     new-project init (steps 1–3 automated; bootstrap prompt printed below)"
fi
echo

if [[ "$DETECTED" == "existing" ]]; then
  if ! confirm "Proceed as existing project?"; then
    if confirm "Switch to new-project mode instead?" "n"; then
      DETECTED="new"
    else
      echo "Aborted."; exit 0
    fi
  fi
else
  if ! confirm "Proceed as new project?"; then
    if confirm "Switch to existing-project mode instead?" "n"; then
      DETECTED="existing"
    else
      echo "Aborted."; exit 0
    fi
  fi
fi
echo

# ── Install ────────────────────────────────────────────────────────────────────

echo "$(bold "Installing Memtoad into:") $TARGET"
echo

install_files "$TARGET" "normal"
echo
update_claude_md "$TARGET"
echo
handle_git_tracking "$TARGET"
echo

# ── Post-install ───────────────────────────────────────────────────────────────

if [[ "$DETECTED" == "new" ]]; then
  cat << 'EOF'
════════════════════════════════════════════════════════════════
 Done. Steps 1–3 complete.
════════════════════════════════════════════════════════════════

Step 4: Open Claude Code in the project directory and paste
        this bootstrap prompt:

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

Step 5: Run /startup to verify Claude can synthesize the diary
        into a coherent briefing.

EOF
else
  DOCS="$(detect_docs "$TARGET")"
  [[ -z "$DOCS" ]] && DOCS="README.md, CLAUDE.md"

  echo "  Detecting docs ..."
  echo "  $(dim "Found: $DOCS")"
  echo

  write_init_file "$TARGET" "$DOCS"

  cat << EOF

════════════════════════════════════════════════════════════════
 Done. Steps 1–3 complete.
════════════════════════════════════════════════════════════════

Steps 4–8 are in: $(bold "$TARGET/MEMTOAD_INIT.md")

Open Claude Code in the project directory, open MEMTOAD_INIT.md,
and paste the prompts into Claude in order.

When finished, delete MEMTOAD_INIT.md.

EOF
fi
