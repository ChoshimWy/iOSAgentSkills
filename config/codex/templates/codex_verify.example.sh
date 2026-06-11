#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./codex_verify.sh -- <xcodebuild args...>
  ./codex_verify.sh --repo-root <repo-root> -- <xcodebuild args...>
  ./codex_verify.sh --build-check <build-check.sh> <repo-root> [build-check args...]
  ~/.codex/bin/codex_verify --repo-root <repo-root> -- <xcodebuild args...>

Purpose:
  Route local project-environment validation into a CLI-specific DerivedData slot
  first, and fall back to serialized system DerivedData only when needed.

Recommended:
  - Preferred: keep this script in the target Xcode project root as ./codex_verify.sh
  - Fallback: install it globally as ~/.codex/bin/codex_verify
  - Ask all agents to use one of the two entrypoints instead of裸跑 xcodebuild
  - Let iOSAgentSkills verify-ios-build delegate into the project wrapper first,
    then fall back to the global wrapper automatically
EOF
}

die() {
  echo "[codex_verify] $*" >&2
  exit 1
}

timestamp_now() {
  date '+%Y-%m-%d %H:%M:%S %z'
}

seconds_now() {
  date '+%s'
}

trim_trailing_space() {
  sed 's/[[:space:]]*$//'
}

resolve_path() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).resolve())
PY
}

