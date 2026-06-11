#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./codex_verify.sh -- <xcodebuild args...>
  ./codex_verify.sh --repo-root <repo-root> -- <xcodebuild args...>
  ./codex_verify.sh --build-check <build-check.sh> <repo-root> [build-check args...]
  ./codex_verify.sh --queue-status
  ~/.codex/bin/codex_verify --repo-root <repo-root> -- <xcodebuild args...>

Purpose:
  Route local project-environment validation into a shared build-queue daemon.
  The daemon executes queued jobs one by one and always uses the system
  DerivedData root: ~/Library/Developer/Xcode/DerivedData

Recommended:
  - Preferred: keep this script in the target Xcode project root as ./codex_verify.sh
  - Fallback: install it globally as ~/.codex/bin/codex_verify
  - Ask all agents to use one of the two entrypoints instead of裸跑 xcodebuild
  - Let iOSAgentSkills verify-ios-build delegate into the project wrapper first,
    then fall back to the global wrapper automatically

Notes:
  - Legacy public overrides XCODE_DERIVED_DATA_MODE / XCODE_DERIVED_DATA_SEED_MODE /
    XCODE_DERIVED_DATA_REFRESH / CODEX_DERIVED_DATA_SLOT are no longer supported.
  - The build-queue daemon is started automatically on first use.
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
    value='unknown'
  fi
  printf '%s' "$value"
}

queue_root() {
  printf '%s' "${CODEX_BUILD_QUEUE_ROOT:-/tmp/codex-build-queue}"
}

job_state() {
  local job_dir="$1"
  if [[ -f "$job_dir/state" ]]; then
    cat "$job_dir/state"
  else
    printf '%s' 'queued'
  fi
}

set_job_state() {
  local job_dir="$1"
  local state="$2"
  printf '%s\n' "$state" >"$job_dir/state"
}

write_text_file() {
  local target="$1"
  local body="$2"
  printf '%s\n' "$body" >"$target"
}

