#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash install-local-agent-config.sh [--dry-run] [--ccswitch] [--claude-only] [--init-memory <path>]

Configure local Codex and Claude entrypoints to use this cloned iOSAgentSkills repo:
  - ~/.codex/AGENTS.md -> <repo>/AGENTS.md
  - ~/.codex/skills -> <repo>/skills (默认)
  - ~/.codex/skills -> ~/.cc-switch/iOSAgentSkills/skills（当启用 --ccswitch 时）
  - ~/.codex/agents/*.toml -> <repo>/config/codex/templates/agents/*.toml
  - ~/.codex/bin/codex_verify -> <repo>/config/codex/templates/codex_verify.example.sh
  - ~/.codex/templates/codex_verify.example.sh -> <repo>/config/codex/templates/codex_verify.example.sh
  - ~/.codex/templates/ui-smoke.example.yml -> <repo>/config/codex/templates/ui-smoke.example.yml
  - ~/.copilot/skills -> <repo>/skills (默认)
  - ~/.copilot/skills -> ~/.cc-switch/iOSAgentSkills/skills（当启用 --ccswitch 时）
  - ~/.claude/CLAUDE.md -> @<repo>/AGENTS.md + CC 运行时编排指令
  - ~/.claude/skills -> <repo>/skills (默认)
  - ~/.claude/skills -> ~/.cc-switch/iOSAgentSkills/skills（当启用 --ccswitch 时）
  - ~/.claude/settings.json -> merge config/claude-code/settings.json into existing
  - ~/.claude/agents/*.md -> <repo>/config/claude-code/agents/*.md
  - ~/.cc-switch/skills -> <repo>/skills（固定不随 --ccswitch 切换）
  - ~/.codex/config.toml -> merge repo config/codex/codex.shared.toml into local shared defaults
  - ~/.codex/config.toml -> ensure model_instructions_file points to ~/.codex/AGENTS.md
  - ~/.codex/config.toml -> keep Codex memories enabled without overwriting local-only state

When --ccswitch is specified, the script synchronizes skills into:
  ~/.cc-switch/iOSAgentSkills/skills
and links ~/.codex/skills / ~/.claude/skills to that staging directory, avoiding CC Switch import actions
from deleting files in the current checked-out repository.
~/.copilot/skills will follow the same target as ~/.codex/skills.

When --claude-only is specified, all Codex-specific steps (~/.codex/*, ~/.copilot/*) are skipped.
Only Claude Code setup remains.

When --init-memory <path> is specified, the script prints a memory-seeding prompt to use as
the first message when starting Claude Code in the given project directory.

When conflicting local files or directories already exist, the script backs them up to:
  ~/.agent-skills-backups/iOSAgentSkills/<timestamp>/
EOF
}

DRY_RUN='0'
CCSWITCH_MODE='0'
CLAUDE_ONLY='0'
INIT_MEMORY_PATH=''

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
    --claude-only)
      CLAUDE_ONLY='1'
      shift
      ;;
    --init-memory)
      INIT_MEMORY_PATH="$2"
      shift 2
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
REPO_SYSTEM_SKILLS="$REPO_SKILLS/.system"
REPO_CODEX_SHARED_CONFIG="$REPO_ROOT/config/codex/codex.shared.toml"
REPO_CODEX_TEMPLATES="$REPO_ROOT/config/codex/templates"
REPO_CODEX_AGENT_TEMPLATES="$REPO_CODEX_TEMPLATES/agents"
REPO_CODEX_VERIFY_TEMPLATE="$REPO_CODEX_TEMPLATES/codex_verify.example.sh"
REPO_CODEX_UI_SMOKE_TEMPLATE="$REPO_CODEX_TEMPLATES/ui-smoke.example.yml"
CODEX_SYNC_SCRIPT="$REPO_ROOT/scripts/sync_codex_shared_config.py"
CODEX_AGENT_VALIDATE_SCRIPT="$REPO_ROOT/scripts/validate_codex_agent_templates.py"
REPO_CLAUDE_CONFIG="$REPO_ROOT/config/claude-code"
REPO_CLAUDE_SETTINGS="$REPO_CLAUDE_CONFIG/settings.json"
REPO_CLAUDE_AGENTS="$REPO_CLAUDE_CONFIG/agents"
REPO_CLAUDE_MEMORY_SEED="$REPO_CLAUDE_CONFIG/memory-seed.md"
CLAUDE_SYNC_SCRIPT="$REPO_ROOT/scripts/sync_claude_settings.py"

HOME_DIR="${HOME:?HOME is required}"
CODEX_DIR="$HOME_DIR/.codex"
CLAUDE_DIR="$HOME_DIR/.claude"
COPILOT_DIR="$HOME_DIR/.copilot"
CODEX_AGENTS="$CODEX_DIR/AGENTS.md"
CODEX_SKILLS="$CODEX_DIR/skills"
CODEX_SYSTEM_SKILLS="$CODEX_SKILLS/.system"
COPILOT_SKILLS="$COPILOT_DIR/skills"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
CLAUDE_SKILLS="$CLAUDE_DIR/skills"
CLAUDE_SETTINGS="$CLAUDE_DIR/settings.json"
CLAUDE_AGENTS_DIR="$CLAUDE_DIR/agents"
CODEX_CONFIG="$CODEX_DIR/config.toml"
CODEX_AGENTS_DIR="$CODEX_DIR/agents"
CODEX_BIN_DIR="$CODEX_DIR/bin"
CODEX_VERIFY_WRAPPER="$CODEX_BIN_DIR/codex_verify"
CODEX_TEMPLATES_DIR="$CODEX_DIR/templates"
CODEX_VERIFY_TEMPLATE="$CODEX_TEMPLATES_DIR/codex_verify.example.sh"
CODEX_UI_SMOKE_TEMPLATE="$CODEX_TEMPLATES_DIR/ui-smoke.example.yml"
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

backup_symlink_target_dir_if_needed() {
  local link_path="$1"
  local label="$2"

  [[ -L "$link_path" ]] || return 0

  local resolved_target
  resolved_target="$(resolve_physical_path "$link_path")"
  [[ -d "$resolved_target" ]] || return 0

  ensure_backup_dir

  local relative_path="${link_path#$HOME_DIR/}"
  if [[ "$relative_path" == "$link_path" ]]; then
    relative_path="$(basename "$link_path")"
  fi
  local backup_target="$BACKUP_DIR/${relative_path}.target_snapshot"

  if [[ "$DRY_RUN" == '1' ]]; then
    log "dry-run: backup symlink target directory for $label: $resolved_target -> $backup_target"
    return 0
  fi

  log "backup: symlink target directory for $label: $resolved_target -> $backup_target"
  mkdir -p "$(dirname "$backup_target")"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$resolved_target"/ "$backup_target"/
  else
    mkdir -p "$backup_target"
    cp -R "$resolved_target"/. "$backup_target"/
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
    backup_symlink_target_dir_if_needed "$link_path" "$label"
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

build_claude_md_content() {
  local import_line="@${REPO_AGENTS}"
  local repo_claude_md="$REPO_ROOT/CLAUDE.md"
  local orchestration_section

  if [[ -f "$repo_claude_md" ]]; then
    orchestration_section="$(tail -n +2 "$repo_claude_md")"
  else
    orchestration_section=''
  fi

  if [[ -n "$orchestration_section" ]]; then
    printf '%s\n%s\n' "$import_line" "$orchestration_section"
  else
    printf '%s\n' "$import_line"
  fi
}

ensure_claude_settings() {
  local template="$REPO_CLAUDE_SETTINGS"
  local action='created'

  if [[ ! -f "$template" ]]; then
    log "skip: config/claude-code/settings.json template not found"
    return 0
  fi

  ensure_directory "$CLAUDE_DIR"

  if [[ -f "$CLAUDE_SETTINGS" && ! -L "$CLAUDE_SETTINGS" ]]; then
    action='updated'
  fi

  log "$action: ~/.claude/settings.json (merged from config/claude-code/settings.json)"
  if [[ "$DRY_RUN" == '0' ]]; then
    python3 "$CLAUDE_SYNC_SCRIPT" --template "$template" --target "$CLAUDE_SETTINGS"
  fi
  record_change "$action"
}

ensure_claude_agents() {
  ensure_directory "$CLAUDE_AGENTS_DIR"

  local source target base_name
  for source in "$REPO_CLAUDE_AGENTS"/*.md; do
    [[ -f "$source" ]] || continue
    base_name="$(basename "$source")"
    target="$CLAUDE_AGENTS_DIR/$base_name"
    ensure_file_copied "$target" "$source" "~/.claude/agents/$base_name"
  done
}

seed_claude_memory() {
  local project_path="$1"

  if [[ ! -f "$REPO_CLAUDE_MEMORY_SEED" ]]; then
    log "skip: config/claude-code/memory-seed.md not found"
    return 0
  fi

  echo ''
  log "=== Claude Code Memory Seed ==="
  log "To prime project memory, start Claude Code in: $project_path"
  log "and use the following as your first prompt:"
  log "---"
  cat "$REPO_CLAUDE_MEMORY_SEED"
  log "---"
  log "After this session, Claude Code will remember the project context automatically."
}

ensure_file_copied() {
  local target_path="$1"
  local source_path="$2"
  local label="$3"
  local action='created'

  ensure_directory "$(dirname "$target_path")"

  if [[ -f "$target_path" && ! -L "$target_path" ]]; then
    if cmp -s "$source_path" "$target_path"; then
      log "unchanged: $label"
      record_change unchanged
      return 0
    fi
    backup_existing_path "$target_path"
    action='updated'
  elif [[ -e "$target_path" || -L "$target_path" ]]; then
    backup_existing_path "$target_path"
    action='updated'
  fi

  log "$action: $label"
  if [[ "$DRY_RUN" == '0' ]]; then
    cp "$source_path" "$target_path"
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

sync_system_skills_from_codex() {
  if [[ ! -d "$CODEX_SYSTEM_SKILLS" ]]; then
    log "skip: ~/.codex/skills/.system not found"
    return 0
  fi

  local source_resolved target_resolved
  source_resolved="$(resolve_physical_path "$CODEX_SYSTEM_SKILLS")"
  target_resolved="$(resolve_physical_path "$REPO_SYSTEM_SKILLS")"

  if [[ "$source_resolved" == "$target_resolved" ]]; then
    log "unchanged: repo skills/.system already points to ~/.codex/skills/.system source"
    record_change unchanged
    return 0
  fi

  if [[ "$DRY_RUN" == '1' ]]; then
    log "dry-run: sync ~/.codex/skills/.system -> $REPO_SYSTEM_SKILLS"
    return 0
  fi

  log "sync: copy ~/.codex/skills/.system -> $REPO_SYSTEM_SKILLS"
  ensure_directory "$REPO_SYSTEM_SKILLS"

  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "$CODEX_SYSTEM_SKILLS/" "$REPO_SYSTEM_SKILLS/"
  else
    rm -rf "$REPO_SYSTEM_SKILLS"/*
    cp -R "$CODEX_SYSTEM_SKILLS"/. "$REPO_SYSTEM_SKILLS"/
  fi

  UPDATED_COUNT=$((UPDATED_COUNT + 1))
}

sync_codex_agent_templates() {
  ensure_directory "$CODEX_AGENTS_DIR"

  local source target base_name
  for source in "$REPO_CODEX_AGENT_TEMPLATES"/*.toml "$REPO_CODEX_AGENT_TEMPLATES"/README.md; do
    [[ -f "$source" ]] || continue
    base_name="$(basename "$source")"
    target="$CODEX_AGENTS_DIR/$base_name"
    ensure_file_copied "$target" "$source" "~/.codex/agents/$base_name"
  done
}

sync_codex_ui_smoke_template() {
  [[ -f "$REPO_CODEX_UI_SMOKE_TEMPLATE" ]] || return 0
  ensure_directory "$CODEX_TEMPLATES_DIR"
  ensure_file_copied "$CODEX_UI_SMOKE_TEMPLATE" "$REPO_CODEX_UI_SMOKE_TEMPLATE" "~/.codex/templates/ui-smoke.example.yml"
}

sync_codex_verify_template() {
  [[ -f "$REPO_CODEX_VERIFY_TEMPLATE" ]] || return 0
  ensure_directory "$CODEX_TEMPLATES_DIR"
  ensure_file_copied "$CODEX_VERIFY_TEMPLATE" "$REPO_CODEX_VERIFY_TEMPLATE" "~/.codex/templates/codex_verify.example.sh"
  if [[ "$DRY_RUN" == '0' ]]; then
    chmod +x "$CODEX_VERIFY_TEMPLATE"
  fi
}

sync_codex_verify_wrapper() {
  [[ -f "$REPO_CODEX_VERIFY_TEMPLATE" ]] || return 0
  ensure_directory "$CODEX_BIN_DIR"
  ensure_file_copied "$CODEX_VERIFY_WRAPPER" "$REPO_CODEX_VERIFY_TEMPLATE" "~/.codex/bin/codex_verify"
  if [[ "$DRY_RUN" == '0' ]]; then
    chmod +x "$CODEX_VERIFY_WRAPPER"
  fi
}

if [[ ! -f "$REPO_AGENTS" ]]; then
  echo "Error: missing AGENTS.md in repo root: $REPO_AGENTS" >&2
  exit 1
fi

if [[ ! -d "$REPO_SKILLS" ]]; then
  echo "Error: missing skills directory in repo root: $REPO_SKILLS" >&2
  exit 1
fi

if [[ "$CLAUDE_ONLY" == '0' ]]; then
  if [[ ! -f "$REPO_CODEX_SHARED_CONFIG" ]]; then
    echo "Error: missing shared Codex config: $REPO_CODEX_SHARED_CONFIG" >&2
    exit 1
  fi

  if [[ ! -d "$REPO_CODEX_AGENT_TEMPLATES" ]]; then
    echo "Error: missing Codex agent templates directory: $REPO_CODEX_AGENT_TEMPLATES" >&2
    exit 1
  fi

  if [[ ! -f "$CODEX_SYNC_SCRIPT" ]]; then
    echo "Error: missing Codex config sync script: $CODEX_SYNC_SCRIPT" >&2
    exit 1
  fi

  if [[ ! -f "$CODEX_AGENT_VALIDATE_SCRIPT" ]]; then
    echo "Error: missing Codex agent validation script: $CODEX_AGENT_VALIDATE_SCRIPT" >&2
    exit 1
  fi
fi

CLAUDE_MD_CONTENT="$(build_claude_md_content)"
if [[ "$CCSWITCH_MODE" == '1' ]]; then
  TARGET_SKILLS="$CCSWITCH_SKILLS"
fi

verify_codex_config() {
  python3 - "$CODEX_CONFIG" "$REPO_CODEX_SHARED_CONFIG" "$CODEX_AGENTS" <<'PY'
from pathlib import Path
import sys
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # Python 3.10 + tomli
    except ModuleNotFoundError:
        import pip._vendor.tomli as tomllib  # Python 3.10 fallback

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

verify_codex_agent_templates() {
  python3 "$CODEX_AGENT_VALIDATE_SCRIPT" "$REPO_CODEX_AGENT_TEMPLATES" >/dev/null || fail "repo Codex agent templates do not match the supported flat Codex custom-agent schema"

  local source target base_name
  for source in "$REPO_CODEX_AGENT_TEMPLATES"/*.toml "$REPO_CODEX_AGENT_TEMPLATES"/README.md; do
    [[ -f "$source" ]] || continue
    base_name="$(basename "$source")"
    target="$CODEX_AGENTS_DIR/$base_name"
    [[ -f "$target" && ! -L "$target" ]] || fail "~/.codex/agents/$base_name is missing or not a regular file"
    cmp -s "$source" "$target" || fail "~/.codex/agents/$base_name does not match repo template"
  done

  python3 "$CODEX_AGENT_VALIDATE_SCRIPT" "$CODEX_AGENTS_DIR" >/dev/null || fail "~/.codex/agents contains malformed Codex custom agent files"

  if [[ -f "$REPO_CODEX_VERIFY_TEMPLATE" ]]; then
    [[ -f "$CODEX_VERIFY_TEMPLATE" && ! -L "$CODEX_VERIFY_TEMPLATE" ]] || fail "~/.codex/templates/codex_verify.example.sh is missing or not a regular file"
    cmp -s "$REPO_CODEX_VERIFY_TEMPLATE" "$CODEX_VERIFY_TEMPLATE" || fail "~/.codex/templates/codex_verify.example.sh does not match repo template"
    [[ -x "$CODEX_VERIFY_TEMPLATE" ]] || fail "~/.codex/templates/codex_verify.example.sh is not executable"
    [[ -f "$CODEX_VERIFY_WRAPPER" && ! -L "$CODEX_VERIFY_WRAPPER" ]] || fail "~/.codex/bin/codex_verify is missing or not a regular file"
    cmp -s "$REPO_CODEX_VERIFY_TEMPLATE" "$CODEX_VERIFY_WRAPPER" || fail "~/.codex/bin/codex_verify does not match repo template"
    [[ -x "$CODEX_VERIFY_WRAPPER" ]] || fail "~/.codex/bin/codex_verify is not executable"
  fi

  if [[ -f "$REPO_CODEX_UI_SMOKE_TEMPLATE" ]]; then
    [[ -f "$CODEX_UI_SMOKE_TEMPLATE" && ! -L "$CODEX_UI_SMOKE_TEMPLATE" ]] || fail "~/.codex/templates/ui-smoke.example.yml is missing or not a regular file"
    cmp -s "$REPO_CODEX_UI_SMOKE_TEMPLATE" "$CODEX_UI_SMOKE_TEMPLATE" || fail "~/.codex/templates/ui-smoke.example.yml does not match repo template"
  fi
}

verify_installation() {
  if [[ "$CLAUDE_ONLY" == '0' ]]; then
    [[ -L "$CODEX_AGENTS" ]] || fail "~/.codex/AGENTS.md is not a symlink"
    [[ "$(resolve_physical_path "$CODEX_AGENTS")" == "$(resolve_physical_path "$REPO_AGENTS")" ]] || fail "~/.codex/AGENTS.md does not point to this cloned repo"

    [[ -L "$CODEX_SKILLS" ]] || fail "~/.codex/skills is not a symlink"
    [[ "$(resolve_physical_path "$CODEX_SKILLS")" == "$(resolve_physical_path "$TARGET_SKILLS")" ]] || fail "~/.codex/skills does not point to expected skills path"

    [[ -L "$COPILOT_SKILLS" ]] || fail "~/.copilot/skills is not a symlink"
    [[ "$(resolve_physical_path "$COPILOT_SKILLS")" == "$(resolve_physical_path "$TARGET_SKILLS")" ]] || fail "~/.copilot/skills does not point to expected skills path"

    [[ -f "$CODEX_CONFIG" && ! -L "$CODEX_CONFIG" ]] || fail "~/.codex/config.toml is missing or not a regular file"
    verify_codex_config || fail "~/.codex/config.toml does not match repo-managed Codex shared config"
    verify_codex_agent_templates
  fi

  [[ -L "$CLAUDE_SKILLS" ]] || fail "~/.claude/skills is not a symlink"
  [[ "$(resolve_physical_path "$CLAUDE_SKILLS")" == "$(resolve_physical_path "$TARGET_SKILLS")" ]] || fail "~/.claude/skills does not point to expected skills path"

  if [[ "$CCSWITCH_MODE" == '1' ]]; then
    [[ "$(resolve_physical_path "$TARGET_SKILLS")" != "$(resolve_physical_path "$REPO_SKILLS")" ]] || fail "--ccswitch mode should use staging cache, not repo/skills"
  fi

  [[ -f "$CLAUDE_MD" && ! -L "$CLAUDE_MD" ]] || fail "~/.claude/CLAUDE.md is missing or not a regular file"
  [[ "$(cat "$CLAUDE_MD")" == "$CLAUDE_MD_CONTENT" ]] || fail "~/.claude/CLAUDE.md does not match expected content"

  [[ -L "$CCSWITCH_PUBLIC_SKILLS" ]] || fail "~/.cc-switch/skills is not a symlink"
  [[ "$(resolve_physical_path "$CCSWITCH_PUBLIC_SKILLS")" == "$(resolve_physical_path "$REPO_SKILLS")" ]] || fail "~/.cc-switch/skills does not point to repo skills"

  [[ -f "$CLAUDE_SETTINGS" && ! -L "$CLAUDE_SETTINGS" ]] || fail "~/.claude/settings.json is missing or not a regular file"
}

if [[ "$CLAUDE_ONLY" == '0' ]]; then
  ensure_symlink "$CODEX_AGENTS" "$REPO_AGENTS" "~/.codex/AGENTS.md"
  ensure_symlink "$CODEX_SKILLS" "$TARGET_SKILLS" "~/.codex/skills"
  ensure_symlink "$COPILOT_SKILLS" "$TARGET_SKILLS" "~/.copilot/skills"
  ensure_codex_config
  sync_codex_agent_templates
  sync_codex_verify_wrapper
  sync_codex_verify_template
  sync_codex_ui_smoke_template
else
  log "skip: Codex setup (--claude-only)"
fi

sync_system_skills_from_codex
sync_skills_to_ccswitch_cache
ensure_text_file "$CLAUDE_MD" "$CLAUDE_MD_CONTENT" "~/.claude/CLAUDE.md"
ensure_symlink "$CLAUDE_SKILLS" "$TARGET_SKILLS" "~/.claude/skills"
ensure_symlink "$CCSWITCH_PUBLIC_SKILLS" "$REPO_SKILLS" "~/.cc-switch/skills"
ensure_claude_settings
ensure_claude_agents

if [[ -n "$INIT_MEMORY_PATH" ]]; then
  seed_claude_memory "$INIT_MEMORY_PATH"
fi

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
