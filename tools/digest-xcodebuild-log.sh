#!/usr/bin/env bash
set -euo pipefail

# Convert a raw xcodebuild log into compact diagnostics.json, build-summary.txt,
# and verification-report.json. Agents should read verification-report.json first
# and avoid the raw log by default.
#
# Usage:
#   tools/digest-xcodebuild-log.sh build.log diagnostics.json build-summary.txt verification-report.json
#
# Inputs:
#   $1 raw xcodebuild log path, default: build.log
#   $2 diagnostics output path, default: diagnostics.json
#   $3 summary output path, default: build-summary.txt
#   $4 verification report output path, default: verification-report.json

LOG_FILE="${1:-build.log}"
OUT_JSON="${2:-diagnostics.json}"
OUT_SUMMARY="${3:-build-summary.txt}"
OUT_REPORT="${4:-verification-report.json}"

if [[ ! -f "$LOG_FILE" ]]; then
  mkdir -p "$(dirname "$OUT_JSON")" "$(dirname "$OUT_SUMMARY")" "$(dirname "$OUT_REPORT")"
  printf '{\n  "status": "error",\n  "summary": "Log file not found",\n  "diagnostics": [],\n  "next_action": "Check the build-queue output path.",\n  "raw_log_policy": "forbidden_by_default"\n}\n' > "$OUT_JSON"
  printf '{\n  "status": "blocked",\n  "summary": "Log file not found",\n  "artifact_paths": {"diagnostics_json": "%s", "build_summary": "%s", "raw_log": "%s"},\n  "suggested_next_action": "Check the build-queue output path.",\n  "needs_raw_log": false\n}\n' "$OUT_JSON" "$OUT_SUMMARY" "$LOG_FILE" > "$OUT_REPORT"
  printf 'Log file not found: %s\n' "$LOG_FILE" > "$OUT_SUMMARY"
  exit 1
fi

mkdir -p "$(dirname "$OUT_JSON")" "$(dirname "$OUT_SUMMARY")" "$(dirname "$OUT_REPORT")"

# Keep only a compact set of actionable lines. This summary is intentionally small.
grep -nE \
  "error:|fatal error:|warning:|Command SwiftCompile failed|Command CompileSwift failed|Undefined symbol|No such module|cannot find|does not conform|failed to build module|Provisioning profile|CodeSign|Signing|The operation couldn.t be completed|xcodebuild: error:|Testing failed|Test Case .* failed|Executed .* tests" \
  "$LOG_FILE" \
  | head -n 200 > "$OUT_SUMMARY" || true

python3 - "$LOG_FILE" "$OUT_JSON" "$OUT_SUMMARY" "$OUT_REPORT" <<'PY'
import datetime as _dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

log_path = Path(sys.argv[1])
out_json = Path(sys.argv[2])
out_summary = Path(sys.argv[3])
out_report = Path(sys.argv[4])

text = log_path.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()

raw_exit_code = os.environ.get("CODEX_VERIFY_EXIT_CODE") or os.environ.get("CODEX_VERIFY_STATUS")
try:
    xcodebuild_exit_code = int(raw_exit_code) if raw_exit_code not in (None, "") else None
except ValueError:
    xcodebuild_exit_code = None