write_args_file() {
  local target="$1"
  shift
  : >"$target"
  while [[ $# -gt 0 ]]; do
    printf '%s\0' "$1" >>"$target"
    shift
  done
}

READ_ARGS_RESULT=()
read_args_file() {
  local target="$1"
  local value=''
  READ_ARGS_RESULT=()
  while IFS= read -r -d '' value; do
    READ_ARGS_RESULT+=("$value")
  done <"$target"
}

append_log_line() {
  local target="$1"
  local line="$2"
  printf '%s\n' "$line" >>"$target"
}

file_mtime_seconds() {
  local target="$1"
  stat -f %m "$target" 2>/dev/null || echo 0
}

daemon_pid() {
  [[ -f "$DAEMON_PID_FILE" ]] || return 0
  tr -d '\n' <"$DAEMON_PID_FILE"
}

daemon_running() {
  local pid
  pid="$(daemon_pid)"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null
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

assert_no_legacy_derived_data_settings() {
  local key value
  for key in \
    XCODE_DERIVED_DATA_MODE \
    XCODE_DERIVED_DATA_SEED_MODE \
    XCODE_DERIVED_DATA_REFRESH \
    CODEX_DERIVED_DATA_SLOT
  do
    value="$(env_or_file_value "$key")"
    if [[ -n "$value" ]]; then
      die "legacy $key is no longer supported; build-queue daemon now always uses $SYSTEM_DERIVED_DATA_HOME. Remove $key from environment or $XCODE_ENV_FILE"
    fi
  done
}

build_owner_body() {
  cat <<EOF
pid=$$
user=${USER:-unknown}
host=$(hostname -s 2>/dev/null || hostname)
repo_root=$REPO_ROOT
mode=$MODE
workspace=${META_WORKSPACE}
project=${META_PROJECT}
scheme=${META_SCHEME}
configuration=${META_CONFIGURATION}
destination=${META_DESTINATION}
action=${META_ACTION}
derived_data_path=$SYSTEM_DERIVED_DATA_HOME
submitted_at=$(timestamp_now)
command=$COMMAND_PREVIEW
wrapper=$(resolve_path "${BASH_SOURCE[0]}")
EOF
}

queue_start_lock_is_stale() {
  [[ -d "$START_LOCK_DIR" ]] || return 1
  local owner_pid owner_file waited now age
  owner_file="$START_LOCK_DIR/owner.pid"
  owner_pid=''
  if [[ -f "$owner_file" ]]; then
    owner_pid="$(tr -d '\n' <"$owner_file")"
  fi
  if [[ -n "$owner_pid" ]] && kill -0 "$owner_pid" 2>/dev/null; then
    return 1
  fi
  now="$(seconds_now)"
  age=$(( now - $(file_mtime_seconds "$START_LOCK_DIR") ))
  [[ $age -ge 15 ]]
}

acquire_start_lock() {
  mkdir -p "$QUEUE_ROOT"
  while ! mkdir "$START_LOCK_DIR" 2>/dev/null; do
    if queue_start_lock_is_stale; then
      rm -rf "$START_LOCK_DIR"
      continue
    fi
    if daemon_running; then
      return 1
    fi
    sleep 1
  done
  printf '%s\n' "$$" >"$START_LOCK_DIR/owner.pid"
  return 0
}

release_start_lock() {
  rm -rf "$START_LOCK_DIR"
}

ensure_daemon_running() {
  local daemon_pid_value start_pid started_at
  mkdir -p "$QUEUE_ROOT" "$JOBS_DIR"
  if daemon_running; then
    return 0
  fi

  if ! acquire_start_lock; then
    return 0
  fi

  if daemon_running; then
    release_start_lock
    return 0
  fi

  started_at="$(timestamp_now)"
  nohup bash "$SCRIPT_PATH" --daemon >>"$DAEMON_STDOUT_LOG" 2>&1 &
  start_pid=$!

  local waited=0
  while [[ $waited -lt 30 ]]; do
    daemon_pid_value="$(daemon_pid)"
    if [[ -n "$daemon_pid_value" ]] && kill -0 "$daemon_pid_value" 2>/dev/null; then
      release_start_lock
      return 0
    fi
    if ! kill -0 "$start_pid" 2>/dev/null; then
      break
    fi
    sleep 1
    waited=$(( waited + 1 ))
  done

  release_start_lock
  die "failed to start build-queue daemon at $QUEUE_ROOT (started_at=$started_at)"
}

generate_job_id() {
  python3 - "$$" "$RANDOM" <<'PY'
import sys, time

pid = sys.argv[1]
rand = sys.argv[2]
print(f"{time.time_ns()}-{pid}-{rand}")
PY
}

write_env_snapshot() {
  local target="$1"
  local key value
  : >"$target"
  for key in PATH DEVELOPER_DIR LANG LC_ALL; do
    if [[ ${!key+x} == x ]]; then
      printf 'export %s=%q\n' "$key" "${!key}" >>"$target"
    fi
  done
  for key in $(compgen -v | LC_ALL=C sort); do
    case "$key" in
      XCODE_*)
        value="${!key}"
        printf 'export %s=%q\n' "$key" "$value" >>"$target"
        ;;
    esac
  done
}

queue_job() {
  local job_id job_dir owner_body
  job_id="$(generate_job_id)"
  job_dir="$JOBS_DIR/$job_id"
  mkdir -p "$job_dir"

  owner_body="$(build_owner_body)"
  set_job_state "$job_dir" 'queued'
  write_text_file "$job_dir/mode" "$MODE"
  write_text_file "$job_dir/repo_root" "$REPO_ROOT"
  write_text_file "$job_dir/created_at" "$(timestamp_now)"
  write_text_file "$job_dir/created_at_epoch" "$(seconds_now)"
  write_text_file "$job_dir/submitter.txt" "$owner_body"
  write_text_file "$job_dir/workspace" "$META_WORKSPACE"
  write_text_file "$job_dir/project" "$META_PROJECT"
  write_text_file "$job_dir/scheme" "$META_SCHEME"
  write_text_file "$job_dir/configuration" "$META_CONFIGURATION"
  write_text_file "$job_dir/destination" "$META_DESTINATION"
  write_text_file "$job_dir/action" "$META_ACTION"
  write_text_file "$job_dir/command_preview" "$COMMAND_PREVIEW"
  write_text_file "$job_dir/log_path" "$job_dir/job.log"
  write_env_snapshot "$job_dir/env.sh"
  write_args_file "$job_dir/command.args0" "${COMMAND[@]}"

  JOB_ID="$job_id"
  JOB_DIR="$job_dir"
  JOB_LOG_FILE="$job_dir/job.log"
}

job_summary_line() {
  local job_dir="$1"
  local job_id repo_root mode workspace scheme destination state
  job_id="$(basename "$job_dir")"
  repo_root="$(cat "$job_dir/repo_root" 2>/dev/null || printf '%s' '-')"
  mode="$(cat "$job_dir/mode" 2>/dev/null || printf '%s' '-')"
  workspace="$(cat "$job_dir/workspace" 2>/dev/null || printf '%s' '-')"
  scheme="$(cat "$job_dir/scheme" 2>/dev/null || printf '%s' '-')"
  destination="$(cat "$job_dir/destination" 2>/dev/null || printf '%s' '-')"
  state="$(job_state "$job_dir")"
  printf '%s | %s | mode=%s | workspace=%s | scheme=%s | destination=%s | state=%s\n' \
    "$job_id" "$repo_root" "$mode" "$workspace" "$scheme" "$destination" "$state"
}

job_matches_filter() {
  local job_dir="$1"
  if [[ -z "$STATUS_FILTER_REPO_ROOT" ]]; then
    return 0
  fi
  [[ -f "$job_dir/repo_root" ]] || return 1
  [[ "$(cat "$job_dir/repo_root")" == "$STATUS_FILTER_REPO_ROOT" ]]
}

queue_status() {
  local active_job active_summary pending_count

  echo "Queue root: $QUEUE_ROOT"
  if daemon_running; then
    echo "Daemon: running pid=$(daemon_pid)"
  else
    echo "Daemon: not running"
  fi
  echo "DerivedData: system default ($SYSTEM_DERIVED_DATA_HOME)"

  active_job=''
  if [[ -f "$ACTIVE_JOB_FILE" ]]; then
    active_job="$(cat "$ACTIVE_JOB_FILE" 2>/dev/null || true)"
  fi
  if [[ -n "$active_job" && -d "$active_job" ]] && job_matches_filter "$active_job"; then
    active_summary="$(job_summary_line "$active_job")"
    echo "Active:"
    echo "  $active_summary"
    if [[ -f "$active_job/log_path" ]]; then
      echo "  log_file=$(cat "$active_job/log_path")"
    fi
  else
    echo "Active: none"
  fi

  pending_count=0
  echo "Pending:"
  local job_dir
  for job_dir in $(find "$JOBS_DIR" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | LC_ALL=C sort); do
    if [[ "$(job_state "$job_dir")" == 'queued' ]] && job_matches_filter "$job_dir"; then
      pending_count=$(( pending_count + 1 ))
      echo "  $pending_count. $(job_summary_line "$job_dir")"
    fi
  done
  if [[ $pending_count -eq 0 ]]; then
    echo "  none"
  fi
}

queue_position() {
  local target_dir="$1"
  local position=0
  local job_dir
  for job_dir in $(find "$JOBS_DIR" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | LC_ALL=C sort); do
    if [[ "$(job_state "$job_dir")" == 'queued' ]]; then
      position=$(( position + 1 ))
      if [[ "$job_dir" == "$target_dir" ]]; then
        printf '%s' "$position"
        return 0
      fi
    fi
  done
  printf '%s' '0'
}

active_job_summary() {
  if [[ -f "$ACTIVE_JOB_FILE" ]]; then
    local active_job
    active_job="$(cat "$ACTIVE_JOB_FILE" 2>/dev/null || true)"
    if [[ -n "$active_job" && -d "$active_job" ]]; then
      job_summary_line "$active_job"
      return 0
    fi
  fi
  printf '%s' 'none'
}

wait_for_job() {
  local last_notice='' state position active_summary exit_code tail_pid=''
  while true; do
    state="$(job_state "$JOB_DIR")"
    case "$state" in
      queued)
        position="$(queue_position "$JOB_DIR")"
        active_summary="$(active_job_summary)"
        if [[ "$last_notice" != "queued:$position:$active_summary" ]]; then
          echo "[codex_verify] queued job=$JOB_ID position=$position active=$active_summary log_file=$JOB_LOG_FILE" >&2
          last_notice="queued:$position:$active_summary"
        fi
        sleep 1
        ;;
      running)
        if [[ -z "$tail_pid" ]]; then
          echo "[codex_verify] running job=$JOB_ID log_file=$JOB_LOG_FILE derived_data_path=$SYSTEM_DERIVED_DATA_HOME" >&2
          tail -n +1 -F "$JOB_LOG_FILE" 2>/dev/null &
          tail_pid=$!
        fi
        sleep 1
        ;;
      succeeded|failed)
        if [[ -z "$tail_pid" ]]; then
          [[ -f "$JOB_LOG_FILE" ]] && cat "$JOB_LOG_FILE"
        else
          kill "$tail_pid" 2>/dev/null || true
          wait "$tail_pid" 2>/dev/null || true
        fi
        exit_code="$(cat "$JOB_DIR/exit_code" 2>/dev/null || printf '%s' '1')"
        echo "[codex_verify] finished job=$JOB_ID state=$state status=$exit_code log_file=$JOB_LOG_FILE" >&2
        return "$exit_code"
        ;;
      *)
        sleep 1
        ;;
    esac
  done
}

