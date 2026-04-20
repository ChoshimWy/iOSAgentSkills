#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/install-local-agent-config.sh [--dry-run]

Configure local Codex and Claude entrypoints to use this cloned iOSAgentSkills repo:
  - ~/.codex/AGENTS.md -> <repo>/AGENTS.md
  - ~/.codex/skills -> <repo>/skills
  - ~/.claude/CLAUDE.md -> @<repo>/AGENTS.md
  - ~/.claude/skills -> <repo>/skills
  - ~/.codex/config.toml -> ensure model_instructions_file points to ~/.codex/AGENTS.md

When conflicting local files or directories already exist, the script backs them up to:
  ~/.agent-skills-backups/iOSAgentSkills/<timestamp>/
EOF
}

DRY_RUN='0'

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN='1'
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown option $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

REPO_ROOT="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
REPO_AGENTS="$REPO_ROOT/AGENTS.md"
REPO_SKILLS="$REPO_ROOT/skills"

HOME_DIR="${HOME:?HOME is required}"
CODEX_DIR="$HOME_DIR/.codex"
CLAUDE_DIR="$HOME_DIR/.claude"
CODEX_AGENTS="$CODEX_DIR/AGENTS.md"
CODEX_SKILLS="$CODEX_DIR/skills"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
CLAUDE_SKILLS="$CLAUDE_DIR/skills"
CODEX_CONFIG="$CODEX_DIR/config.toml"

BACKUP_BASE="$HOME_DIR/.agent-skills-backups/iOSAgentSkills"
BACKUP_DIR=""

CREATED_COUNT=0
UPDATED_COUNT=0
UNCHANGED_COUNT=0
BACKUP_COUNT=0

log() {
  printf '%s\n' "$*"
}

resolve_physical_path() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).resolve())
PY
}

fail() {
  echo "Verification failed: $*" >&2
  exit 1
}

ensure_backup_dir() {
  if [[ -n "$BACKUP_DIR" ]]; then
    return 0
  fi

  local timestamp
  timestamp="$(date +%Y%m%d-%H%M%S)"
  BACKUP_DIR="$BACKUP_BASE/$timestamp"
  if [[ "$DRY_RUN" == '0' ]]; then
    mkdir -p "$BACKUP_DIR"
  fi
}

backup_existing_path() {
  local path="$1"
  [[ -e "$path" || -L "$path" ]] || return 0

  ensure_backup_dir

  local relative_path="${path#$HOME_DIR/}"
  if [[ "$relative_path" == "$path" ]]; then
    relative_path="$(basename "$path")"
  fi
  local backup_target="$BACKUP_DIR/$relative_path"

  log "backup: $path -> $backup_target"
  if [[ "$DRY_RUN" == '0' ]]; then
    mkdir -p "$(dirname "$backup_target")"
    mv "$path" "$backup_target"
  fi
  BACKUP_COUNT=$((BACKUP_COUNT + 1))
}

ensure_directory() {
  local dir_path="$1"

  if [[ -d "$dir_path" ]]; then
    return 0
  fi

  if [[ -e "$dir_path" || -L "$dir_path" ]]; then
    backup_existing_path "$dir_path"
  fi

  log "mkdir: $dir_path"
  if [[ "$DRY_RUN" == '0' ]]; then
    mkdir -p "$dir_path"
  fi
}

record_change() {
  local action="$1"
  case "$action" in
    created)
      CREATED_COUNT=$((CREATED_COUNT + 1))
      ;;
    updated)
      UPDATED_COUNT=$((UPDATED_COUNT + 1))
      ;;
    unchanged)
      UNCHANGED_COUNT=$((UNCHANGED_COUNT + 1))
      ;;
  esac
}

is_expected_symlink() {
  local path="$1"
  local target="$2"

  [[ -L "$path" ]] || return 1
  [[ "$(resolve_physical_path "$path")" == "$(resolve_physical_path "$target")" ]]
}

ensure_symlink() {
  local link_path="$1"
  local target_path="$2"
  local label="$3"
  local action='created'

  ensure_directory "$(dirname "$link_path")"

  if is_expected_symlink "$link_path" "$target_path"; then
    log "unchanged: $label"
    record_change unchanged
    return 0
  fi

  if [[ -e "$link_path" || -L "$link_path" ]]; then
    backup_existing_path "$link_path"
    action='updated'
  fi

  log "$action: $label -> $target_path"
  if [[ "$DRY_RUN" == '0' ]]; then
    ln -s "$target_path" "$link_path"
  fi
  record_change "$action"
}

ensure_text_file() {
  local file_path="$1"
  local expected_content="$2"
  local label="$3"
  local action='created'

  ensure_directory "$(dirname "$file_path")"

  if [[ -f "$file_path" && ! -L "$file_path" ]]; then
    if [[ "$(cat "$file_path")" == "$expected_content" ]]; then
      log "unchanged: $label"
      record_change unchanged
      return 0
    fi
    backup_existing_path "$file_path"
    action='updated'
  elif [[ -e "$file_path" || -L "$file_path" ]]; then
    backup_existing_path "$file_path"
    action='updated'
  fi

  log "$action: $label"
  if [[ "$DRY_RUN" == '0' ]]; then
    printf '%s\n' "$expected_content" > "$file_path"
  fi
  record_change "$action"
}