patterns = [
    (
        "workspace_path_error",
        re.compile(
            r"is not a workspace file|contents\.xcworkspacedata|Unable to open workspace|workspace .* cannot be opened",
            re.I,
        ),
    ),
    (
        "simulator_service_unavailable",
        re.compile(
            r"CoreSimulator|simdiskimaged|CoreDeviceService|Failed to boot simulator|Unable to boot.*Simulator",
            re.I,
        ),
    ),
    (
        "destination_unavailable",
        re.compile(
            r"Unable to find a destination|destination specifier|No available destinations|Unable to locate a destination",
            re.I,
        ),
    ),
    ("project_config_error", re.compile(r"The project .* cannot be opened|Unable to open project|scheme .* is not currently configured|does not contain a scheme", re.I)),
    ("missing_module", re.compile(r"No such module '([^']+)'|failed to build module '([^']+)'", re.I)),
    ("missing_dependency", re.compile(r"package .* is required|Could not resolve package dependencies|Unable to find a specification", re.I)),
    ("swift_compile_error", re.compile(r"(?P<file>[^:\n]+\.swift):(?P<line>\d+):(?P<column>\d+):\s*error:\s*(?P<msg>.*)")),
    ("objc_compile_error", re.compile(r"(?P<file>[^:\n]+\.(?:m|mm|h|hpp|cpp|c)):?(?P<line>\d+)?:?(?P<column>\d+)?:?\s*error:\s*(?P<msg>.*)")),
    ("linker_error", re.compile(r"Undefined symbol|duplicate symbol|ld: .*error|clang: error: linker command failed", re.I)),
    ("signing_error", re.compile(r"Provisioning profile|CodeSign|Signing for .* requires a development team|No profiles for", re.I)),
    ("destination_error", re.compile(r"destination specifier|destination .*not|device .*not|No devices are available", re.I)),
    ("test_failure", re.compile(r"Test Case .* failed|XCTAssert|Testing failed", re.I)),
    ("xcodebuild_error", re.compile(r"xcodebuild: error:", re.I)),
]

# Fallback generic error patterns are intentionally later so structured compiler errors win.
generic_error = re.compile(r"\berror:\s*(?P<msg>.*)", re.I)

priority = {
    "workspace_path_error": 0,
    "simulator_service_unavailable": 1,
    "destination_unavailable": 2,
    "project_config_error": 3,
    "missing_dependency": 4,
    "missing_module": 5,
    "swift_compile_error": 6,
    "objc_compile_error": 7,
    "linker_error": 8,
    "signing_error": 9,
    "destination_error": 10,
    "test_failure": 11,
    "xcodebuild_error": 12,
    "unknown": 99,
}

failure_domain = {
    "workspace_path_error": "env_issue",
    "simulator_service_unavailable": "env_issue",
    "destination_unavailable": "env_issue",
    "destination_error": "env_issue",
    "xcodebuild_error": "env_issue",
    "project_config_error": "project_config",
    "missing_dependency": "dependency",
    "missing_module": "dependency",
    "swift_compile_error": "code",
    "objc_compile_error": "code",
    "linker_error": "code",
    "signing_error": "signing",
    "test_failure": "test",
    "unknown": "unknown",
}

env_issue_kinds = {
    "workspace_path_error",
    "simulator_service_unavailable",
    "destination_unavailable",
    "destination_error",
}

non_blocking_noise_patterns = [
    # Xcode CLI may scan stale/corrupt local provisioning profile cache even when
    # actions like `-showdestinations` or `-list` complete successfully. These
    # DVTProvisioningProfileManager lines are environment noise unless the
    # underlying xcodebuild command exits non-zero with a real signing blocker.
    re.compile(
        r"DVTProvisioningProfileManager: Failed to load profile .*Profile is missing the required UUID property",
        re.I,
    ),
]

def is_non_blocking_noise(line: str) -> bool:
    return any(pattern.search(line) for pattern in non_blocking_noise_patterns)

def compact_excerpt(index: int, radius: int = 1) -> str:
    start = max(index - radius, 0)
    end = min(index + radius + 1, len(lines))
    return "\n".join(lines[start:end])[:1200]