mark_running_jobs_failed_on_recovery() {
  local job_dir
  for job_dir in $(find "$JOBS_DIR" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | LC_ALL=C sort); do
    if [[ "$(job_state "$job_dir")" == 'running' ]]; then
      append_log_line "$job_dir/job.log" "[codex_verify] job interrupted: daemon restarted before completion"
      write_text_file "$job_dir/exit_code" "1"
      write_text_file "$job_dir/finished_at" "$(timestamp_now)"
      set_job_state "$job_dir" 'failed'
    fi
  done
  rm -f "$ACTIVE_JOB_FILE"
}

next_queued_job() {
  local job_dir
  NEXT_QUEUED_JOB=''
  for job_dir in $(find "$JOBS_DIR" -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | LC_ALL=C sort); do
    if [[ "$(job_state "$job_dir")" == 'queued' ]]; then
      NEXT_QUEUED_JOB="$job_dir"
      return 0
    fi
  done
  return 1
}

run_job() {
  local job_dir="$1"
  local repo_root mode started_at status
  local job_id
  job_id="$(basename "$job_dir")"
  repo_root="$(cat "$job_dir/repo_root")"
  mode="$(cat "$job_dir/mode")"
  started_at="$(timestamp_now)"

  set_job_state "$job_dir" 'running'
  write_text_file "$job_dir/started_at" "$started_at"
  write_text_file "$job_dir/runner_pid" "$$"
  write_text_file "$ACTIVE_JOB_FILE" "$job_dir"

  read_args_file "$job_dir/command.args0"
  append_log_line "$job_dir/job.log" "[codex_verify] job_id=$job_id"
  append_log_line "$job_dir/job.log" "[codex_verify] repo_root=$repo_root"
  append_log_line "$job_dir/job.log" "[codex_verify] mode=$mode"
  append_log_line "$job_dir/job.log" "[codex_verify] workspace=$(cat "$job_dir/workspace") project=$(cat "$job_dir/project") scheme=$(cat "$job_dir/scheme") destination=$(cat "$job_dir/destination")"
  append_log_line "$job_dir/job.log" "[codex_verify] action=$(cat "$job_dir/action") configuration=$(cat "$job_dir/configuration")"
  append_log_line "$job_dir/job.log" "[codex_verify] derived_data_path=$SYSTEM_DERIVED_DATA_HOME"
  append_log_line "$job_dir/job.log" "[codex_verify] started_at=$started_at"
  append_log_line "$job_dir/job.log" "[codex_verify] command=$(cat "$job_dir/command_preview")"

  set +e
  (
    cd "$repo_root"
    if [[ -f "$job_dir/env.sh" ]]; then
      # shellcheck source=/dev/null
      source "$job_dir/env.sh"
    fi
    export CODEX_VERIFY_BYPASS_WRAPPER=1
    export CODEX_VERIFY_QUEUE_ROOT="$QUEUE_ROOT"
    unset XCODE_DERIVED_DATA
    "${READ_ARGS_RESULT[@]}"
  ) 2>&1 | tee -a "$job_dir/job.log"
  status=${PIPESTATUS[0]}
  set -e

  write_text_file "$job_dir/exit_code" "$status"
  write_text_file "$job_dir/finished_at" "$(timestamp_now)"
  if [[ $status -eq 0 ]]; then
    set_job_state "$job_dir" 'succeeded'
  else
    set_job_state "$job_dir" 'failed'
  fi
  append_log_line "$job_dir/job.log" "[codex_verify] finished_at=$(cat "$job_dir/finished_at")"
  append_log_line "$job_dir/job.log" "[codex_verify] status=$status"
  rm -f "$ACTIVE_JOB_FILE"
}

