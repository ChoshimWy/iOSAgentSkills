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
  Serialize local project-environment validation so multiple Codex/Claude CLI
  sessions do not run xcodebuild concurrently against the same Xcode project.

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

join_quoted_command() {
  local out=''
  local part
  for part in "$@"; do
    out+=$(printf '%q ' "$part")
  done
  printf '%s' "$out" | trim_trailing_space
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
      build|test|archive|analyze|clean)
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

summarize_owner() {
  [[ -f "$OWNER_FILE" ]] || return 0
  awk 'NF { print }' "$OWNER_FILE" | paste -sd '; ' -
}

write_owner_file() {
  cat >"$OWNER_FILE" <<EOF
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
started_at=$(timestamp_now)
command=$COMMAND_PREVIEW
log_file=$LOG_FILE
EOF
}

cleanup_owner_file() {
  rm -f "$OWNER_FILE"
  if [[ "$LOCK_BACKEND" == 'shlock' ]]; then
    rm -f "$LOCK_FILE"
  fi
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

if [[ "$MODE" == 'build-check' ]]; then
  if [[ "${META_WORKSPACE}" != 'auto' ]]; then
    LOCK_BASIS="$(resolve_repo_member_path "$META_WORKSPACE")"
  elif [[ "${META_PROJECT}" != 'auto' ]]; then
    LOCK_BASIS="$(resolve_repo_member_path "$META_PROJECT")"
  else
    LOCK_BASIS="$REPO_ROOT"
  fi
else
  if [[ -n "${META_WORKSPACE}" && "${META_WORKSPACE}" != 'auto' ]]; then
    LOCK_BASIS="$(resolve_repo_member_path "$META_WORKSPACE")"
  elif [[ -n "${META_PROJECT}" && "${META_PROJECT}" != 'auto' ]]; then
    LOCK_BASIS="$(resolve_repo_member_path "$META_PROJECT")"
  else
    LOCK_BASIS="$REPO_ROOT"
  fi
fi

LOCK_KEY="$(printf '%s' "$LOCK_BASIS" | shasum -a 256 | awk '{print $1}')"
LOCK_DIR="/tmp/codex-xcodebuild-locks/$LOCK_KEY"
LOCK_FILE="$LOCK_DIR/project.lock"
OWNER_FILE="$LOCK_DIR/owner.txt"
LOG_DIR="/tmp/codex-verify/$LOCK_KEY"
RUN_TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
LOG_FILE="$LOG_DIR/$RUN_TIMESTAMP.log"
COMMAND_PREVIEW="$(join_quoted_command "${COMMAND[@]}")"

mkdir -p "$LOCK_DIR" "$LOG_DIR"

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

trap cleanup_owner_file EXIT INT TERM HUP
write_owner_file

echo "[codex_verify] acquired validation lock" >&2
echo "[codex_verify] repo_root=$REPO_ROOT" >&2
echo "[codex_verify] lock_basis=$LOCK_BASIS" >&2
echo "[codex_verify] workspace=${META_WORKSPACE} project=${META_PROJECT} scheme=${META_SCHEME} destination=${META_DESTINATION}" >&2
echo "[codex_verify] action=${META_ACTION} configuration=${META_CONFIGURATION}" >&2
echo "[codex_verify] log_file=$LOG_FILE" >&2

cd "$REPO_ROOT"

set +e
if [[ "$MODE" == 'build-check' ]]; then
  CODEX_VERIFY_BYPASS_WRAPPER=1 "${COMMAND[@]}" 2>&1 | tee "$LOG_FILE"
else
  "${COMMAND[@]}" 2>&1 | tee "$LOG_FILE"
fi
COMMAND_STATUS=${PIPESTATUS[0]}
set -e

echo "[codex_verify] finished status=$COMMAND_STATUS log_file=$LOG_FILE" >&2
exit "$COMMAND_STATUS"