def normalize_file(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    # Remove common prefixes from xcodebuild log formatting.
    value = re.sub(r"^.*?(/[^\s]+\.swift)$", r"\1", value)
    return value

items = []
failed_tests = []
warning_count = 0

failed_test_pattern = re.compile(r"Test Case ['\"](?P<name>[^'\"]+)['\"] failed|Failing tests?:\s*(?P<tail>.+)", re.I)

for idx, line in enumerate(lines):
    if is_non_blocking_noise(line):
        continue

    if " warning: " in f" {line} " or line.strip().startswith("warning:"):
        warning_count += 1
    if m := failed_test_pattern.search(line):
        name = (m.groupdict().get("name") or m.groupdict().get("tail") or line).strip()
        if name and name not in failed_tests:
            failed_tests.append(name[:300])

    for kind, pattern in patterns:
        m = pattern.search(line)
        if not m:
            continue
        gd = m.groupdict()
        msg = gd.get("msg") or line.strip()
        item = {
            "kind": kind,
            "severity": "error",
            "message": msg.strip()[:1000],
            "raw_excerpt": compact_excerpt(idx),
        }
        item["failure_domain"] = failure_domain.get(kind, "unknown")
        item["retryable"] = item["failure_domain"] == "env_issue"
        if gd.get("file"):
            item["file"] = normalize_file(gd.get("file"))
        if gd.get("line"):
            try:
                item["line"] = int(gd["line"])
            except ValueError:
                pass
        if gd.get("column"):
            try:
                item["column"] = int(gd["column"])
            except ValueError:
                pass
        items.append(item)
        break

if not items:
    for idx, line in enumerate(lines):
        m = generic_error.search(line)
        if m:
            items.append({
                "kind": "unknown",
                "severity": "error",
                "message": m.group("msg").strip()[:1000] or line.strip()[:1000],
                "raw_excerpt": compact_excerpt(idx),
                "failure_domain": "unknown",
                "retryable": False,
            })
            break

if xcodebuild_exit_code == 0:
    items = []
else:
    items.sort(key=lambda d: priority.get(d.get("kind", "unknown"), 99))
    items = items[:10]

status = "failed" if items else "unknown"
summary = "No actionable compiler/test error pattern found. Inspect build-summary.txt before raw logs."
next_action = "Read build-summary.txt. Only inspect raw build log if summaries are insufficient."

if xcodebuild_exit_code == 0:
    status = "passed"
    summary = "Verification succeeded."
    next_action = "none"
elif xcodebuild_exit_code is not None and not items:
    status = "failed"
    summary = "Verification failed; digest could not classify the first blocking error."
    next_action = "Read build-summary.txt. Only inspect raw build log if summaries are insufficient."

if items:
    first = items[0]
    if first.get("kind") in env_issue_kinds or first.get("failure_domain") == "env_issue":
        status = "blocked"
    loc = ""
    if first.get("file"):
        loc = first["file"]
        if first.get("line"):
            loc += f":{first['line']}"
        if first.get("column"):
            loc += f":{first['column']}"
    prefix = f"{first['kind']}"
    summary = f"{prefix}: {loc + ' ' if loc else ''}{first.get('message', '').strip()}"[:1200]
    if status == "blocked":
        next_action = "Inspect the local Xcode workspace/destination/Simulator environment, then rerun verification. Do not treat this as XCTest failure."
    else:
        next_action = "Fix the first real blocking error only, then request verification again. Do not read the raw build log by default."

fingerprint = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]

payload = {
    "status": status,
    "mode": "auto",
    "fingerprint": fingerprint,
    "cached": False,
    "summary": summary,
    "finished_at": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    "diagnostics": items,
    "first_blocking_error": items[0] if items else None,
    "failed_tests": failed_tests[:20],
    "warnings_count": warning_count,
    "artifacts": {
        "diagnostics_json": str(out_json),
        "build_summary": str(out_summary),
        "verification_report": str(out_report),
        "raw_log": str(log_path),
    },
    "next_action": next_action,
    "raw_log_policy": "forbidden_by_default",
    "needs_raw_log": False,
}

out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

report = {
    "status": status,
    "mode": os.environ.get("CODEX_VERIFY_MODE", "auto"),
    "fingerprint": fingerprint,
    "cached": False,
    "summary": summary,
    "first_blocking_error": items[0] if items else None,
    "failed_tests": failed_tests[:20],
    "warnings_count": warning_count,
    "artifact_paths": {
        "diagnostics_json": str(out_json),
        "build_summary": str(out_summary),
        "verification_report": str(out_report),
        "raw_log": str(log_path),
    },
    "suggested_next_action": next_action,
    "raw_log_policy": "forbidden_by_default",
    "needs_raw_log": False,
    "generated_at": payload["finished_at"],
}
out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if not out_summary.exists() or out_summary.stat().st_size == 0:
    out_summary.write_text(summary + "\n", encoding="utf-8")
PY

printf 'Wrote %s\nWrote %s\nWrote %s\n' "$OUT_JSON" "$OUT_SUMMARY" "$OUT_REPORT"