resolve_repo_member_path() {
  local candidate="$1"
  if [[ "$candidate" == /* ]]; then
    resolve_path "$candidate"
  else
    resolve_path "$REPO_ROOT/$candidate"
  fi
}

read_env_file_value() {
  local key="$1"
  [[ -f "$XCODE_ENV_FILE" ]] || return 0
  (
    set -a
    # shellcheck source=/dev/null
    source "$XCODE_ENV_FILE"
    eval 'printf "%s" "${'"$key"':-}"'
  )
}

env_or_file_value() {
  local key="$1"
  if [[ ${!key+x} == x ]]; then
    printf '%s' "${!key}"
    return 0
  fi
  read_env_file_value "$key" || true
}

join_quoted_command() {
  local out=''
  local part
  for part in "$@"; do
    out+=$(printf '%q ' "$part")
  done
  printf '%s' "$out" | trim_trailing_space
}

sanitize_token() {
  local value="$1"
  value="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  value="$(printf '%s' "$value" | tr -cs '[:alnum:]._-+' '-')"
  value="${value#-}"
  value="${value%-}"
  if [[ -z "$value" ]]; then
    value='slot'
  fi
  printf '%s' "$value"
}

hash_text() {
  printf '%s' "$1" | shasum -a 256 | awk '{print $1}'
}

build_owner_body() {
  cat <<EOF
pid=$$
user=${USER:-unknown}
host=$(hostname -s 2>/dev/null || hostname)
repo_root=$REPO_ROOT
lock_basis=$LOCK_BASIS
mode=$MODE
workspace=${META_WORKSPACE}
project=${META_PROJECT}
scheme=${META_SCHEME}
configuration=${META_CONFIGURATION}
destination=${META_DESTINATION}
action=${META_ACTION}
derived_data_mode=${EFFECTIVE_DERIVED_DATA_MODE:-unset}
derived_data_slot=${DERIVED_DATA_SLOT_ID:-unset}
derived_data_path=${DERIVED_DATA_PATH:-system-default}
started_at=$(timestamp_now)
command=$COMMAND_PREVIEW
log_file=$LOG_FILE
EOF
}

directory_lock_owner_summary() {
  local lock_dir="$1"
  local owner_file="$lock_dir/owner.txt"
  [[ -f "$owner_file" ]] || return 0
  awk 'NF { print }' "$owner_file" | paste -sd '; ' -
}

declare -a ACQUIRED_DIRECTORY_LOCKS=()
LOCK_BACKEND=''
LOCK_FILE=''
OWNER_FILE=''

register_directory_lock() {
  ACQUIRED_DIRECTORY_LOCKS+=("$1")
}

unregister_directory_lock() {
  local target="$1"
  local -a updated=()
  local item
  for item in "${ACQUIRED_DIRECTORY_LOCKS[@]}"; do
    if [[ -n "$item" && "$item" != "$target" ]]; then
      updated+=("$item")
    fi
  done
  if [[ ${#updated[@]} -gt 0 ]]; then
    ACQUIRED_DIRECTORY_LOCKS=("${updated[@]}")
  else
    ACQUIRED_DIRECTORY_LOCKS=()
  fi
}

release_directory_lock() {
  local lock_dir="$1"
  [[ -n "$lock_dir" ]] || return 0
  rm -rf "$lock_dir"
}

acquire_directory_lock() {
  local lock_dir="$1"
  local label="$2"
  local owner_body="$3"
  local wait_started now waited owner_summary

  mkdir -p "$(dirname "$lock_dir")"
  wait_started="$(seconds_now)"
  while ! mkdir "$lock_dir" 2>/dev/null; do
    now="$(seconds_now)"
    waited=$(( now - wait_started ))
    owner_summary="$(directory_lock_owner_summary "$lock_dir")"
    if [[ -n "$owner_summary" ]]; then
      echo "[codex_verify] waiting ${waited}s for ${label}: ${owner_summary}" >&2
    else
      echo "[codex_verify] waiting ${waited}s for ${label}: lock_dir=$lock_dir" >&2
    fi
    sleep "$WAIT_INTERVAL_SECONDS"
  done

  printf '%s\n' "$owner_body" >"$lock_dir/owner.txt"
  register_directory_lock "$lock_dir"
}

cleanup_repo_lock() {
  [[ -n "$OWNER_FILE" ]] && rm -f "$OWNER_FILE"
  if [[ "$LOCK_BACKEND" == 'shlock' ]]; then
    [[ -n "$LOCK_FILE" ]] && rm -f "$LOCK_FILE"
  fi
}

cleanup_all() {
  local index
  cleanup_repo_lock || true
  for (( index=${#ACQUIRED_DIRECTORY_LOCKS[@]}-1; index>=0; index-=1 )); do
    release_directory_lock "${ACQUIRED_DIRECTORY_LOCKS[$index]}" || true
  done
}

trap cleanup_all EXIT INT TERM HUP

summarize_owner() {
  [[ -f "$OWNER_FILE" ]] || return 0
  awk 'NF { print }' "$OWNER_FILE" | paste -sd '; ' -
}

wait_for_lockf_lock() {
  local now wait_started
  wait_started="$(seconds_now)"
  exec 9>"$LOCK_FILE"
  while ! /usr/bin/lockf -s -t 0 9 2>/dev/null; do
    local waited owner_summary
    now="$(seconds_now)"
    waited=$(( now - wait_started ))
    owner_summary="$(summarize_owner)"
    if [[ -n "$owner_summary" ]]; then
      echo "[codex_verify] waiting ${waited}s for project validation lock: ${owner_summary}" >&2
    else
      echo "[codex_verify] waiting ${waited}s for project validation lock: lock_file=$LOCK_FILE" >&2
    fi
    sleep "$WAIT_INTERVAL_SECONDS"
  done
}

wait_for_shlock_lock() {
  local now wait_started
  wait_started="$(seconds_now)"
  while ! /usr/bin/shlock -f "$LOCK_FILE" -p "$$" 2>/dev/null; do
    local waited owner_summary
    now="$(seconds_now)"
    waited=$(( now - wait_started ))
    owner_summary="$(summarize_owner)"
    if [[ -n "$owner_summary" ]]; then
      echo "[codex_verify] waiting ${waited}s for project validation lock: ${owner_summary}" >&2
    else
      echo "[codex_verify] waiting ${waited}s for project validation lock: lock_file=$LOCK_FILE" >&2
    fi
    sleep "$WAIT_INTERVAL_SECONDS"
  done
}

acquire_repo_serial_lock() {
  LOCK_BACKEND=''
  if command -v /usr/bin/lockf >/dev/null 2>&1; then
    LOCK_BACKEND='lockf'
    wait_for_lockf_lock
  elif command -v /usr/bin/shlock >/dev/null 2>&1; then
    LOCK_BACKEND='shlock'
    wait_for_shlock_lock
  else
    die "neither /usr/bin/lockf nor /usr/bin/shlock is available on this host"
  fi

  printf '%s\n' "$(build_owner_body)" >"$OWNER_FILE"
}

load_metadata_from_xcode_args() {
  local args=("$@")
  local index=0
  while [[ $index -lt ${#args[@]} ]]; do
    local arg="${args[$index]}"
    case "$arg" in
      -workspace)
        ((index += 1))
        META_WORKSPACE="${args[$index]:-}"
        ;;
      -project)
        ((index += 1))
        META_PROJECT="${args[$index]:-}"
        ;;
      -scheme)
        ((index += 1))
        META_SCHEME="${args[$index]:-}"
        ;;
      -destination)
        ((index += 1))
        META_DESTINATION="${args[$index]:-}"
        ;;
      -configuration)
        ((index += 1))
        META_CONFIGURATION="${args[$index]:-}"
        ;;
      build|build-for-testing|test|test-without-building|archive|analyze|clean)
        META_ACTION="$arg"
        ;;
      -exportArchive)
        META_ACTION='exportArchive'
        ;;
    esac
    ((index += 1))
  done
}

load_metadata_defaults() {
  META_WORKSPACE="${META_WORKSPACE:-$(read_env_file_value XCODE_WORKSPACE)}"
  META_PROJECT="${META_PROJECT:-$(read_env_file_value XCODE_PROJECT)}"
  META_SCHEME="${META_SCHEME:-$(read_env_file_value XCODE_SCHEME)}"
  META_CONFIGURATION="${META_CONFIGURATION:-$(read_env_file_value XCODE_CONFIGURATION)}"
  META_ACTION="${META_ACTION:-$(read_env_file_value XCODE_ACTION)}"

  if [[ -z "${META_DESTINATION:-}" ]]; then
    local explicit_destination explicit_device_id explicit_device_name
    explicit_destination="$(read_env_file_value XCODE_DESTINATION)"
    explicit_device_id="$(read_env_file_value XCODE_DEVICE_ID)"
    explicit_device_name="$(read_env_file_value XCODE_DEVICE_NAME)"
    if [[ -n "$explicit_destination" ]]; then
      META_DESTINATION="$explicit_destination"
    elif [[ -n "$explicit_device_id" ]]; then
      META_DESTINATION="id=$explicit_device_id"
    elif [[ -n "$explicit_device_name" ]]; then
      META_DESTINATION="name=$explicit_device_name"
    else
      META_DESTINATION='auto(connected-device-preferred)'
    fi
  fi

  META_WORKSPACE="${META_WORKSPACE:-auto}"
  META_PROJECT="${META_PROJECT:-auto}"
  META_SCHEME="${META_SCHEME:-auto}"
  META_CONFIGURATION="${META_CONFIGURATION:-Debug(auto)}"
  META_ACTION="${META_ACTION:-build(auto)}"
}

normalize_derived_data_mode() {
  local mode="$1"
  case "$mode" in
    ''|isolated-preferred)
      printf '%s' 'isolated-preferred'
      ;;
    isolated-required|system-serial)
      printf '%s' "$mode"
      ;;
    *)
      die "unsupported XCODE_DERIVED_DATA_MODE: $mode"
      ;;
  esac
}

normalize_seed_mode() {
  local mode="$1"
  case "$mode" in
    ''|once)
      printf '%s' 'once'
      ;;
    always|empty)
      printf '%s' "$mode"
      ;;
    *)
      die "unsupported XCODE_DERIVED_DATA_SEED_MODE: $mode"
      ;;
  esac
}

current_xcode_version_hash() {
  local version_output
  version_output="$(xcodebuild -version 2>/dev/null || true)"
  if [[ -z "$version_output" ]]; then
    version_output='unknown-xcode-version'
  fi
  hash_text "$version_output"
}

target_cache_stem() {
  if [[ "${META_WORKSPACE}" != 'auto' ]]; then
    basename "${META_WORKSPACE%*.xcworkspace}"
  elif [[ "${META_PROJECT}" != 'auto' ]]; then
    basename "${META_PROJECT%*.xcodeproj}"
  else
    basename "$REPO_ROOT"
  fi
}

discover_slot_id() {
  local manual_slot
  manual_slot="$(env_or_file_value CODEX_DERIVED_DATA_SLOT)"
  if [[ -n "$manual_slot" ]]; then
    DERIVED_DATA_SLOT_REASON='using explicit CODEX_DERIVED_DATA_SLOT'
    DERIVED_DATA_SLOT_ID="$(sanitize_token "$manual_slot")"
    return 0
  fi

  local current_pid="$PPID"
  local depth=0
  local ps_line pid ppid command label
  while [[ -n "$current_pid" && $depth -lt 12 ]]; do
    ps_line="$(ps -o pid=,ppid=,command= -p "$current_pid" 2>/dev/null | head -n 1 | sed 's/^[[:space:]]*//' || true)"
    [[ -n "$ps_line" ]] || break
    pid="$(printf '%s\n' "$ps_line" | awk '{print $1}')"
    ppid="$(printf '%s\n' "$ps_line" | awk '{print $2}')"
    command="$(printf '%s\n' "$ps_line" | cut -d' ' -f3-)"
    label=''
    if printf '%s' "$command" | grep -Eqi '(^|/)(codex|codex-cli)([[:space:]]|$)'; then
      label='codex-cli'
    elif printf '%s' "$command" | grep -Eqi '(^|/)(claude|claude-code)([[:space:]]|$)'; then
      label='claude-cli'
    fi
    if [[ -n "$label" && -n "$pid" ]]; then
      DERIVED_DATA_SLOT_REASON="derived from parent process $label pid=$pid"
      DERIVED_DATA_SLOT_ID="$(sanitize_token "${label}-${pid}")"
      return 0
    fi
    current_pid="$ppid"
    depth=$(( depth + 1 ))
  done

  local tty_name
  tty_name="$(tty 2>/dev/null || true)"
  if [[ -n "$tty_name" && "$tty_name" != 'not a tty' ]]; then
    DERIVED_DATA_SLOT_REASON="derived from tty $tty_name"
    DERIVED_DATA_SLOT_ID="$(sanitize_token "tty-${tty_name#/dev/}")"
    return 0
  fi

  if [[ -n "${PPID:-}" ]]; then
    DERIVED_DATA_SLOT_REASON="derived from parent shell pid=$PPID"
    DERIVED_DATA_SLOT_ID="$(sanitize_token "ppid-${PPID}")"
    return 0
  fi

  DERIVED_DATA_SLOT_REASON='fallback to current shell pid'
  DERIVED_DATA_SLOT_ID="$(sanitize_token "shell-$$")"
}

select_seed_project_dir() {
  python3 - "$SYSTEM_DERIVED_DATA_HOME" "$TARGET_CACHE_STEM" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
stem = sys.argv[2]
if not root.exists():
    raise SystemExit(0)

candidates = sorted(
    (path for path in root.iterdir() if path.is_dir() and path.name.startswith(f"{stem}-")),
    key=lambda item: item.stat().st_mtime,
    reverse=True,
)
if candidates:
    print(candidates[0])
PY
}

sync_directory_contents() {
  local source_dir="$1"
  local dest_dir="$2"
  [[ -d "$source_dir" ]] || return 0
  mkdir -p "$dest_dir"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$source_dir"/ "$dest_dir"/
  elif command -v ditto >/dev/null 2>&1; then
    ditto "$source_dir" "$dest_dir"
  else
    cp -R "$source_dir"/. "$dest_dir"/
  fi
}

sync_file_if_exists() {
  local source_file="$1"
  local dest_file="$2"
  [[ -f "$source_file" ]] || return 0
  mkdir -p "$(dirname "$dest_file")"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$source_file" "$dest_file"
  elif command -v ditto >/dev/null 2>&1; then
    ditto "$source_file" "$dest_file"
  else
    cp "$source_file" "$dest_file"
  fi
}

read_metadata_value() {
  local file="$1"
  local key="$2"
  [[ -f "$file" ]] || return 0
  awk -F= -v target="$key" '
    $1 == target {
      print substr($0, index($0, "=") + 1)
      exit
    }
  ' "$file"
}

needs_reseed() {
  if [[ "$DERIVED_DATA_REFRESH" == '1' ]]; then
    return 0
  fi
  if [[ "$DERIVED_DATA_SEED_MODE" == 'always' ]]; then
    return 0
  fi
  if [[ ! -d "$DERIVED_DATA_PATH" ]]; then
    return 0
  fi
  if [[ ! -f "$DERIVED_DATA_METADATA" ]]; then
    return 0
  fi
  local recorded_hash recorded_stem recorded_mode
  recorded_hash="$(read_metadata_value "$DERIVED_DATA_METADATA" XCODE_VERSION_HASH)"
  recorded_stem="$(read_metadata_value "$DERIVED_DATA_METADATA" TARGET_CACHE_STEM)"
  recorded_mode="$(read_metadata_value "$DERIVED_DATA_METADATA" SEED_MODE)"
  if [[ "$recorded_hash" != "$CURRENT_XCODE_VERSION_HASH" ]]; then
    return 0
  fi
  if [[ "$recorded_stem" != "$TARGET_CACHE_STEM" ]]; then
    return 0
  fi
  if [[ "$recorded_mode" == 'empty' && "$DERIVED_DATA_SEED_MODE" != 'empty' ]]; then
    return 0
  fi
  return 1
}

write_slot_metadata() {
  cat >"$DERIVED_DATA_METADATA" <<EOF
XCODE_VERSION_HASH=$CURRENT_XCODE_VERSION_HASH
TARGET_CACHE_STEM=$TARGET_CACHE_STEM
SEED_MODE=$DERIVED_DATA_SEED_MODE
SEEDED_AT=$(timestamp_now)
SEEDED_SOURCE=${DERIVED_DATA_SEED_SOURCE:-none}
LOCK_BASIS_HASH=$LOCK_KEY
EOF
}

seed_slot_from_system_cache() {
  mkdir -p "$DERIVED_DATA_ROOT"
  rm -rf "$DERIVED_DATA_PATH"
  mkdir -p "$DERIVED_DATA_PATH"

  DERIVED_DATA_SEED_SOURCE='empty'
  if [[ "$DERIVED_DATA_SEED_MODE" == 'empty' ]]; then
    write_slot_metadata
    return 0
  fi

  if [[ ! -d "$SYSTEM_DERIVED_DATA_HOME" ]]; then
    write_slot_metadata
    return 0
  fi

  sync_directory_contents "$SYSTEM_DERIVED_DATA_HOME/ModuleCache.noindex" "$DERIVED_DATA_PATH/ModuleCache.noindex"
  sync_directory_contents "$SYSTEM_DERIVED_DATA_HOME/SDKStatCaches.noindex" "$DERIVED_DATA_PATH/SDKStatCaches.noindex"

  local selected_project_dir
  selected_project_dir="$(select_seed_project_dir)"
  if [[ -n "$selected_project_dir" && -d "$selected_project_dir" ]]; then
    DERIVED_DATA_SEED_SOURCE="$selected_project_dir"
    sync_directory_contents "$selected_project_dir/Build" "$DERIVED_DATA_PATH/Build"
    sync_directory_contents "$selected_project_dir/SourcePackages" "$DERIVED_DATA_PATH/SourcePackages"
    sync_directory_contents "$selected_project_dir/Index.noindex" "$DERIVED_DATA_PATH/Index.noindex"
    sync_directory_contents "$selected_project_dir/Logs/Build" "$DERIVED_DATA_PATH/Logs/Build"
    sync_file_if_exists "$selected_project_dir/info.plist" "$DERIVED_DATA_PATH/info.plist"
  fi

  write_slot_metadata
}

prepare_isolated_derived_data() {
  local seed_owner_body
  seed_owner_body="$(build_owner_body)"
  acquire_directory_lock "$SEED_LOCK_DIR" 'derived data seed lock' "$seed_owner_body"
  if needs_reseed; then
    seed_slot_from_system_cache
  else
    DERIVED_DATA_SEED_SOURCE="$(read_metadata_value "$DERIVED_DATA_METADATA" SEEDED_SOURCE)"
    DERIVED_DATA_SEED_SOURCE="${DERIVED_DATA_SEED_SOURCE:-reused-existing-slot}"
  fi
  release_directory_lock "$SEED_LOCK_DIR"
  unregister_directory_lock "$SEED_LOCK_DIR"
}

command_has_derived_data_path() {
  local args=("$@")
  local index=0
  while [[ $index -lt ${#args[@]} ]]; do
    if [[ "${args[$index]}" == '-derivedDataPath' ]]; then
      return 0
    fi
    index=$(( index + 1 ))
  done
  return 1
}

build_run_command() {
  RUN_COMMAND=("${COMMAND[@]}")
  if [[ "$MODE" == 'xcodebuild' && "$EFFECTIVE_DERIVED_DATA_MODE" != 'system-serial' ]]; then
    if ! command_has_derived_data_path "${RUN_COMMAND[@]}"; then
      RUN_COMMAND+=( -derivedDataPath "$DERIVED_DATA_PATH" )
    fi
  fi
}

destination_lock_key() {
  local destination="$1"
  if [[ -z "$destination" || "$destination" == 'auto(connected-device-preferred)' ]]; then
    printf '%s' ''
    return 0
  fi
  printf '%s' "$(hash_text "$destination")"
}

is_test_like_action() {
  case "${META_ACTION}" in
    test|test-without-building)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

log_effective_header() {
  echo "[codex_verify] repo_root=$REPO_ROOT" >&2
  echo "[codex_verify] lock_basis=$LOCK_BASIS" >&2
  echo "[codex_verify] workspace=${META_WORKSPACE} project=${META_PROJECT} scheme=${META_SCHEME} destination=${META_DESTINATION}" >&2
  echo "[codex_verify] action=${META_ACTION} configuration=${META_CONFIGURATION}" >&2
  echo "[codex_verify] derived_data_mode=${EFFECTIVE_DERIVED_DATA_MODE}" >&2
  if [[ "$EFFECTIVE_DERIVED_DATA_MODE" == 'system-serial' ]]; then
    echo "[codex_verify] derived_data_path=$SYSTEM_DERIVED_DATA_HOME (system default)" >&2
  else
    echo "[codex_verify] derived_data_slot=$DERIVED_DATA_SLOT_ID ($DERIVED_DATA_SLOT_REASON)" >&2
    echo "[codex_verify] derived_data_path=$DERIVED_DATA_PATH" >&2
    echo "[codex_verify] seed_mode=$DERIVED_DATA_SEED_MODE refresh=$DERIVED_DATA_REFRESH seed_source=${DERIVED_DATA_SEED_SOURCE:-pending}" >&2
  fi
  echo "[codex_verify] log_file=$LOG_FILE" >&2
}

run_logged_command() {
  local -a command_to_run=("$@")
  set +e
  (
    cd "$REPO_ROOT"
    export CODEX_EFFECTIVE_DERIVED_DATA_MODE="$EFFECTIVE_DERIVED_DATA_MODE"
    export CODEX_EFFECTIVE_DERIVED_DATA_PATH="${DERIVED_DATA_PATH:-}"
    export CODEX_EFFECTIVE_DERIVED_DATA_SLOT="${DERIVED_DATA_SLOT_ID:-}"
    export CODEX_VERIFY_DESTINATION_LOCK_ROOT="$DESTINATION_LOCK_ROOT"
    export CODEX_VERIFY_LOCK_POLL_SECONDS="$WAIT_INTERVAL_SECONDS"
    if [[ "$EFFECTIVE_DERIVED_DATA_MODE" != 'system-serial' ]]; then
      export XCODE_DERIVED_DATA="$DERIVED_DATA_PATH"
    else
      unset XCODE_DERIVED_DATA
      unset CODEX_EFFECTIVE_DERIVED_DATA_PATH
      unset CODEX_EFFECTIVE_DERIVED_DATA_SLOT
    fi
    if [[ "$MODE" == 'build-check' ]]; then
      export CODEX_VERIFY_BYPASS_WRAPPER=1
    fi
    "${command_to_run[@]}"
  ) 2>&1 | tee "$LOG_FILE"
  COMMAND_STATUS=${PIPESTATUS[0]}
  set -e
  return "$COMMAND_STATUS"
}

log_contains_build_db_lock() {
  [[ -f "$LOG_FILE" ]] || return 1
  grep -Eqi 'build\.db:.*locked|database is locked|unable to attach DB|SWBBuildService' "$LOG_FILE"
}

execute_isolated_mode() {
  local slot_owner_body slot_lock_dir destination_hash destination_lock_dir

  slot_owner_body="$(build_owner_body)"
  acquire_directory_lock "$SLOT_LOCK_DIR" 'derived data slot lock' "$slot_owner_body"

  if [[ "$MODE" == 'xcodebuild' && -n "${META_DESTINATION}" ]] && is_test_like_action; then
    destination_hash="$(destination_lock_key "$META_DESTINATION")"
    if [[ -n "$destination_hash" ]]; then
      destination_lock_dir="$DESTINATION_LOCK_ROOT/destination-$destination_hash.lockdir"
      acquire_directory_lock "$destination_lock_dir" 'destination validation lock' "$slot_owner_body"
    fi
  fi

  build_run_command
  log_effective_header
  run_logged_command "${RUN_COMMAND[@]}"
}

execute_system_serial_mode() {
  build_run_command
  EFFECTIVE_DERIVED_DATA_MODE='system-serial'
  LOCK_DIR="/tmp/codex-xcodebuild-locks/$LOCK_KEY"
  LOCK_FILE="$LOCK_DIR/project.lock"
  OWNER_FILE="$LOCK_DIR/owner.txt"
  mkdir -p "$LOCK_DIR" "$LOG_DIR"
  acquire_repo_serial_lock
  echo "[codex_verify] acquired validation lock" >&2
  log_effective_header
  run_logged_command "${RUN_COMMAND[@]}"
}

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 64
fi

MODE=''
WAIT_INTERVAL_SECONDS="${CODEX_VERIFY_LOCK_POLL_SECONDS:-5}"
SCRIPT_PATH="$(resolve_path "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" && pwd -P)"
USER_REPO_ROOT=''

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      [[ $# -ge 2 ]] || die "--repo-root requires a path"
      USER_REPO_ROOT="$2"
      shift 2
      ;;
    --|--build-check|--help|-h)
      break
      ;;
    *)
      usage >&2
      exit 64
      ;;
  esac
done

if [[ -n "$USER_REPO_ROOT" ]]; then
  REPO_ROOT="$(resolve_path "$USER_REPO_ROOT")"
elif [[ "$(basename "$SCRIPT_PATH")" == 'codex_verify.sh' ]]; then
  REPO_ROOT="$SCRIPT_DIR"
else
  REPO_ROOT="$(pwd -P)"
fi
XCODE_ENV_FILE="$REPO_ROOT/.codex/xcodebuild.env"

case "$1" in
  --)
    shift
    [[ $# -gt 0 ]] || die "missing xcodebuild arguments after --"
    MODE='xcodebuild'
    RAW_ARGS=("$@")
    if [[ "${RAW_ARGS[0]}" == "xcodebuild" ]]; then
      COMMAND=("xcodebuild" "${RAW_ARGS[@]:1}")
    else
      COMMAND=("xcodebuild" "${RAW_ARGS[@]}")
    fi
    ;;
  --build-check)
    shift
    [[ $# -ge 2 ]] || die "--build-check requires <build-check.sh> <repo-root>"
    MODE='build-check'
    BUILD_CHECK_SCRIPT="$1"
    BUILD_CHECK_ROOT="$2"
    shift 2
    [[ -f "$BUILD_CHECK_SCRIPT" ]] || die "build-check script not found: $BUILD_CHECK_SCRIPT"
    BUILD_CHECK_SCRIPT="$(resolve_path "$BUILD_CHECK_SCRIPT")"
    BUILD_CHECK_ROOT="$(resolve_path "$BUILD_CHECK_ROOT")"
    COMMAND=(bash "$BUILD_CHECK_SCRIPT" "$BUILD_CHECK_ROOT" "$@")
    ;;
  --help|-h)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 64
    ;;
esac

if [[ "$MODE" == 'build-check' ]]; then
  REPO_ROOT="$BUILD_CHECK_ROOT"
  XCODE_ENV_FILE="$REPO_ROOT/.codex/xcodebuild.env"
fi

META_WORKSPACE=''
META_PROJECT=''
META_SCHEME=''
META_DESTINATION=''
META_CONFIGURATION=''
META_ACTION=''

if [[ "$MODE" == 'xcodebuild' ]]; then
  load_metadata_from_xcode_args "${COMMAND[@]:1}"
fi
load_metadata_defaults

if [[ "${META_WORKSPACE}" != 'auto' ]]; then
  LOCK_BASIS="$(resolve_repo_member_path "$META_WORKSPACE")"
elif [[ "${META_PROJECT}" != 'auto' ]]; then
  LOCK_BASIS="$(resolve_repo_member_path "$META_PROJECT")"
else
  LOCK_BASIS="$REPO_ROOT"
fi

LOCK_KEY="$(printf '%s' "$LOCK_BASIS" | shasum -a 256 | awk '{print $1}')"
LOG_DIR="/tmp/codex-verify/$LOCK_KEY"
RUN_TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
LOG_FILE="$LOG_DIR/$RUN_TIMESTAMP.log"
COMMAND_PREVIEW="$(join_quoted_command "${COMMAND[@]}")"

SYSTEM_DERIVED_DATA_HOME="$HOME/Library/Developer/Xcode/DerivedData"
DERIVED_DATA_MODE="$(normalize_derived_data_mode "$(env_or_file_value XCODE_DERIVED_DATA_MODE)")"
DERIVED_DATA_SEED_MODE="$(normalize_seed_mode "$(env_or_file_value XCODE_DERIVED_DATA_SEED_MODE)")"
DERIVED_DATA_REFRESH="$(env_or_file_value XCODE_DERIVED_DATA_REFRESH)"
DERIVED_DATA_REFRESH="${DERIVED_DATA_REFRESH:-0}"
DERIVED_DATA_SLOT_ID=''
DERIVED_DATA_SLOT_REASON=''
discover_slot_id
DERIVED_DATA_ROOT="/tmp/codex-derived-data/$LOCK_KEY/$DERIVED_DATA_SLOT_ID"
DERIVED_DATA_PATH="$DERIVED_DATA_ROOT/DerivedData"
DERIVED_DATA_METADATA="$DERIVED_DATA_ROOT/metadata.env"
DERIVED_DATA_LOCK_ROOT="/tmp/codex-derived-data-locks/$LOCK_KEY"
SEED_LOCK_DIR="$DERIVED_DATA_LOCK_ROOT/$DERIVED_DATA_SLOT_ID.seed.lockdir"
SLOT_LOCK_DIR="$DERIVED_DATA_LOCK_ROOT/$DERIVED_DATA_SLOT_ID.slot.lockdir"
DESTINATION_LOCK_ROOT="/tmp/codex-xcodebuild-locks/$LOCK_KEY"
TARGET_CACHE_STEM="$(target_cache_stem)"
CURRENT_XCODE_VERSION_HASH="$(current_xcode_version_hash)"
DERIVED_DATA_SEED_SOURCE='pending'
EFFECTIVE_DERIVED_DATA_MODE="$DERIVED_DATA_MODE"

mkdir -p "$LOG_DIR" "$DERIVED_DATA_ROOT" "$DERIVED_DATA_LOCK_ROOT" "$DESTINATION_LOCK_ROOT"

if [[ "$DERIVED_DATA_MODE" != 'system-serial' ]]; then
  if ! prepare_isolated_derived_data; then
    if [[ "$DERIVED_DATA_MODE" == 'isolated-preferred' ]]; then
      echo "[codex_verify] isolated DerivedData setup failed; falling back to system-serial" >&2
      EFFECTIVE_DERIVED_DATA_MODE='system-serial'
    else
      die "isolated DerivedData setup failed in isolated-required mode"
    fi
  fi
fi

COMMAND_STATUS=0
if [[ "$EFFECTIVE_DERIVED_DATA_MODE" == 'system-serial' ]]; then
  execute_system_serial_mode
else
  if ! execute_isolated_mode; then
    COMMAND_STATUS=$?
    if [[ "$DERIVED_DATA_MODE" == 'isolated-preferred' ]] && log_contains_build_db_lock; then
      echo "[codex_verify] isolated validation hit build.db lock signature; retrying once with system-serial mode" >&2
      EFFECTIVE_DERIVED_DATA_MODE='system-serial'
      COMMAND_STATUS=0
      execute_system_serial_mode || COMMAND_STATUS=$?
    fi
  fi
fi

echo "[codex_verify] finished status=$COMMAND_STATUS log_file=$LOG_FILE" >&2
exit "$COMMAND_STATUS"
