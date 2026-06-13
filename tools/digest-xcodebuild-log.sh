#!/usr/bin/env bash
set -euo pipefail

# Convert a raw xcodebuild log into compact diagnostics.json and build-summary.txt.
# Agents should read diagnostics.json first and avoid the raw log by default.
#
# Usage:
#   tools/digest-xcodebuild-log.sh build.log diagnostics.json build-summary.txt
#
# Inputs:
#   $1 raw xcodebuild log path, default: build.log
#   $2 diagnostics output path, default: diagnostics.json
#   $3 summary output path, default: build-summary.txt

LOG_FILE="${1:-build.log}"
OUT_JSON="${2:-diagnostics.json}"
OUT_SUMMARY="${3:-build-summary.txt}"

if [[ ! -f "$LOG_FILE" ]]; then
  mkdir -p "$(dirname "$OUT_JSON")" "$(dirname "$OUT_SUMMARY")"
  printf '{\n  "status": "error",\n  "summary": "Log file not found",\n  "diagnostics": [],\n  "next_action": "Check the build-queue output path.",\n  "raw_log_policy": "forbidden_by_default"\n}\n' > "$OUT_JSON"
  printf 'Log file not found: %s\n' "$LOG_FILE" > "$OUT_SUMMARY"
  exit 1
fi

mkdir -p "$(dirname "$OUT_JSON")" "$(dirname "$OUT_SUMMARY")"

# Keep only a compact set of actionable lines. This summary is intentionally small.
grep -nE \
  "error:|fatal error:|warning:|Command SwiftCompile failed|Command CompileSwift failed|Undefined symbol|No such module|cannot find|does not conform|failed to build module|Provisioning profile|CodeSign|Signing|The operation couldn.t be completed|xcodebuild: error:|Testing failed|Test Case .* failed|Executed .* tests" \
  "$LOG_FILE" \
  | head -n 200 > "$OUT_SUMMARY" || true

python3 - "$LOG_FILE" "$OUT_JSON" "$OUT_SUMMARY" <<'PY'
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

text = log_path.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()

patterns = [
    ("project_config_error", re.compile(r"xcodebuild: error:|The project .* cannot be opened|Unable to open project", re.I)),
    ("missing_module", re.compile(r"No such module '([^']+)'|failed to build module '([^']+)'", re.I)),
    ("missing_dependency", re.compile(r"package .* is required|Could not resolve package dependencies|Unable to find a specification", re.I)),
    ("swift_compile_error", re.compile(r"(?P<file>[^:\n]+\.swift):(?P<line>\d+):(?P<column>\d+):\s*error:\s*(?P<msg>.*)")),
    ("objc_compile_error", re.compile(r"(?P<file>[^:\n]+\.(?:m|mm|h|hpp|cpp|c)):?(?P<line>\d+)?:?(?P<column>\d+)?:?\s*error:\s*(?P<msg>.*)")),
    ("linker_error", re.compile(r"Undefined symbol|duplicate symbol|ld: .*error|clang: error: linker command failed", re.I)),
    ("signing_error", re.compile(r"Provisioning profile|CodeSign|Signing for .* requires a development team|No profiles for", re.I)),
    ("destination_error", re.compile(r"Unable to find a destination|destination specifier|No available destinations", re.I)),
    ("test_failure", re.compile(r"Test Case .* failed|XCTAssert|Testing failed", re.I)),
]

# Fallback generic error patterns are intentionally later so structured compiler errors win.
generic_error = re.compile(r"\berror:\s*(?P<msg>.*)", re.I)

priority = {
    "project_config_error": 0,
    "missing_dependency": 1,
    "missing_module": 2,
    "swift_compile_error": 3,
    "objc_compile_error": 4,
    "linker_error": 5,
    "signing_error": 6,
    "destination_error": 7,
    "test_failure": 8,
    "unknown": 99,
}

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

for idx, line in enumerate(lines):
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
            })
            break

items.sort(key=lambda d: priority.get(d.get("kind", "unknown"), 99))
items = items[:10]

status = "failed" if items else "unknown"
summary = "No actionable compiler/test error pattern found. Inspect build-summary.txt before raw logs."
next_action = "Read build-summary.txt. Only inspect raw build log if summaries are insufficient."

if items:
    first = items[0]
    loc = ""
    if first.get("file"):
        loc = first["file"]
        if first.get("line"):
            loc += f":{first['line']}"
        if first.get("column"):
            loc += f":{first['column']}"
    prefix = f"{first['kind']}"
    summary = f"{prefix}: {loc + ' ' if loc else ''}{first.get('message', '').strip()}"[:1200]
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
    "artifacts": {
        "diagnostics_json": str(out_json),
        "build_summary": str(out_summary),
        "raw_log": str(log_path),
    },
    "next_action": next_action,
    "raw_log_policy": "forbidden_by_default",
}

out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if not out_summary.exists() or out_summary.stat().st_size == 0:
    out_summary.write_text(summary + "\n", encoding="utf-8")
PY

printf 'Wrote %s\nWrote %s\n' "$OUT_JSON" "$OUT_SUMMARY"
