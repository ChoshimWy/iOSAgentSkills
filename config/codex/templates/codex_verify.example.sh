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
  - Let iOSAgentSkills ios-verification delegate into the project wrapper first,
    then fall back to the global wrapper automatically

Notes:
  - Legacy public overrides XCODE_DERIVED_DATA_MODE / XCODE_DERIVED_DATA_SEED_MODE /
    XCODE_DERIVED_DATA_REFRESH / CODEX_DERIVED_DATA_SLOT are no longer supported.
  - The build-queue daemon is started automatically on first use.
  - The wrapper prints a compact agent-summary.json by default. Set
    CODEX_VERIFY_STREAM_LOG=1 only when raw log streaming is explicitly needed.
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

resolve_digest_script() {
  local candidate
  for candidate in \
    "${CODEX_XCODEBUILD_DIGEST_SCRIPT:-}" \
    "$REPO_ROOT/tools/digest-xcodebuild-log.sh" \
    "$SCRIPT_DIR/digest-xcodebuild-log" \
    "$SCRIPT_DIR/digest-xcodebuild-log.sh" \
    "$HOME/.codex/bin/digest-xcodebuild-log"
  do
    [[ -n "$candidate" ]] || continue
    if [[ -f "$candidate" ]]; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  return 1
}

write_minimal_verification_report() {
  local job_dir="$1"
  local status="$2"
  python3 - "$job_dir" "$status" <<'PY'
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

job_dir = Path(sys.argv[1])
status_code = int(sys.argv[2])
raw_log = job_dir / "job.log"
diagnostics_path = job_dir / "diagnostics.json"
summary_path = job_dir / "build-summary.txt"
report_path = job_dir / "verification-report.json"

text = raw_log.read_text(encoding="utf-8", errors="replace") if raw_log.exists() else ""
fingerprint = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
state = "passed" if status_code == 0 else "failed"
summary = "Verification succeeded." if status_code == 0 else "Verification failed; no digest script was available, inspect build-summary.txt before raw logs."
generated_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

diagnostics = {
    "status": state,
    "mode": (job_dir / "mode").read_text().strip() if (job_dir / "mode").exists() else "auto",
    "fingerprint": fingerprint,
    "cached": False,
    "summary": summary,
    "finished_at": generated_at,
    "diagnostics": [],
    "first_blocking_error": None,
    "failed_tests": [],
    "warnings_count": 0,
    "artifacts": {
        "diagnostics_json": str(diagnostics_path),
        "build_summary": str(summary_path),
        "verification_report": str(report_path),
        "raw_log": str(raw_log),
    },
    "next_action": "Read build-summary.txt. Only inspect the raw log if compact evidence is insufficient.",
    "raw_log_policy": "forbidden_by_default",
    "needs_raw_log": status_code != 0,
}
diagnostics_path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
summary_path.write_text(summary + "\n", encoding="utf-8")
report = {
    "status": state,
    "mode": diagnostics["mode"],
    "fingerprint": fingerprint,
    "cached": False,
    "summary": summary,
    "first_blocking_error": None,
    "failed_tests": [],
    "warnings_count": 0,
    "artifact_paths": diagnostics["artifacts"],
    "suggested_next_action": diagnostics["next_action"],
    "raw_log_policy": "forbidden_by_default",
    "needs_raw_log": status_code != 0,
    "generated_at": generated_at,
}
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

write_agent_summary() {
  local job_dir="$1"
  python3 - "$job_dir" <<'PY'
from __future__ import annotations

import json
import re
import shlex
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

job_dir = Path(sys.argv[1])
report_path = job_dir / "verification-report.json"
summary_path = job_dir / "agent-summary.json"


def read_text(name: str) -> str:
    path = job_dir / name
    return path.read_text(encoding="utf-8", errors="replace").strip() if path.exists() else ""


def load_report() -> dict:
    if not report_path.exists():
        return {
            "status": "blocked",
            "summary": "verification-report.json missing",
            "artifact_paths": {"raw_log": str(job_dir / "job.log")},
            "needs_raw_log": False,
        }
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": "blocked",
            "summary": f"verification-report.json unreadable: {exc}",
            "artifact_paths": {"verification_report": str(report_path), "raw_log": str(job_dir / "job.log")},
            "needs_raw_log": False,
        }


def extract_only_testing(command_preview: str) -> list[str]:
    try:
        parts = shlex.split(command_preview)
    except ValueError:
        parts = command_preview.split()
    selectors: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part.startswith("-only-testing:"):
            selector = part.split(":", 1)[1]
            if selector:
                selectors.append(selector)
        elif part == "-only-testing" and index + 1 < len(parts):
            selectors.append(parts[index + 1])
            index += 1
        index += 1
    return selectors


def destination_type(destination: str) -> str:
    normalized = destination.lower()
    if not normalized:
        return "unknown"
    if "simulator" in normalized:
        return "simulator"
    if "generic/platform=ios" in normalized:
        return "generic_ios"
    if normalized.startswith("id="):
        return "physical_device"
    if "macos" in normalized:
        return "macos"
    return "unknown"


def verification_level(action: str, only_testing: list[str], report: dict) -> str:
    ui_smoke = report.get("ui_smoke")
    if isinstance(ui_smoke, dict) and ui_smoke.get("executed"):
        return "ui"
    if only_testing:
        return "unit"
    normalized = action.lower()
    if normalized in {"test", "test-without-building"}:
        return "unit"
    if normalized in {"archive", "exportarchive"}:
        return "full"
    return "build"


def non_auto(value: object) -> str:
    text = str(value or "").strip()
    return "" if text in {"", "auto", "Debug(auto)", "build(auto)"} else text


def workspace_candidates(repo_root: Path) -> list[Path]:
    return sorted(
        path
        for path in repo_root.rglob("*.xcworkspace")
        if "Pods" not in path.parts
        and "project.xcworkspace" not in str(path)
        and len(path.relative_to(repo_root).parts) <= 3
    )


def project_candidates(repo_root: Path) -> list[Path]:
    return sorted(
        path
        for path in repo_root.rglob("*.xcodeproj")
        if "Pods" not in path.parts and len(path.relative_to(repo_root).parts) <= 3
    )


def scheme_paths(repo_root: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for path in sorted(repo_root.rglob("*.xcscheme")):
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
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return []
    names: list[str] = []
    for reference in root.findall(".//TestAction//TestableReference//BuildableReference"):
        for key in ("BuildableName", "BlueprintName"):
            value = reference.get(key)
            if value:
                name = Path(value).stem
                if name not in names:
                    names.append(name)
    return names


def scheme_has_unit_tests(path: Path | None) -> bool:
    return any(is_unit_test_name(name) for name in iter_scheme_testables(path))


def scheme_has_ui_tests(path: Path | None) -> bool:
    return any(is_ui_test_name(name) for name in iter_scheme_testables(path))


def scheme_reason(name: str, path: Path | None, source: str) -> str:
    if source == "xcodebuild-args-or-env":
        return "metadata captured by codex_verify wrapper"
    if scheme_has_unit_tests(path):
        return "scheme has unit test binding"
    if is_unit_test_name(name):
        return "scheme name matches unit test pattern"
    if is_generic_test_scheme(name):
        return "scheme name matches generic test pattern"
    if scheme_has_ui_tests(path):
        return "scheme has UI test binding"
    if is_ui_test_name(name):
        return "scheme name matches UI test pattern"
    return "fallback shared scheme"


def scheme_sort_key(name: str, path: Path | None) -> tuple[int, str]:
    if scheme_has_unit_tests(path):
        return (0, name.lower())
    if is_unit_test_name(name):
        return (1, name.lower())
    if is_generic_test_scheme(name):
        return (2, name.lower())
    if scheme_has_ui_tests(path):
        return (3, name.lower())
    if is_ui_test_name(name):
        return (4, name.lower())
    return (5, name.lower())


def fallback_project_selection(repo_root: Path, workspace: str, project: str) -> dict:
    workspaces = workspace_candidates(repo_root)
    projects = project_candidates(repo_root)
    if workspace:
        value = workspace
        source = "xcodebuild-args-or-env"
        reason = "metadata captured by codex_verify wrapper"
    elif workspaces:
        value = str(workspaces[0].relative_to(repo_root))
        source = "auto_discovered"
        reason = ".xcworkspace preferred over .xcodeproj" if projects else ".xcworkspace auto discovered"
    else:
        value = project or (str(projects[0].relative_to(repo_root)) if projects else None)
        source = "xcodebuild-args-or-env" if project else "auto_discovered"
        reason = "metadata captured by codex_verify wrapper" if project else "no .xcworkspace found; using .xcodeproj"
    return {
        "type": "workspace" if value and str(value).endswith(".xcworkspace") else "project",
        "value": value,
        "source": source,
        "reason": reason,
        "workspace_candidates": [str(path.relative_to(repo_root)) for path in workspaces],
        "project_candidates": [str(path.relative_to(repo_root)) for path in projects],
    }


def fallback_scheme_selection(repo_root: Path, scheme: str) -> dict:
    paths = scheme_paths(repo_root)
    selected = scheme
    source = "xcodebuild-args-or-env" if selected else "auto_discovered"
    if not selected and paths:
        selected = sorted(paths.keys(), key=lambda name: scheme_sort_key(name, paths.get(name)))[0]
    selected_path = paths.get(selected)
    testables = iter_scheme_testables(selected_path)
    return {
        "scheme": selected,
        "source": source,
        "reason": scheme_reason(selected, selected_path, source) if selected else "no shared scheme metadata available",
        "testables": testables,
        "has_unit_tests": any(is_unit_test_name(name) for name in testables),
        "has_ui_tests": any(is_ui_test_name(name) for name in testables),
        "scheme_path": str(selected_path.relative_to(repo_root)) if selected_path else None,
        "candidate_schemes": sorted(paths.keys()),
    }


report = load_report()
command_preview = read_text("command_preview")
only_testing = report.get("only_testing") or extract_only_testing(command_preview)
destination = read_text("destination")
baseline = report.get("baseline") if isinstance(report.get("baseline"), dict) else {}
project_selection = report.get("project_selection") if isinstance(report.get("project_selection"), dict) else None
scheme_selection = report.get("scheme_selection") if isinstance(report.get("scheme_selection"), dict) else None
repo_root = Path(non_auto(read_text("repo_root")) or ".").resolve()
metadata_workspace = non_auto(read_text("workspace"))
metadata_project = non_auto(read_text("project"))
metadata_scheme = non_auto(read_text("scheme"))
workspace_or_project = metadata_workspace or metadata_project or non_auto(baseline.get("workspace_or_project")) or (
    project_selection.get("value") if project_selection else None
)
scheme = metadata_scheme or non_auto(baseline.get("scheme")) or (
    scheme_selection.get("scheme") if scheme_selection else None
)
effective_project_selection = project_selection or fallback_project_selection(repo_root, metadata_workspace, metadata_project)
effective_scheme_selection = scheme_selection or fallback_scheme_selection(repo_root, metadata_scheme)
workspace_or_project = workspace_or_project or effective_project_selection.get("value")
scheme = scheme or effective_scheme_selection.get("scheme")
configuration = non_auto(read_text("configuration")) or non_auto(baseline.get("configuration")) or "Debug"
action = non_auto(read_text("action")) or non_auto(baseline.get("action")) or str(report.get("mode") or "build")
artifact_paths = report.get("artifact_paths") if isinstance(report.get("artifact_paths"), dict) else {}
artifact_paths = {
    **artifact_paths,
    "agent_summary": str(summary_path),
    "verification_report": str(report_path),
    "diagnostics_json": str(job_dir / "diagnostics.json"),
    "build_summary": str(job_dir / "build-summary.txt"),
    "raw_log": str(job_dir / "job.log"),
}

summary = {
    "schema_version": 1,
    "producer": "codex_verify_agent_summary",
    "status": report.get("status", "unknown"),
    "verification_level": verification_level(read_text("action") or str(report.get("mode", "")), list(only_testing), report),
    "route": "codex_verify -> build-queue daemon -> xcodebuild",
    "repo_root": str(repo_root),
    "workspace_or_project": workspace_or_project,
    "project_selection": effective_project_selection,
    "scheme": scheme,
    "scheme_selection": effective_scheme_selection,
    "configuration": configuration,
    "action": action,
    "destination": {
        "type": baseline.get("destination_type") or destination_type(destination or str(baseline.get("destination", ""))),
        "value": destination or baseline.get("destination"),
        "selected_device_reason": baseline.get("selected_device_reason"),
    },
    "only_testing": list(only_testing),
    "executed_command": command_preview,
    "executed_commands": [command_preview] if command_preview else [],
    "queue_job_id": job_dir.name,
    "queue_job_dir": str(job_dir),
    "fingerprint": report.get("fingerprint"),
    "cached": report.get("cached", False),
    "summary": report.get("summary"),
    "first_blocking_error": report.get("first_blocking_error"),
    "failed_tests": report.get("failed_tests", []),
    "warnings_count": report.get("warnings_count", 0),
    "ui_smoke": report.get("ui_smoke"),
    "artifact_paths": artifact_paths,
    "raw_log_policy": report.get("raw_log_policy", "forbidden_by_default"),
    "needs_raw_log": report.get("needs_raw_log", False),
    "next_action": report.get("suggested_next_action") or report.get("next_action"),
}
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

generate_verification_artifacts() {
  local job_dir="$1"
  local status="$2"
  local digest_script=''
  local diagnostics_path="$job_dir/diagnostics.json"
  local summary_path="$job_dir/build-summary.txt"
  local report_path="$job_dir/verification-report.json"

  if digest_script="$(resolve_digest_script)"; then
    CODEX_VERIFY_MODE="$(cat "$job_dir/mode" 2>/dev/null || printf '%s' auto)" \
      bash "$digest_script" "$job_dir/job.log" "$diagnostics_path" "$summary_path" "$report_path" \
      >"$job_dir/digest.log" 2>&1 || true
  fi

  if [[ ! -f "$report_path" ]]; then
    write_minimal_verification_report "$job_dir" "$status"
  fi
  write_agent_summary "$job_dir"

  write_text_file "$job_dir/diagnostics_path" "$diagnostics_path"
  write_text_file "$job_dir/build_summary_path" "$summary_path"
  write_text_file "$job_dir/verification_report_path" "$report_path"
  write_text_file "$job_dir/agent_summary_path" "$job_dir/agent-summary.json"
  write_text_file "$QUEUE_ROOT/latest_job" "$job_dir"
  write_text_file "$QUEUE_ROOT/latest_verification_report" "$report_path"
  write_text_file "$QUEUE_ROOT/latest_agent_summary" "$job_dir/agent-summary.json"
}

print_verification_report() {
  local job_dir="$1"
  local summary_path="$job_dir/agent-summary.json"
  if [[ -f "$summary_path" ]]; then
    cat "$summary_path"
  else
    echo "{\"status\":\"blocked\",\"summary\":\"agent-summary.json missing\",\"artifact_paths\":{\"raw_log\":\"$job_dir/job.log\"},\"needs_raw_log\":false}"
  fi
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
        if [[ -z "$last_notice" || "$last_notice" != "running" ]]; then
          echo "[codex_verify] running job=$JOB_ID log_file=$JOB_LOG_FILE derived_data_path=$SYSTEM_DERIVED_DATA_HOME" >&2
          last_notice="running"
        fi
        if [[ "${CODEX_VERIFY_STREAM_LOG:-0}" == '1' && -z "$tail_pid" ]]; then
          tail -n +1 -F "$JOB_LOG_FILE" 2>/dev/null &
          tail_pid=$!
        fi
        sleep 1
        ;;
      succeeded|failed)
        if [[ -n "$tail_pid" ]]; then
          kill "$tail_pid" 2>/dev/null || true
          wait "$tail_pid" 2>/dev/null || true
        fi
        exit_code="$(cat "$JOB_DIR/exit_code" 2>/dev/null || printf '%s' '1')"
        print_verification_report "$JOB_DIR"
        echo "[codex_verify] finished job=$JOB_ID state=$state status=$exit_code agent_summary=$JOB_DIR/agent-summary.json report=$JOB_DIR/verification-report.json log_file=$JOB_LOG_FILE" >&2
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
    export CODEX_VERIFY_JOB_ID="$job_id"
    export CODEX_VERIFY_JOB_DIR="$job_dir"
    unset XCODE_DERIVED_DATA
    "${READ_ARGS_RESULT[@]}"
  ) 2>&1 | tee -a "$job_dir/job.log"
  status=${PIPESTATUS[0]}
  set -e

  write_text_file "$job_dir/exit_code" "$status"
  write_text_file "$job_dir/finished_at" "$(timestamp_now)"
  append_log_line "$job_dir/job.log" "[codex_verify] finished_at=$(cat "$job_dir/finished_at")"
  append_log_line "$job_dir/job.log" "[codex_verify] status=$status"
  generate_verification_artifacts "$job_dir" "$status"
  if [[ $status -eq 0 ]]; then
    set_job_state "$job_dir" 'succeeded'
  else
    set_job_state "$job_dir" 'failed'
  fi
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