build_config_candidate() {
  local config_path="$1"
  local target_agents_path="$2"
  local input_exists="$3"

  python3 - "$config_path" "$target_agents_path" "$input_exists" <<'PY'
from pathlib import Path
import sys

config_path = Path(sys.argv[1])
agents_path = sys.argv[2]
input_exists = sys.argv[3] == "1"
target_line = f'model_instructions_file = "{agents_path}"'

text = config_path.read_text() if input_exists else ""
if not text:
    sys.stdout.write(target_line + "\n")
    raise SystemExit

lines = text.splitlines(keepends=True)
new_lines = []
found = False

for line in lines:
    stripped = line.lstrip()
    if stripped.startswith("model_instructions_file") and "=" in stripped:
        if not found:
            new_lines.append(target_line + "\n")
            found = True
        continue
    new_lines.append(line)

if not found:
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] = new_lines[-1] + "\n"
    new_lines.append(target_line + "\n")

sys.stdout.write("".join(new_lines))
PY
}

ensure_codex_config() {
  local action='created'
  local has_regular_file='0'
  local candidate_file

  ensure_directory "$CODEX_DIR"

  if [[ -f "$CODEX_CONFIG" && ! -L "$CODEX_CONFIG" ]]; then
    has_regular_file='1'
  elif [[ -e "$CODEX_CONFIG" || -L "$CODEX_CONFIG" ]]; then
    backup_existing_path "$CODEX_CONFIG"
  fi

  candidate_file="$(mktemp)"
  build_config_candidate "$CODEX_CONFIG" "$CODEX_AGENTS" "$has_regular_file" > "$candidate_file"

  if [[ "$has_regular_file" == '1' ]] && cmp -s "$CODEX_CONFIG" "$candidate_file"; then
    rm -f "$candidate_file"
    log "unchanged: ~/.codex/config.toml"
    record_change unchanged
    return 0
  fi

  if [[ "$has_regular_file" == '1' ]]; then
    backup_existing_path "$CODEX_CONFIG"
    action='updated'
  fi

  log "$action: ~/.codex/config.toml (model_instructions_file)"
  if [[ "$DRY_RUN" == '0' ]]; then
    cat "$candidate_file" > "$CODEX_CONFIG"
  fi
  rm -f "$candidate_file"
  record_change "$action"
}

if [[ ! -f "$REPO_AGENTS" ]]; then
  echo "Error: missing AGENTS.md in repo root: $REPO_AGENTS" >&2
  exit 1
fi

if [[ ! -d "$REPO_SKILLS" ]]; then
  echo "Error: missing skills directory in repo root: $REPO_SKILLS" >&2
  exit 1
fi

CLAUDE_IMPORT_LINE="@${REPO_AGENTS}"

verify_installation() {
  [[ -L "$CODEX_AGENTS" ]] || fail "~/.codex/AGENTS.md is not a symlink"
  [[ "$(resolve_physical_path "$CODEX_AGENTS")" == "$(resolve_physical_path "$REPO_AGENTS")" ]] || fail "~/.codex/AGENTS.md does not point to this cloned repo"

  [[ -L "$CODEX_SKILLS" ]] || fail "~/.codex/skills is not a symlink"
  [[ "$(resolve_physical_path "$CODEX_SKILLS")" == "$(resolve_physical_path "$REPO_SKILLS")" ]] || fail "~/.codex/skills does not point to this cloned repo"

  [[ -L "$CLAUDE_SKILLS" ]] || fail "~/.claude/skills is not a symlink"
  [[ "$(resolve_physical_path "$CLAUDE_SKILLS")" == "$(resolve_physical_path "$REPO_SKILLS")" ]] || fail "~/.claude/skills does not point to this cloned repo"

  [[ -f "$CLAUDE_MD" && ! -L "$CLAUDE_MD" ]] || fail "~/.claude/CLAUDE.md is missing or not a regular file"
  [[ "$(cat "$CLAUDE_MD")" == "$CLAUDE_IMPORT_LINE" ]] || fail "~/.claude/CLAUDE.md does not import this cloned repo"

  [[ -f "$CODEX_CONFIG" && ! -L "$CODEX_CONFIG" ]] || fail "~/.codex/config.toml is missing or not a regular file"
  grep -Fq "model_instructions_file = \"$CODEX_AGENTS\"" "$CODEX_CONFIG" || fail "~/.codex/config.toml does not point model_instructions_file to ~/.codex/AGENTS.md"
}

ensure_symlink "$CODEX_AGENTS" "$REPO_AGENTS" "~/.codex/AGENTS.md"
ensure_symlink "$CODEX_SKILLS" "$REPO_SKILLS" "~/.codex/skills"
ensure_text_file "$CLAUDE_MD" "$CLAUDE_IMPORT_LINE" "~/.claude/CLAUDE.md"
ensure_symlink "$CLAUDE_SKILLS" "$REPO_SKILLS" "~/.claude/skills"
ensure_codex_config

printf '\nSummary:\n'
printf '  created: %d\n' "$CREATED_COUNT"
printf '  updated: %d\n' "$UPDATED_COUNT"
printf '  backed up: %d\n' "$BACKUP_COUNT"
printf '  unchanged: %d\n' "$UNCHANGED_COUNT"
if [[ -n "$BACKUP_DIR" ]]; then
  printf '  backup dir: %s\n' "$BACKUP_DIR"
fi
if [[ "$DRY_RUN" == '1' ]]; then
  printf '  mode: dry-run\n'
  printf 'Verification: skipped (dry-run)\n'
else
  verify_installation
  printf 'Verification: OK\n'
fi
