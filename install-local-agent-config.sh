#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash install-local-agent-config.sh [--dry-run] [--ccswitch]

Configure local Codex and Claude entrypoints to use this cloned iOSAgentSkills repo:
  - ~/.codex/AGENTS.md -> <repo>/AGENTS.md
  - ~/.codex/skills -> <repo>/skills (默认)
  - ~/.codex/skills -> ~/.cc-switch/iOSAgentSkills/skills（当启用 --ccswitch 时）
  - ~/.copilot/skills -> <repo>/skills (默认)
  - ~/.copilot/skills -> ~/.cc-switch/iOSAgentSkills/skills（当启用 --ccswitch 时）
  - ~/.claude/CLAUDE.md -> @<repo>/AGENTS.md
  - ~/.claude/skills -> <repo>/skills (默认)
  - ~/.claude/skills -> ~/.cc-switch/iOSAgentSkills/skills（当启用 --ccswitch 时）
  - ~/.cc-switch/skills -> <repo>/skills（固定不随 --ccswitch 切换）
  - ~/.codex/config.toml -> merge repo config/codex.shared.toml into local shared defaults
  - ~/.codex/config.toml -> ensure model_instructions_file points to ~/.codex/AGENTS.md
  - ~/.codex/config.toml -> keep Codex memories enabled without overwriting local-only state

When --ccswitch is specified, the script synchronizes skills into:
  ~/.cc-switch/iOSAgentSkills/skills
and links ~/.codex/skills / ~/.claude/skills to that staging directory, avoiding CC Switch import actions
from deleting files in the current checked-out repository.
~/.copilot/skills will follow the same target as ~/.codex/skills.

When conflicting local files or directories already exist, the script backs them up to:
  ~/.agent-skills-backups/iOSAgentSkills/<timestamp>/
EOF
}

DRY_RUN='0'
CCSWITCH_MODE='0'

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN='1'
      shift
      ;;
    --ccswitch)
      CCSWITCH_MODE='1'
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

REPO_ROOT="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_AGENTS="$REPO_ROOT/AGENTS.md"
REPO_SKILLS="$REPO_ROOT/skills"
REPO_CODEX_SHARED_CONFIG="$REPO_ROOT/config/codex.shared.toml"
CODEX_SYNC_SCRIPT="$REPO_ROOT/scripts/sync_codex_shared_config.py"

HOME_DIR="${HOME:?HOME is required}"
CODEX_DIR="$HOME_DIR/.codex"
CLAUDE_DIR="$HOME_DIR/.claude"
COPILOT_DIR="$HOME_DIR/.copilot"
CODEX_AGENTS="$CODEX_DIR/AGENTS.md"
CODEX_SKILLS="$CODEX_DIR/skills"
COPILOT_SKILLS="$COPILOT_DIR/skills"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
CLAUDE_SKILLS="$CLAUDE_DIR/skills"
CODEX_CONFIG="$CODEX_DIR/config.toml"
CCSWITCH_PUBLIC_SKILLS="$HOME_DIR/.cc-switch/skills"
CCSWITCH_CACHE_ROOT="$HOME_DIR/.cc-switch/iOSAgentSkills"
CCSWITCH_SKILLS="$CCSWITCH_CACHE_ROOT/skills"
TARGET_SKILLS="$REPO_SKILLS"

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
  local existing_config_path=''

  if [[ -f "$config_path" && ! -L "$config_path" ]]; then
    existing_config_path="$config_path"
  fi

  python3 "$CODEX_SYNC_SCRIPT" \
    --shared-config "$REPO_CODEX_SHARED_CONFIG" \
    --existing-config "$existing_config_path" \
    --agents-path "$target_agents_path"
}