daemon_cleanup() {
  local current_pid
  current_pid="$(daemon_pid)"
  if [[ "$current_pid" == "$$" ]]; then
    rm -f "$DAEMON_PID_FILE"
  fi
}

daemon_main() {
  mkdir -p "$QUEUE_ROOT" "$JOBS_DIR"

  if daemon_running; then
    local existing_pid
    existing_pid="$(daemon_pid)"
    if [[ "$existing_pid" != "$$" ]]; then
      exit 0
    fi
  fi

  printf '%s\n' "$$" >"$DAEMON_PID_FILE"
  trap daemon_cleanup EXIT INT TERM HUP

  mark_running_jobs_failed_on_recovery

  while true; do
    if next_queued_job; then
      run_job "$NEXT_QUEUED_JOB"
      continue
    fi
    sleep 1
  done
}

MODE=''
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
    --|--build-check|--queue-status|--daemon|--help|-h)
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
SYSTEM_DERIVED_DATA_HOME="$HOME/Library/Developer/Xcode/DerivedData"
QUEUE_ROOT="$(queue_root)"
JOBS_DIR="$QUEUE_ROOT/jobs"
DAEMON_PID_FILE="$QUEUE_ROOT/daemon.pid"
DAEMON_STDOUT_LOG="$QUEUE_ROOT/daemon.log"
ACTIVE_JOB_FILE="$QUEUE_ROOT/active_job"
START_LOCK_DIR="$QUEUE_ROOT/start.lockdir"
STATUS_FILTER_REPO_ROOT=''

