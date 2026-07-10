#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash install-local-agent-config.sh [--dry-run] [--refresh-profiles] [--ccswitch] [--claude-only] [--init-project <path>] [--init-memory <path>]

Configure local Codex and Claude entrypoints to use this cloned iOSAgentSkills repo:
  - ~/.codex/AGENTS.md -> <repo>/AGENTS.md
  - ~/.codex/skills -> <repo>/skills (默认)
  - ~/.codex/skills -> ~/.cc-switch/iOSAgentSkills/skills（当启用 --ccswitch 时）
  - ~/.codex/agents/*.toml -> <repo>/config/codex/templates/agents/*.toml
  - ~/.codex/*.config.toml -> <repo>/config/codex/templates/profiles/*.config.toml
  - ~/.codex/bin/codex_verify -> <repo>/config/codex/templates/codex_verify.example.sh
  - ~/.codex/bin/digest-xcodebuild-log -> <repo>/tools/digest-xcodebuild-log.sh
  - ~/.codex/templates/codex_verify.example.sh -> <repo>/config/codex/templates/codex_verify.example.sh
  - ~/.codex/templates/ui-smoke.example.yml -> <repo>/config/codex/templates/ui-smoke.example.yml
  - ~/.copilot/skills -> <repo>/skills (默认)
  - ~/.copilot/skills -> ~/.cc-switch/iOSAgentSkills/skills（当启用 --ccswitch 时）
  - ~/.claude/CLAUDE.md -> <repo>/CLAUDE.md
  - ~/.claude/skills -> <repo>/skills (默认)
  - ~/.claude/skills -> ~/.cc-switch/iOSAgentSkills/skills（当启用 --ccswitch 时）
  - ~/.claude/settings.json -> merge config/claude-code/settings.json into existing
  - ~/.claude/agents/*.md -> <repo>/config/claude-code/agents/*.md
  - ~/.cc-switch/skills -> <repo>/skills（固定不随 --ccswitch 切换）
  - ~/.codex/config.toml -> merge repo config/codex/codex.shared.toml without overriding local model/reasoning/Fast preferences
  - ~/.codex/config.toml -> ensure model_instructions_file points to ~/.codex/AGENTS.md
  - ~/.codex/config.toml -> keep Codex memories enabled without overwriting local-only state
  - ~/.config/git/commitlint.py + hooks/commit-msg -> repo-managed global commit message lint

When --ccswitch is specified, the script synchronizes skills into:
  ~/.cc-switch/iOSAgentSkills/skills
and links ~/.codex/skills / ~/.claude/skills to that staging directory, avoiding CC Switch import actions
from deleting files in the current checked-out repository.
~/.copilot/skills will follow the same target as ~/.codex/skills.

When --claude-only is specified, all Codex-specific steps (~/.codex/*, ~/.copilot/*) are skipped.
Claude Code setup and global Git commitlint hook synchronization still run.

Codex Profile templates are installed only when the corresponding local file is missing.
Use --refresh-profiles to back up and replace existing ~/.codex/*.config.toml files explicitly.

When --init-project <path> is specified, the script initializes or updates:
  <path>/.codex/xcodebuild.env
with detected workspace/project, scheme, Debug configuration, and device fallback defaults.
The generated file is project-local; device IDs remain commented because they are machine-specific.
The script also ensures <path>/.gitignore ignores .codex/ verification artifacts and local overrides.

When --init-memory <path> is specified, the script prints a memory-seeding prompt to use as
the first message when starting Claude Code in the given project directory.

When conflicting local files or directories already exist, the script backs them up to:
  ~/.agent-skills-backups/iOSAgentSkills/<timestamp>/
EOF
}

DRY_RUN='0'
CCSWITCH_MODE='0'
CLAUDE_ONLY='0'
REFRESH_PROFILES='0'
INIT_PROJECT_PATH=''
INIT_MEMORY_PATH=''

require_option_value() {
  local option="$1"
  local value="${2:-}"
  if [[ -z "$value" || "$value" == --* ]]; then
    echo "Error: $option requires a path argument" >&2
    usage >&2
    exit 1
  fi
}

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
    --refresh-profiles)
      REFRESH_PROFILES='1'
      shift
      ;;
    --init-project)
      require_option_value "$1" "${2:-}"
      INIT_PROJECT_PATH="$2"
      shift 2
      ;;
    --init-memory)
      require_option_value "$1" "${2:-}"
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
REPO_CODEX_PROFILE_TEMPLATES="$REPO_CODEX_TEMPLATES/profiles"
REPO_CODEX_VERIFY_TEMPLATE="$REPO_CODEX_TEMPLATES/codex_verify.example.sh"
REPO_CODEX_UI_SMOKE_TEMPLATE="$REPO_CODEX_TEMPLATES/ui-smoke.example.yml"
REPO_XCODEBUILD_DIGEST_SCRIPT="$REPO_ROOT/tools/digest-xcodebuild-log.sh"
CODEX_SYNC_SCRIPT="$REPO_ROOT/scripts/sync_codex_shared_config.py"
CODEX_AGENT_VALIDATE_SCRIPT="$REPO_ROOT/scripts/validate_codex_agent_templates.py"
CODEX_MODEL_POLICY_CHECK_SCRIPT="$REPO_ROOT/scripts/check_codex_model_policy.py"
REPO_CLAUDE_CONFIG="$REPO_ROOT/config/claude-code"
REPO_CLAUDE_SETTINGS="$REPO_CLAUDE_CONFIG/settings.json"
REPO_CLAUDE_AGENTS="$REPO_CLAUDE_CONFIG/agents"
REPO_CLAUDE_MEMORY_SEED="$REPO_CLAUDE_CONFIG/memory-seed.md"
CLAUDE_SYNC_SCRIPT="$REPO_ROOT/scripts/sync_claude_settings.py"
REPO_COMMITLINT_SCRIPT="$REPO_ROOT/scripts/commitlint.py"

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
CODEX_XCODEBUILD_DIGEST="$CODEX_BIN_DIR/digest-xcodebuild-log"
CODEX_TEMPLATES_DIR="$CODEX_DIR/templates"
CODEX_VERIFY_TEMPLATE="$CODEX_TEMPLATES_DIR/codex_verify.example.sh"
CODEX_UI_SMOKE_TEMPLATE="$CODEX_TEMPLATES_DIR/ui-smoke.example.yml"
CCSWITCH_PUBLIC_SKILLS="$HOME_DIR/.cc-switch/skills"
CCSWITCH_CACHE_ROOT="$HOME_DIR/.cc-switch/iOSAgentSkills"
CCSWITCH_SKILLS="$CCSWITCH_CACHE_ROOT/skills"
TARGET_SKILLS="$REPO_SKILLS"
GLOBAL_GIT_DIR="$HOME_DIR/.config/git"
GLOBAL_GIT_HOOKS_DIR="$GLOBAL_GIT_DIR/hooks"
GLOBAL_GIT_COMMITLINT="$GLOBAL_GIT_DIR/commitlint.py"
GLOBAL_GIT_COMMIT_MSG_HOOK="$GLOBAL_GIT_HOOKS_DIR/commit-msg"

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

ensure_line_in_file() {
  local file_path="$1"
  local expected_line="$2"
  local label="$3"
  local action='updated'

  ensure_directory "$(dirname "$file_path")"

  if [[ -f "$file_path" && ! -L "$file_path" ]]; then
    if grep -Fxq "$expected_line" "$file_path"; then
      log "unchanged: $label"
      record_change unchanged
      return 0
    fi
  elif [[ -e "$file_path" || -L "$file_path" ]]; then
    backup_existing_path "$file_path"
    action='updated'
  else
    action='created'
  fi

  log "$action: $label"
  if [[ "$DRY_RUN" == '0' ]]; then
    if [[ -s "$file_path" ]]; then
      printf '\n%s\n' "$expected_line" >> "$file_path"
    else
      printf '%s\n' "$expected_line" > "$file_path"
    fi
  fi
  record_change "$action"
}

build_claude_md_content() {
  local repo_claude_md="$REPO_ROOT/CLAUDE.md"

  if [[ -f "$repo_claude_md" ]]; then
    cat "$repo_claude_md"
  else
    printf '%s\n' '# Claude Code Runtime Orchestration'
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

build_project_xcode_env_content() {
  local project_path="$1"

  python3 - "$project_path" <<'PY'
from __future__ import annotations

import re
import shlex
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(sys.argv[1]).expanduser().resolve()
if not root.exists() or not root.is_dir():
    raise SystemExit(f"project path is not a directory: {root}")


def rel(path: Path) -> str:
    return str(path.relative_to(root))


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def env_assignment(key: str, value: str) -> str:
    return f"{key}={shell_quote(value)}"


def commented_env_assignment(key: str, value: str) -> str:
    return f"# {key}={shell_quote(value)}"


def comment_list(label: str, values: list[str]) -> str:
    return "# " + label + ": " + ", ".join(value.replace("\n", " ") for value in values)


def workspace_candidates() -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.xcworkspace")
        if "Pods" not in path.parts
        and "project.xcworkspace" not in str(path)
        and len(path.relative_to(root).parts) <= 3
    )


def project_candidates() -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.xcodeproj")
        if "Pods" not in path.parts and len(path.relative_to(root).parts) <= 3
    )


def scheme_paths() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for path in sorted(root.rglob("*.xcscheme")):
        if "Pods" in path.parts:
            continue
        paths.setdefault(path.stem, path)
    return paths


def is_ui_test_name(name: str) -> bool:
    return bool(re.search(r"(?:^|[_-])UITESTS?$", name, re.IGNORECASE) or re.search(r"UITests?$", name, re.IGNORECASE))


def is_unit_test_name(name: str) -> bool:
    return bool(
        (re.search(r"(?:^|[_-])TESTS$", name, re.IGNORECASE) or re.search(r"(?<!UI)Tests$", name, re.IGNORECASE))
        and not is_ui_test_name(name)
    )


def is_generic_test_scheme(name: str) -> bool:
    return bool(re.search(r"(?:^|[_-])TEST$", name, re.IGNORECASE) and not is_ui_test_name(name))


def iter_scheme_testables(path: Path | None) -> list[str]:
    if path is None:
        return []
    try:
        scheme_root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return []
    names: list[str] = []
    for reference in scheme_root.findall(".//TestAction//TestableReference//BuildableReference"):
        for key in ("BuildableName", "BlueprintName"):
            value = reference.get(key)
            if value:
                name = Path(value).stem
                if name not in names:
                    names.append(name)
    return names


def scheme_sort_key(name: str, path: Path | None) -> tuple[int, str]:
    testables = iter_scheme_testables(path)
    if any(is_unit_test_name(item) for item in testables):
        return (0, name.lower())
    if is_unit_test_name(name):
        return (1, name.lower())
    if is_generic_test_scheme(name):
        return (2, name.lower())
    if any(is_ui_test_name(item) for item in testables):
        return (3, name.lower())
    if is_ui_test_name(name):
        return (4, name.lower())
    if not re.search(r"(^|[_-])(DEV|TEST|UAT|STAGING)$", name, re.IGNORECASE):
        return (5, name.lower())
    return (6, name.lower())


workspaces = workspace_candidates()
projects = project_candidates()
schemes = scheme_paths()
selected_workspace = rel(workspaces[0]) if workspaces else ""
selected_project = rel(projects[0]) if projects else ""
selected_scheme = ""
selected_testables: list[str] = []
if schemes:
    selected_scheme = sorted(schemes, key=lambda item: scheme_sort_key(item, schemes.get(item)))[0]
    selected_testables = iter_scheme_testables(schemes.get(selected_scheme))

if not selected_workspace and not selected_project:
    raise SystemExit(f"no .xcworkspace or .xcodeproj found under: {root}")

lines = [
    "# Generated by iOSAgentSkills install-local-agent-config.sh --init-project",
    "# Project-local Xcode verification defaults consumed by codex_verify / ios-verification.",
    "# Keep device-specific values commented unless this project must pin a local device.",
]
if selected_workspace:
    lines.append(env_assignment("XCODE_WORKSPACE", selected_workspace))
    lines.append(commented_env_assignment("XCODE_PROJECT", selected_project) if selected_project else commented_env_assignment("XCODE_PROJECT", "App.xcodeproj"))
else:
    lines.append(env_assignment("XCODE_PROJECT", selected_project))
if selected_scheme:
    lines.append(env_assignment("XCODE_SCHEME", selected_scheme))
else:
    lines.append(commented_env_assignment("XCODE_SCHEME", "App"))
lines.extend(
    [
        env_assignment("XCODE_CONFIGURATION", "Debug"),
        "# Default action remains build; Agents can inject test / -only-testing for targeted XCTest.",
        env_assignment("XCODE_ACTION", "build"),
        env_assignment("XCODE_DEVICE_FALLBACK", "1"),
        commented_env_assignment("XCODE_DESTINATION", "generic/platform=iOS Simulator"),
        commented_env_assignment("XCODE_DEVICE_ID", "00008110-001234567890001E"),
        commented_env_assignment("XCODE_DEVICE_NAME", "Your iPhone"),
        env_assignment("CODEX_VERIFY_ARTIFACT_DIR", ".codex/build-results/latest"),
    ]
)
if selected_testables:
    lines.append(comment_list("Detected testables", selected_testables))
if workspaces:
    lines.append(comment_list("Workspace candidates", [rel(path) for path in workspaces]))
if projects:
    lines.append(comment_list("Project candidates", [rel(path) for path in projects]))
if schemes:
    lines.append(comment_list("Scheme candidates", sorted(schemes)))
print("\n".join(lines))
PY
}

init_project_xcode_env() {
  local project_path="$1"
  local resolved_project_path
  local env_path
  local gitignore_path
  local content

  resolved_project_path="$(resolve_physical_path "$project_path")"
  env_path="$resolved_project_path/.codex/xcodebuild.env"
  gitignore_path="$resolved_project_path/.gitignore"
  content="$(build_project_xcode_env_content "$resolved_project_path")"
  ensure_text_file "$env_path" "$content" "$resolved_project_path/.codex/xcodebuild.env"
  ensure_line_in_file "$gitignore_path" ".codex/" "$resolved_project_path/.gitignore ignores .codex/"
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

sync_codex_profile_templates() {
  local source target base_name
  for source in "$REPO_CODEX_PROFILE_TEMPLATES"/*.config.toml; do
    [[ -f "$source" ]] || continue
    base_name="$(basename "$source")"
    target="$CODEX_DIR/$base_name"
    if [[ "$REFRESH_PROFILES" == '0' && ( -e "$target" || -L "$target" ) ]]; then
      log "preserved: ~/.codex/$base_name (use --refresh-profiles to replace)"
      record_change unchanged
      continue
    fi
    ensure_file_copied "$target" "$source" "~/.codex/$base_name"
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

sync_codex_xcodebuild_digest() {
  [[ -f "$REPO_XCODEBUILD_DIGEST_SCRIPT" ]] || return 0
  ensure_directory "$CODEX_BIN_DIR"
  ensure_file_copied "$CODEX_XCODEBUILD_DIGEST" "$REPO_XCODEBUILD_DIGEST_SCRIPT" "~/.codex/bin/digest-xcodebuild-log"
  if [[ "$DRY_RUN" == '0' ]]; then
    chmod +x "$CODEX_XCODEBUILD_DIGEST"
  fi
}

GLOBAL_COMMIT_MSG_HOOK_CONTENT=$'#!/usr/bin/env bash\nset -euo pipefail\nexec python3 "$HOME/.config/git/commitlint.py" "$1"'

sync_global_git_hooks() {
  [[ -f "$REPO_COMMITLINT_SCRIPT" ]] || return 0

  ensure_directory "$GLOBAL_GIT_HOOKS_DIR"
  ensure_file_copied "$GLOBAL_GIT_COMMITLINT" "$REPO_COMMITLINT_SCRIPT" "~/.config/git/commitlint.py"
  ensure_text_file "$GLOBAL_GIT_COMMIT_MSG_HOOK" "$GLOBAL_COMMIT_MSG_HOOK_CONTENT" "~/.config/git/hooks/commit-msg"

  if [[ "$DRY_RUN" == '0' ]]; then
    chmod +x "$GLOBAL_GIT_COMMITLINT" "$GLOBAL_GIT_COMMIT_MSG_HOOK"
    git config --global core.hooksPath "$GLOBAL_GIT_HOOKS_DIR"
  else
    log "dry-run: git config --global core.hooksPath $GLOBAL_GIT_HOOKS_DIR"
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

  if [[ ! -d "$REPO_CODEX_PROFILE_TEMPLATES" ]]; then
    echo "Error: missing Codex profile templates directory: $REPO_CODEX_PROFILE_TEMPLATES" >&2
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

  if [[ ! -f "$CODEX_MODEL_POLICY_CHECK_SCRIPT" ]]; then
    echo "Error: missing Codex model policy check script: $CODEX_MODEL_POLICY_CHECK_SCRIPT" >&2
    exit 1
  fi

  python3 "$CODEX_MODEL_POLICY_CHECK_SCRIPT" --offline >/dev/null || {
    echo "Error: repository Codex model/profile policy is invalid" >&2
    exit 1
  }
fi

if [[ ! -f "$REPO_COMMITLINT_SCRIPT" ]]; then
  echo "Error: missing commitlint script: $REPO_COMMITLINT_SCRIPT" >&2
  exit 1
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
  if [[ -f "$REPO_XCODEBUILD_DIGEST_SCRIPT" ]]; then
    [[ -f "$CODEX_XCODEBUILD_DIGEST" && ! -L "$CODEX_XCODEBUILD_DIGEST" ]] || fail "~/.codex/bin/digest-xcodebuild-log is missing or not a regular file"
    cmp -s "$REPO_XCODEBUILD_DIGEST_SCRIPT" "$CODEX_XCODEBUILD_DIGEST" || fail "~/.codex/bin/digest-xcodebuild-log does not match repo script"
    [[ -x "$CODEX_XCODEBUILD_DIGEST" ]] || fail "~/.codex/bin/digest-xcodebuild-log is not executable"
  fi

  if [[ -f "$REPO_CODEX_UI_SMOKE_TEMPLATE" ]]; then
    [[ -f "$CODEX_UI_SMOKE_TEMPLATE" && ! -L "$CODEX_UI_SMOKE_TEMPLATE" ]] || fail "~/.codex/templates/ui-smoke.example.yml is missing or not a regular file"
    cmp -s "$REPO_CODEX_UI_SMOKE_TEMPLATE" "$CODEX_UI_SMOKE_TEMPLATE" || fail "~/.codex/templates/ui-smoke.example.yml does not match repo template"
  fi
}

verify_codex_profile_templates() {
  local source target base_name
  for source in "$REPO_CODEX_PROFILE_TEMPLATES"/*.config.toml; do
    [[ -f "$source" ]] || continue
    base_name="$(basename "$source")"
    target="$CODEX_DIR/$base_name"
    [[ -f "$target" && ! -L "$target" ]] || fail "~/.codex/$base_name is missing or not a regular file"
    python3 - "$target" <<'PY' || fail "~/.codex/$base_name is not valid TOML"
from pathlib import Path
import sys
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        import pip._vendor.tomli as tomllib

tomllib.loads(Path(sys.argv[1]).read_text())
PY
    if [[ "$REFRESH_PROFILES" == '1' ]]; then
      cmp -s "$source" "$target" || fail "~/.codex/$base_name does not match refreshed repo template"
    fi
  done
}

verify_global_git_hooks() {
  [[ -f "$GLOBAL_GIT_COMMITLINT" && ! -L "$GLOBAL_GIT_COMMITLINT" ]] || fail "~/.config/git/commitlint.py is missing or not a regular file"
  cmp -s "$REPO_COMMITLINT_SCRIPT" "$GLOBAL_GIT_COMMITLINT" || fail "~/.config/git/commitlint.py does not match repo script"
  [[ -x "$GLOBAL_GIT_COMMITLINT" ]] || fail "~/.config/git/commitlint.py is not executable"
  [[ -f "$GLOBAL_GIT_COMMIT_MSG_HOOK" && ! -L "$GLOBAL_GIT_COMMIT_MSG_HOOK" ]] || fail "~/.config/git/hooks/commit-msg is missing or not a regular file"
  [[ "$(cat "$GLOBAL_GIT_COMMIT_MSG_HOOK")" == "$GLOBAL_COMMIT_MSG_HOOK_CONTENT" ]] || fail "~/.config/git/hooks/commit-msg does not match expected content"
  [[ -x "$GLOBAL_GIT_COMMIT_MSG_HOOK" ]] || fail "~/.config/git/hooks/commit-msg is not executable"
  [[ "$(git config --global --get core.hooksPath)" == "$GLOBAL_GIT_HOOKS_DIR" ]] || fail "global core.hooksPath does not point to ~/.config/git/hooks"
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
    verify_codex_profile_templates
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
  verify_global_git_hooks
}

if [[ "$CLAUDE_ONLY" == '0' ]]; then
  ensure_symlink "$CODEX_AGENTS" "$REPO_AGENTS" "~/.codex/AGENTS.md"
  ensure_symlink "$CODEX_SKILLS" "$TARGET_SKILLS" "~/.codex/skills"
  ensure_symlink "$COPILOT_SKILLS" "$TARGET_SKILLS" "~/.copilot/skills"
  ensure_codex_config
  sync_codex_agent_templates
  sync_codex_profile_templates
  sync_codex_verify_wrapper
  sync_codex_xcodebuild_digest
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
sync_global_git_hooks

if [[ -n "$INIT_PROJECT_PATH" ]]; then
  init_project_xcode_env "$INIT_PROJECT_PATH"
fi

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