ensure_codex_config() {
  local action='created'
  local candidate_file

  ensure_directory "$CODEX_DIR"

  if [[ ! -f "$CODEX_CONFIG" && ( -e "$CODEX_CONFIG" || -L "$CODEX_CONFIG" ) ]]; then
    backup_existing_path "$CODEX_CONFIG"
  fi

  candidate_file="$(mktemp)"
  build_config_candidate "$CODEX_CONFIG" "$CODEX_AGENTS" > "$candidate_file"

  if [[ -f "$CODEX_CONFIG" && ! -L "$CODEX_CONFIG" ]] && cmp -s "$CODEX_CONFIG" "$candidate_file"; then
    rm -f "$candidate_file"
    log "unchanged: ~/.codex/config.toml"
    record_change unchanged
    return 0
  fi

  if [[ -f "$CODEX_CONFIG" && ! -L "$CODEX_CONFIG" ]]; then
    backup_existing_path "$CODEX_CONFIG"
    action='updated'
  fi

  log "$action: ~/.codex/config.toml (shared defaults + local preservation)"
  if [[ "$DRY_RUN" == '0' ]]; then
    cat "$candidate_file" > "$CODEX_CONFIG"
  fi
  rm -f "$candidate_file"
  record_change "$action"
}

sync_skills_to_ccswitch_cache() {
  if [[ "$CCSWITCH_MODE" == '0' ]]; then
    return 0
  fi

  if [[ "$DRY_RUN" == '1' ]]; then
    log "dry-run: sync skills to staging cache: $REPO_SKILLS -> $CCSWITCH_SKILLS"
    return 0
  fi

  log "sync: copy skills into staging cache: $REPO_SKILLS -> $CCSWITCH_SKILLS"
  ensure_directory "$CCSWITCH_CACHE_ROOT"
  ensure_directory "$CCSWITCH_SKILLS"

  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$REPO_SKILLS/" "$CCSWITCH_SKILLS/"
  else
    rm -rf "$CCSWITCH_SKILLS"/*
    cp -R "$REPO_SKILLS"/. "$CCSWITCH_SKILLS"/
  fi

  TARGET_SKILLS="$CCSWITCH_SKILLS"
}

if [[ ! -f "$REPO_AGENTS" ]]; then
  echo "Error: missing AGENTS.md in repo root: $REPO_AGENTS" >&2
  exit 1
fi

if [[ ! -d "$REPO_SKILLS" ]]; then
  echo "Error: missing skills directory in repo root: $REPO_SKILLS" >&2
  exit 1
fi

if [[ ! -f "$REPO_CODEX_SHARED_CONFIG" ]]; then
  echo "Error: missing shared Codex config: $REPO_CODEX_SHARED_CONFIG" >&2
  exit 1
fi

if [[ ! -f "$CODEX_SYNC_SCRIPT" ]]; then
  echo "Error: missing Codex config sync script: $CODEX_SYNC_SCRIPT" >&2
  exit 1
fi

CLAUDE_IMPORT_LINE="@${REPO_AGENTS}"
if [[ "$CCSWITCH_MODE" == '1' ]]; then
  TARGET_SKILLS="$CCSWITCH_SKILLS"
fi

verify_codex_config() {
  python3 - "$CODEX_CONFIG" "$REPO_CODEX_SHARED_CONFIG" "$CODEX_AGENTS" <<'PY'
from pathlib import Path
import sys
import tomllib

config_path = Path(sys.argv[1])
shared_path = Path(sys.argv[2])
agents_path = sys.argv[3]

config = tomllib.loads(config_path.read_text())
shared = tomllib.loads(shared_path.read_text())

errors = []

if config.get("model_instructions_file") != agents_path:
    errors.append("model_instructions_file does not point to ~/.codex/AGENTS.md")

def lookup(mapping, path):
    value = mapping
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value

def compare_shared(shared_value, actual_value, path):
    if isinstance(shared_value, dict):
        if not isinstance(actual_value, dict):
            errors.append("missing table: " + ".".join(path))
            return

        if path and path[0] in {"mcp_servers", "plugins"} and len(path) == 2:
            if actual_value != shared_value:
                errors.append("managed subtree mismatch: " + ".".join(path))
            return

        for key, child in shared_value.items():
            compare_shared(child, actual_value.get(key), path + [key])
        return

    if actual_value != shared_value:
        errors.append("managed value mismatch: " + ".".join(path))

for key, value in shared.items():
    compare_shared(value, config.get(key), [key])

if errors:
    for message in errors:
        print(message, file=sys.stderr)
    raise SystemExit(1)
PY
}

verify_installation() {
  [[ -L "$CODEX_AGENTS" ]] || fail "~/.codex/AGENTS.md is not a symlink"
  [[ "$(resolve_physical_path "$CODEX_AGENTS")" == "$(resolve_physical_path "$REPO_AGENTS")" ]] || fail "~/.codex/AGENTS.md does not point to this cloned repo"

  [[ -L "$CODEX_SKILLS" ]] || fail "~/.codex/skills is not a symlink"
  [[ "$(resolve_physical_path "$CODEX_SKILLS")" == "$(resolve_physical_path "$TARGET_SKILLS")" ]] || fail "~/.codex/skills does not point to expected skills path"

  [[ -L "$CLAUDE_SKILLS" ]] || fail "~/.claude/skills is not a symlink"
  [[ "$(resolve_physical_path "$CLAUDE_SKILLS")" == "$(resolve_physical_path "$TARGET_SKILLS")" ]] || fail "~/.claude/skills does not point to expected skills path"

  [[ -L "$COPILOT_SKILLS" ]] || fail "~/.copilot/skills is not a symlink"
  [[ "$(resolve_physical_path "$COPILOT_SKILLS")" == "$(resolve_physical_path "$TARGET_SKILLS")" ]] || fail "~/.copilot/skills does not point to expected skills path"

  if [[ "$CCSWITCH_MODE" == '1' ]]; then
    [[ "$(resolve_physical_path "$TARGET_SKILLS")" != "$(resolve_physical_path "$REPO_SKILLS")" ]] || fail "--ccswitch mode should use staging cache, not repo/skills"
  fi

  [[ -f "$CLAUDE_MD" && ! -L "$CLAUDE_MD" ]] || fail "~/.claude/CLAUDE.md is missing or not a regular file"
  [[ "$(cat "$CLAUDE_MD")" == "$CLAUDE_IMPORT_LINE" ]] || fail "~/.claude/CLAUDE.md does not import this cloned repo"

  [[ -L "$CCSWITCH_PUBLIC_SKILLS" ]] || fail "~/.cc-switch/skills is not a symlink"
  [[ "$(resolve_physical_path "$CCSWITCH_PUBLIC_SKILLS")" == "$(resolve_physical_path "$REPO_SKILLS")" ]] || fail "~/.cc-switch/skills does not point to repo skills"

  [[ -f "$CODEX_CONFIG" && ! -L "$CODEX_CONFIG" ]] || fail "~/.codex/config.toml is missing or not a regular file"
  verify_codex_config || fail "~/.codex/config.toml does not match repo-managed Codex shared config"
}

ensure_symlink "$CODEX_AGENTS" "$REPO_AGENTS" "~/.codex/AGENTS.md"
sync_skills_to_ccswitch_cache
ensure_symlink "$CODEX_SKILLS" "$TARGET_SKILLS" "~/.codex/skills"
ensure_symlink "$COPILOT_SKILLS" "$TARGET_SKILLS" "~/.copilot/skills"
ensure_text_file "$CLAUDE_MD" "$CLAUDE_IMPORT_LINE" "~/.claude/CLAUDE.md"
ensure_symlink "$CLAUDE_SKILLS" "$TARGET_SKILLS" "~/.claude/skills"
ensure_symlink "$CCSWITCH_PUBLIC_SKILLS" "$REPO_SKILLS" "~/.cc-switch/skills"
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