case "${1:-}" in
  --)
    shift
    [[ $# -gt 0 ]] || die "missing xcodebuild arguments after --"
    MODE='xcodebuild'
    RAW_ARGS=("$@")
    if [[ "${RAW_ARGS[0]}" == 'xcodebuild' ]]; then
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
    REPO_ROOT="$BUILD_CHECK_ROOT"
    XCODE_ENV_FILE="$REPO_ROOT/.codex/xcodebuild.env"
    COMMAND=(bash "$BUILD_CHECK_SCRIPT" "$BUILD_CHECK_ROOT" "$@")
    ;;
  --queue-status)
    MODE='queue-status'
    COMMAND=()
    if [[ -n "$USER_REPO_ROOT" || "$(basename "$SCRIPT_PATH")" == 'codex_verify.sh' ]]; then
      STATUS_FILTER_REPO_ROOT="$REPO_ROOT"
    fi
    ;;
  --daemon)
    MODE='daemon'
    COMMAND=()
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

if [[ "$MODE" == 'daemon' ]]; then
  daemon_main
  exit 0
fi

assert_no_legacy_derived_data_settings

if [[ "$MODE" == 'queue-status' ]]; then
  queue_status
  exit 0
fi

COMMAND_PREVIEW="$(join_quoted_command "${COMMAND[@]}")"

queue_job
ensure_daemon_running
wait_for_job
exit $?
