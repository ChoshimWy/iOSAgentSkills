#!/usr/bin/env python3
"""Export and summarize xctrace evidence into compact Agent-readable files.

The script intentionally keeps raw `xctrace export` XML out of the Agent context.
It exports a small set of high-signal tables, then produces `trace-summary.json`
and `trace-summary.md` with hangs, dispatch events, runloop counts, and top app
or focus-process frames.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

DEFAULT_TABLES = [
    "potential-hangs",
    "hang-risks",
    "time-profile",
    "time-sample",
    "thread-info",
    "runloop-events",
    "gcd-perf-event",
    "os-log",
]
DEFAULT_APP_PATTERNS: list[str] = []
LARGE_TABLE_BYTES = 10_000_000
MAX_SIGNATURE_FRAMES = 20
MAX_STACK_SIGNATURES = 20
MAX_THREAD_HOTSPOTS = 10
MAX_THREAD_FRAMES = 20


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def textish(elem: ET.Element | None) -> str | None:
    if elem is None:
        return None
    for key in ("fmt", "name", "schema", "pid", "path"):
        value = elem.get(key)
        if value:
            return value
    if elem.text and elem.text.strip():
        return elem.text.strip()
    return None


def first_desc(row: ET.Element, names: set[str]) -> ET.Element | None:
    for child in row.iter():
        if child is row:
            continue
        if local(child.tag) in names:
            return child
    return None


def all_desc_values(row: ET.Element, names: set[str]) -> list[str]:
    values: list[str] = []
    for child in row.iter():
        if child is row:
            continue
        if local(child.tag) in names:
            value = textish(child)
            if value:
                values.append(value)
    return values


def iter_rows(path: Path):
    for _, elem in ET.iterparse(path, events=("end",)):
        if local(elem.tag) == "row":
            yield elem
            elem.clear()


def run_command(command: list[str], *, quiet: bool) -> None:
    if not quiet:
        print("$ " + " ".join(command), file=sys.stderr)
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            print(exc.stdout, file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        raise SystemExit(exc.returncode) from exc


def safe_parse(path: Path) -> ET.ElementTree | Exception:
    try:
        return ET.parse(path)
    except Exception as exc:  # pragma: no cover - diagnostic path
        return exc


def parse_toc(toc_path: Path, trace_path: Path) -> dict:
    summary: dict = {
        "trace_path": str(trace_path),
        "toc_path": str(toc_path),
        "toc_bytes": toc_path.stat().st_size if toc_path.exists() else None,
        "runs": [],
        "processes": [],
        "tables": [],
    }
    parsed = safe_parse(toc_path)
    if isinstance(parsed, Exception):
        summary["parse_error"] = str(parsed)
        return summary

    root = parsed.getroot()
    for run in root.findall("run"):
        run_item: dict = dict(run.attrib)
        info = run.find("info")
        if info is not None:
            target = info.find("target")
            if target is not None:
                process = target.find("process")
                if process is not None:
                    run_item["target_process"] = dict(process.attrib)
                device = target.find("device")
                if device is not None:
                    run_item["device"] = dict(device.attrib)
            summary_node = info.find("summary")
            if summary_node is not None:
                run_item["summary"] = {
                    local(child.tag): textish(child) for child in list(summary_node) if textish(child)
                }
        processes = run.find("processes")
        if processes is not None:
            for process in processes.findall("process"):
                summary["processes"].append(dict(process.attrib))
        data = run.find("data")
        if data is not None:
            for table in data.findall("table"):
                item = dict(table.attrib)
                if item.get("schema"):
                    summary["tables"].append(item)
        summary["runs"].append(run_item)
    return summary


def available_schemas(toc_path: Path, run_number: str) -> set[str]:
    parsed = safe_parse(toc_path)
    if isinstance(parsed, Exception):
        return set()
    root = parsed.getroot()
    schemas: set[str] = set()
    for run in root.findall("run"):
        if run.get("number") != run_number:
            continue
        data = run.find("data")
        if data is None:
            continue
        for table in data.findall("table"):
            schema = table.get("schema")
            if schema:
                schemas.add(schema)
    return schemas


def export_tables(trace_path: Path, output_dir: Path, tables: list[str], *, run_number: str, quiet: bool) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    toc_path = output_dir / "toc.xml"
    run_command(
        ["xcrun", "xctrace", "export", "--input", str(trace_path), "--toc", "--output", str(toc_path)],
        quiet=quiet,
    )
    available = available_schemas(toc_path, run_number)
    requested = list(dict.fromkeys(tables))
    selected = [table for table in requested if table in available]
    missing = [table for table in requested if table not in available]
    manifest = {
        "requested_tables": requested,
        "exported_tables": selected,
        "missing_tables": missing,
        "available_tables_count": len(available),
    }
    (output_dir / "export-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if not quiet and missing:
        print("Skipping tables absent from trace: " + ", ".join(missing), file=sys.stderr)
    for table in selected:
        out = output_dir / f"{table}.xml"
        xpath = f"/trace-toc/run[@number='{run_number}']/data/table[@schema='{table}']"
        run_command(
            ["xcrun", "xctrace", "export", "--input", str(trace_path), "--xpath", xpath, "--output", str(out)],
            quiet=quiet,
        )
    return toc_path


def parse_potential_hangs(path: Path) -> dict:
    rows: list[dict] = []
    if not path.exists():
        return {"exported": False, "rows": []}
    for row in iter_rows(path):
        item = {
            "start_time": textish(first_desc(row, {"start-time"})),
            "duration": textish(first_desc(row, {"duration"})),
            "hang_type": textish(first_desc(row, {"hang-type", "category"})),
            "thread": textish(first_desc(row, {"thread"})),
            "process": textish(first_desc(row, {"process"})),
        }
        rows.append({key: value for key, value in item.items() if value})
    return {"exported": True, "row_count": len(rows), "rows": rows[:50]}


def parse_gcd_events(path: Path) -> dict:
    if not path.exists():
        return {"exported": False}
    event_counts: Counter[str] = Counter()
    thread_counts: Counter[str] = Counter()
    samples: list[dict] = []
    rows = 0
    for row in iter_rows(path):
        rows += 1
        values = all_desc_values(row, {"string", "dispatch-perf-event", "event-concept"})
        event = next((value for value in values if value not in {"Event", "Concept"}), None) or "unknown"
        event_counts[event] += 1
        thread = textish(first_desc(row, {"thread"})) or "unknown"
        thread_counts[thread] += 1
        if len(samples) < 10:
            samples.append(
                {
                    "sample_time": textish(first_desc(row, {"sample-time", "start-time"})),
                    "event": event,
                    "thread": thread,
                }
            )
    return {
        "exported": True,
        "row_count": rows,
        "event_counts": event_counts.most_common(30),
        "top_threads": thread_counts.most_common(20),
        "samples": samples,
    }


def parse_runloop_events(path: Path) -> dict:
    if not path.exists():
        return {"exported": False}
    event_counts: Counter[str] = Counter()
    thread_counts: Counter[str] = Counter()
    duration_rows: list[dict] = []
    rows = 0
    for row in iter_rows(path):
        rows += 1
        values = all_desc_values(row, {"string", "event-concept", "activity", "state", "category"})
        event = values[0] if values else "unknown"
        event_counts[event] += 1
        thread = textish(first_desc(row, {"thread"})) or "unknown"
        thread_counts[thread] += 1
        duration = textish(first_desc(row, {"duration"}))
        if duration and len(duration_rows) < 20:
            duration_rows.append(
                {
                    "start_time": textish(first_desc(row, {"start-time", "sample-time"})),
                    "duration": duration,
                    "event": event,
                    "thread": thread,
                }
            )
    return {
        "exported": True,
        "bytes": path.stat().st_size,
        "row_count": rows,
        "event_counts": event_counts.most_common(30),
        "top_threads": thread_counts.most_common(20),
        "duration_samples": duration_rows,
    }


def frame_binary(elem: ET.Element, binary_by_id: dict[str, str]) -> str:
    for key in ("binary", "image", "library"):
        value = elem.get(key)
        if value:
            return binary_by_id.get(value, value)
    child = first_desc(elem, {"binary", "image", "library"})
    if child is None:
        return ""
    ref = child.get("ref")
    if ref and ref in binary_by_id:
        return binary_by_id[ref]
    value = textish(child)
    child_id = child.get("id")
    if child_id and value:
        binary_by_id[child_id] = value
    return value or ""


def is_address_symbol(name: str) -> bool:
    return bool(re.fullmatch(r"0x[0-9A-Fa-f]+", name)) or name == "<unknown>"


BOILERPLATE_FRAME_PATTERNS = [
    "UIApplicationMain",
    "-[UIApplication _run]",
    "GSEventRunModal",
    "CFRunLoopRun",
    "__CFRunLoopRun",
    "__CFRUNLOOP_IS_CALLING_OUT",
    "__debug_main_executable_dylib_entry_point",
    "_pthread_start",
    "thread_start",
]
BOILERPLATE_FRAME_EXACT = {"start"}


def is_actionable_frame(name: str) -> bool:
    if is_address_symbol(name) or name in BOILERPLATE_FRAME_EXACT:
        return False
    return not any(pattern in name for pattern in BOILERPLATE_FRAME_PATTERNS)


def stack_signature_entries(counter: Counter[tuple[str, tuple[str, ...]]], limit: int = MAX_STACK_SIGNATURES) -> list[dict]:
    entries: list[dict] = []
    for (thread, frames), count in counter.most_common(limit):
        entries.append(
            {
                "count": count,
                "thread": thread,
                "frames": list(frames),
            }
        )
    return entries


def thread_hotspot_entries(
    thread_counts: Counter[str],
    thread_actionable_counts: dict[str, Counter[str]],
    thread_focus_counts: dict[str, Counter[str]],
) -> list[dict]:
    entries: list[dict] = []
    for thread, samples in thread_counts.most_common(MAX_THREAD_HOTSPOTS):
        entries.append(
            {
                "thread": thread,
                "samples": samples,
                "top_actionable_frames": thread_actionable_counts.get(thread, Counter()).most_common(MAX_THREAD_FRAMES),
                "top_focus_frames": thread_focus_counts.get(thread, Counter()).most_common(MAX_THREAD_FRAMES),
            }
        )
    return entries


def parse_trace_time_seconds(value: str | None) -> float | None:
    if not value:
        return None
    text = value.strip()
    match = re.match(r"(?:(\d+):)?(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not match:
        return None
    minutes = int(match.group(1) or 0)
    seconds = int(match.group(2))
    frac = (match.group(3) or "") + (match.group(4) or "")
    fraction = float("0." + frac) if frac else 0.0
    return minutes * 60 + seconds + fraction


def parse_duration_seconds(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value)
    return float(match.group(1)) if match else None


def hang_windows(potential_hangs: dict) -> list[dict]:
    windows: list[dict] = []
    for row in potential_hangs.get("rows", []):
        start = parse_trace_time_seconds(row.get("start_time"))
        duration = parse_duration_seconds(row.get("duration"))
        if start is None or duration is None:
            continue
        item = dict(row)
        item["start_seconds"] = start
        item["end_seconds"] = start + duration
        windows.append(item)
    return windows


def window_label(window: dict, index: int) -> str:
    start = window.get("start_time") or f"{window.get('start_seconds', 0):.3f}s"
    duration = window.get("duration") or "unknown"
    return f"hang[{index}] {start} + {duration}"


def matches_app_frame(name: str, binary: str, patterns: list[str]) -> bool:
    target = f"{binary} {name}"
    return any(pattern in target for pattern in patterns)


def resolve_thread(elem: ET.Element | None, thread_by_id: dict[str, str]) -> str:
    if elem is None:
        return "unknown"
    ref = elem.get("ref")
    if ref and ref in thread_by_id:
        return thread_by_id[ref]
    value = textish(elem) or "unknown"
    elem_id = elem.get("id")
    if elem_id and value != "unknown":
        thread_by_id[elem_id] = value
    return value


def resolve_frame(elem: ET.Element, binary_by_id: dict[str, str], frame_by_id: dict[str, tuple[str, str]]) -> tuple[str, str]:
    ref = elem.get("ref")
    if ref and ref in frame_by_id:
        return frame_by_id[ref]
    name = elem.get("name") or textish(first_desc(elem, {"symbol", "name"})) or "<unknown>"
    binary = frame_binary(elem, binary_by_id)
    frame_id = elem.get("id")
    if frame_id:
        frame_by_id[frame_id] = (name, binary)
    return name, binary


def parse_frame_table(
    path: Path,
    patterns: list[str],
    *,
    max_frames: int | None,
    windows: list[dict] | None = None,
) -> dict:
    if not path.exists():
        return {"exported": False}
    frame_counts: Counter[str] = Counter()
    actionable_frame_counts: Counter[str] = Counter()
    app_frame_counts: Counter[str] = Counter()
    app_actionable_frame_counts: Counter[str] = Counter()
    binary_counts: Counter[str] = Counter()
    unresolved_frame_counts: Counter[str] = Counter()
    thread_counts: Counter[str] = Counter()
    focus_thread_counts: Counter[str] = Counter()
    thread_actionable_counts: dict[str, Counter[str]] = {}
    thread_focus_actionable_counts: dict[str, Counter[str]] = {}
    stack_signature_counts: Counter[tuple[str, tuple[str, ...]]] = Counter()
    focus_stack_signature_counts: Counter[tuple[str, tuple[str, ...]]] = Counter()
    window_frame_counts: dict[str, Counter[str]] = {}
    window_focus_counts: dict[str, Counter[str]] = {}
    window_stack_signature_counts: dict[str, Counter[tuple[str, tuple[str, ...]]]] = {}
    window_focus_stack_signature_counts: dict[str, Counter[tuple[str, tuple[str, ...]]]] = {}
    for index, window in enumerate(windows or []):
        label = window_label(window, index)
        window_frame_counts[label] = Counter()
        window_focus_counts[label] = Counter()
        window_stack_signature_counts[label] = Counter()
        window_focus_stack_signature_counts[label] = Counter()

    binary_by_id: dict[str, str] = {}
    binary_info_by_name: dict[str, dict] = {}
    frame_by_id: dict[str, tuple[str, str]] = {}
    thread_by_id: dict[str, str] = {}
    rows = 0
    frames = 0
    symbolicated_frames = 0
    truncated = False

    for _, row in ET.iterparse(path, events=("end",)):
        if local(row.tag) != "row":
            continue
        rows += 1
        for binary_elem in row.iter():
            if local(binary_elem.tag) != "binary":
                continue
            binary_id = binary_elem.get("id")
            binary_name = binary_elem.get("name") or binary_elem.get("path")
            if binary_id and binary_name:
                binary_by_id[binary_id] = binary_name
            if binary_name:
                binary_info_by_name.setdefault(
                    binary_name,
                    {
                        "name": binary_name,
                        "uuid": binary_elem.get("UUID") or binary_elem.get("uuid"),
                        "arch": binary_elem.get("arch"),
                        "path": binary_elem.get("path"),
                    },
                )

        thread = resolve_thread(first_desc(row, {"thread"}), thread_by_id)
        thread_counts[thread] += 1
        sample_seconds = parse_trace_time_seconds(textish(first_desc(row, {"sample-time", "start-time"})))
        active_windows = []
        if sample_seconds is not None:
            for index, window in enumerate(windows or []):
                start = window.get("start_seconds")
                end = window.get("end_seconds")
                if isinstance(start, (int, float)) and isinstance(end, (int, float)) and start <= sample_seconds <= end:
                    active_windows.append(window_label(window, index))

        row_has_focus = False
        row_actionable_frames: list[str] = []
        row_focus_actionable_frames: list[str] = []
        for frame_elem in row.iter():
            if local(frame_elem.tag) != "frame":
                continue
            frames += 1
            name, binary = resolve_frame(frame_elem, binary_by_id, frame_by_id)
            frame_counts[name] += 1
            focus = matches_app_frame(name, binary, patterns)
            actionable = is_actionable_frame(name)
            if actionable:
                actionable_frame_counts[name] += 1
                row_actionable_frames.append(name)
                thread_actionable_counts.setdefault(thread, Counter())[name] += 1
            if focus:
                row_has_focus = True
                app_frame_counts[name] += 1
                if actionable:
                    app_actionable_frame_counts[name] += 1
                    row_focus_actionable_frames.append(name)
                    thread_focus_actionable_counts.setdefault(thread, Counter())[name] += 1
            if not is_address_symbol(name):
                symbolicated_frames += 1
            else:
                unresolved_frame_counts[binary or "<unknown-binary>"] += 1
            if binary:
                binary_counts[binary] += 1
            for label in active_windows:
                if actionable:
                    window_frame_counts[label][name] += 1
                if focus and actionable:
                    window_focus_counts[label][name] += 1
            if max_frames and frames >= max_frames:
                truncated = True
                break
        if row_actionable_frames:
            signature = tuple(row_actionable_frames[:MAX_SIGNATURE_FRAMES])
            stack_signature_counts[(thread, signature)] += 1
            for label in active_windows:
                window_stack_signature_counts[label][(thread, signature)] += 1
        if row_focus_actionable_frames:
            focus_signature = tuple(row_focus_actionable_frames[:MAX_SIGNATURE_FRAMES])
            focus_stack_signature_counts[(thread, focus_signature)] += 1
            for label in active_windows:
                window_focus_stack_signature_counts[label][(thread, focus_signature)] += 1
        if row_has_focus:
            focus_thread_counts[thread] += 1
        row.clear()
        if truncated:
            break

    return {
        "exported": True,
        "bytes": path.stat().st_size,
        "row_count_seen": rows,
        "frame_count_seen": frames,
        "top_frames": frame_counts.most_common(30),
        "top_actionable_frames": actionable_frame_counts.most_common(50),
        "top_app_or_focus_frames": app_frame_counts.most_common(50),
        "top_app_or_focus_actionable_frames": app_actionable_frame_counts.most_common(50),
        "top_binaries": binary_counts.most_common(30),
        "binary_images": [
            {
                **binary_info_by_name.get(binary, {"name": binary}),
                "frame_count": count,
            }
            for binary, count in binary_counts.most_common(30)
        ],
        "top_threads": thread_counts.most_common(30),
        "top_focus_threads": focus_thread_counts.most_common(30),
        "thread_hotspots": thread_hotspot_entries(
            thread_counts,
            thread_actionable_counts,
            thread_focus_actionable_counts,
        ),
        "top_stack_signatures": {
            "overall": stack_signature_entries(stack_signature_counts),
            "focus": stack_signature_entries(focus_stack_signature_counts),
            "hang_windows": {
                label: stack_signature_entries(counter)
                for label, counter in window_stack_signature_counts.items()
            },
            "hang_window_focus": {
                label: stack_signature_entries(counter)
                for label, counter in window_focus_stack_signature_counts.items()
            },
        },
        "top_unresolved_binaries": unresolved_frame_counts.most_common(30),
        "hang_window_actionable_frames": {label: counter.most_common(30) for label, counter in window_frame_counts.items()},
        "hang_window_focus_actionable_frames": {label: counter.most_common(30) for label, counter in window_focus_counts.items()},
        "symbolication": {
            "symbolicated_frames": symbolicated_frames,
            "unresolved_frames": max(frames - symbolicated_frames, 0),
            "symbolicated_ratio": round(symbolicated_frames / frames, 4) if frames else None,
        },
        "truncated": truncated,
    }


def derive_focus_patterns(trace_summary: dict, explicit_patterns: list[str] | None) -> list[str]:
    patterns: list[str] = []
    if explicit_patterns:
        patterns.extend(explicit_patterns)
    for run in trace_summary.get("runs", []):
        process = run.get("target_process", {})
        for key in ("name", "path"):
            value = process.get(key)
            if value:
                patterns.append(value)
    for process in trace_summary.get("processes", []):
        for key in ("name", "path"):
            value = process.get(key)
            if value and value not in {"kernel", "Unknown"}:
                patterns.append(value)
    patterns.extend(DEFAULT_APP_PATTERNS)
    return list(dict.fromkeys(patterns))


def read_export_manifest(output_dir: Path) -> dict:
    path = output_dir / "export-manifest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"parse_error": str(exc), "path": str(path)}


def collect_table_field(summary: dict, field: str) -> dict:
    collected: dict = {}
    for key in ("time_profile", "time_sample"):
        value = summary.get(key, {}).get(field)
        if value:
            collected[key] = value
    return collected


def needs_dsym_for_binary(binary: str, path: str | None) -> bool:
    if binary in {"<unknown-binary>", "Unknown"}:
        return False
    if not path:
        return True
    return not path.startswith(("/System/", "/usr/lib/"))


def symbolication_diagnostics(summary: dict) -> dict:
    tables: list[dict] = []
    needs_dsym = False
    for key in ("time_profile", "time_sample"):
        table = summary.get(key, {})
        symbolication = table.get("symbolication")
        if not symbolication:
            continue
        image_by_name = {image.get("name"): image for image in table.get("binary_images", []) if image.get("name")}
        unresolved = []
        for binary, count in table.get("top_unresolved_binaries", [])[:15]:
            image = image_by_name.get(binary, {})
            needs_dsym = needs_dsym_for_binary(binary, image.get("path"))
            unresolved.append(
                {
                    "binary": binary,
                    "unresolved_frames": count,
                    "uuid": image.get("uuid"),
                    "arch": image.get("arch"),
                    "path": image.get("path"),
                    "needs_dsym": needs_dsym,
                }
            )
        ratio = symbolication.get("symbolicated_ratio")
        table_needs_dsym = any(item["needs_dsym"] for item in unresolved) and (ratio is None or ratio < 0.8)
        needs_dsym = needs_dsym or table_needs_dsym
        tables.append(
            {
                "table": key,
                "symbolicated_ratio": ratio,
                "symbolicated_frames": symbolication.get("symbolicated_frames"),
                "unresolved_frames": symbolication.get("unresolved_frames"),
                "needs_dsym": table_needs_dsym,
                "top_unresolved_binaries": unresolved,
            }
        )
    return {
        "needs_dsym": needs_dsym,
        "tables": tables,
        "suggested_next_action": (
            "Provide matching .dSYM or .xcarchive for binaries with high unresolved frame counts."
            if needs_dsym
            else "Symbolication is sufficient for first-pass hotspot triage."
        ),
    }


def first_non_empty_frame_list(*lists: list) -> list:
    for value in lists:
        if value:
            return value
    return []


def frame_names(*entry_lists: list, limit: int = 8) -> list[str]:
    names: list[str] = []
    for entries in entry_lists:
        for item in entries[:limit]:
            if isinstance(item, dict):
                frames = item.get("frames") or []
                for frame in frames:
                    if frame not in names:
                        names.append(frame)
                    if len(names) >= limit:
                        return names
            elif isinstance(item, (list, tuple)) and item:
                name = item[0]
                if isinstance(name, str) and name not in names:
                    names.append(name)
            if len(names) >= limit:
                return names
        if len(names) >= limit:
            break
    return names


def build_actionable_findings(summary: dict) -> list[dict]:
    findings: list[dict] = []
    time_profile = summary.get("time_profile", {})
    hang_focus_windows = time_profile.get("hang_window_focus_actionable_frames", {})
    hang_general_windows = time_profile.get("hang_window_actionable_frames", {})
    hang_focus_stacks = time_profile.get("top_stack_signatures", {}).get("hang_window_focus", {})
    focus_frames = time_profile.get("top_app_or_focus_actionable_frames", [])
    actionable_frames = time_profile.get("top_actionable_frames", [])

    for index, hang in enumerate(summary.get("potential_hangs", {}).get("rows", [])):
        label_prefix = f"hang[{index}]"
        focus_window_frames = next((frames for label, frames in hang_focus_windows.items() if label.startswith(label_prefix)), [])
        general_window_frames = next((frames for label, frames in hang_general_windows.items() if label.startswith(label_prefix)), [])
        focus_window_stacks = next((stacks for label, stacks in hang_focus_stacks.items() if label.startswith(label_prefix)), [])
        suspects = frame_names(
            focus_window_stacks,
            focus_window_frames,
            general_window_frames,
            focus_frames,
            actionable_frames,
        )
        thread = hang.get("thread", "unknown")
        findings.append(
            {
                "severity": "high",
                "category": "main_thread_hang" if "Main Thread" in thread else "hang",
                "evidence": f"{hang.get('hang_type', 'Hang')} {hang.get('duration', 'unknown duration')} on {thread}",
                "suspects": suspects,
                "next_action": (
                    "Inspect hang-window stack signatures first; reduce synchronous work, notification fanout, or UI refresh on the blocked thread."
                ),
            }
        )

    for hotspot in time_profile.get("thread_hotspots", []):
        thread = hotspot.get("thread", "")
        if "Main Thread" not in thread:
            continue
        suspects = frame_names(
            hotspot.get("top_focus_frames", []),
            hotspot.get("top_actionable_frames", []),
        )
        if suspects:
            findings.append(
                {
                    "severity": "medium",
                    "category": "main_thread_hotspot",
                    "evidence": f"{hotspot.get('samples', 0)} samples on {thread}",
                    "suspects": suspects,
                    "next_action": "Move repeated computation off the main thread or throttle UI-facing updates.",
                }
            )
        break

    ui_suspects = [
        name
        for name in frame_names(actionable_frames, limit=20)
        if any(token in name for token in ("UICollectionView", "layout", "layoutSubviews", "cellForItemAt", "UIView"))
    ][:8]
    if ui_suspects:
        findings.append(
            {
                "severity": "medium",
                "category": "ui_layout_hotspot",
                "evidence": "UIKit layout or collection-view frames appear in top actionable samples.",
                "suspects": ui_suspects,
                "next_action": "Check whether high-frequency model updates trigger reload/layout work every profiling tick.",
            }
        )

    diagnostics = summary.get("symbolication_diagnostics", {})
    if diagnostics.get("needs_dsym"):
        suspects = [
            item.get("binary")
            for table in diagnostics.get("tables", [])
            for item in table.get("top_unresolved_binaries", [])[:3]
            if item.get("needs_dsym")
        ][:8]
        findings.append(
            {
                "severity": "medium",
                "category": "symbolication_gap",
                "evidence": "Low symbolication ratio or unresolved frames remain in exported profiling data.",
                "suspects": suspects,
                "next_action": "Provide matching .dSYM or .xcarchive before making source-line-level conclusions.",
            }
        )
    return findings


def build_summary(args: argparse.Namespace, toc_path: Path) -> dict:
    output_dir = Path(args.output_dir)
    exported_files = {path.name: path.stat().st_size for path in sorted(output_dir.glob("*.xml"))}
    trace_summary = parse_toc(toc_path, Path(args.trace))
    patterns = derive_focus_patterns(trace_summary, args.focus_pattern)
    summary: dict = {
        "status": "completed",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "trace": trace_summary,
        "export_manifest": read_export_manifest(output_dir),
        "exported_files_bytes": exported_files,
        "raw_log_policy": "Do not read full xctrace XML exports in Agent context; consume trace-summary.json or trace-summary.md first.",
        "focus_patterns": patterns,
        "potential_hangs": parse_potential_hangs(output_dir / "potential-hangs.xml"),
        "gcd_perf_events": parse_gcd_events(output_dir / "gcd-perf-event.xml"),
        "runloop_events": parse_runloop_events(output_dir / "runloop-events.xml"),
    }
    max_frames = None if args.max_frames <= 0 else args.max_frames
    for table in ("time-profile", "time-sample"):
        path = output_dir / f"{table}.xml"
        key = table.replace("-", "_")
        if path.exists():
            summary[key] = parse_frame_table(
                path,
                patterns,
                max_frames=max_frames,
                windows=hang_windows(summary.get("potential_hangs", {})),
            )
    summary["top_stack_signatures"] = collect_table_field(summary, "top_stack_signatures")
    summary["thread_hotspots"] = collect_table_field(summary, "thread_hotspots")
    summary["symbolication_diagnostics"] = symbolication_diagnostics(summary)
    summary["actionable_findings"] = build_actionable_findings(summary)
    attention: list[str] = []
    hangs = summary.get("potential_hangs", {})
    if hangs.get("row_count"):
        attention.append(f"potential_hangs={hangs.get('row_count')}")
    if any(size > LARGE_TABLE_BYTES for size in exported_files.values()):
        attention.append("large_raw_tables_present")
    for key in ("time_profile", "time_sample"):
        ratio = summary.get(key, {}).get("symbolication", {}).get("symbolicated_ratio")
        if ratio is not None and ratio < 0.2:
            attention.append(f"low_symbolication_{key}={ratio}")
    summary["assessment"] = {
        "workflow_ok": True,
        "needs_attention": attention,
        "headline": (
            "Trace evidence was reduced to structured summary; potential hangs are present."
            if hangs.get("row_count")
            else "Trace evidence was reduced to structured summary; no potential hangs exported."
        ),
    }
    return summary


def write_markdown(summary: dict, path: Path) -> None:
    lines = [
        "# xctrace Summary",
        "",
        f"- status: {summary['status']}",
        f"- generated_at: {summary.get('generated_at')}",
        f"- workflow_ok: {summary['assessment']['workflow_ok']}",
        f"- headline: {summary['assessment']['headline']}",
        f"- needs_attention: {', '.join(summary['assessment']['needs_attention']) or 'none'}",
        "",
        "## Actionable findings",
    ]
    findings = summary.get("actionable_findings", [])
    if findings:
        for finding in findings:
            lines.append(
                f"- [{finding.get('severity', 'unknown')}] {finding.get('category', 'unknown')}: "
                f"{finding.get('evidence', '')}"
            )
            suspects = finding.get("suspects") or []
            if suspects:
                lines.append(f"  - suspects: {', '.join(suspects[:8])}")
            if finding.get("next_action"):
                lines.append(f"  - next_action: {finding['next_action']}")
    else:
        lines.append("- none")

    lines.extend(["", "## Symbolication"])
    for key in ("time_profile", "time_sample"):
        symbolication = summary.get(key, {}).get("symbolication")
        if symbolication:
            lines.append(f"- {key}: {symbolication}")

    diagnostics = summary.get("symbolication_diagnostics", {})
    lines.extend(["", "## Symbolication diagnostics"])
    if diagnostics:
        lines.append(f"- needs_dsym: {diagnostics.get('needs_dsym')}")
        lines.append(f"- suggested_next_action: {diagnostics.get('suggested_next_action')}")
        for table in diagnostics.get("tables", []):
            lines.append(f"### {table.get('table')}")
            lines.append(f"- symbolicated_ratio: {table.get('symbolicated_ratio')}")
            unresolved = table.get("top_unresolved_binaries", [])[:10]
            if unresolved:
                for item in unresolved:
                    lines.append(
                        "- "
                        f"{item.get('binary')}: unresolved={item.get('unresolved_frames')}, "
                        f"uuid={item.get('uuid')}, needs_dsym={item.get('needs_dsym')}"
                    )
            else:
                lines.append("- unresolved: none")
    else:
        lines.append("- none")

    lines.extend(["", "## Exported files"])
    for name, size in summary.get("exported_files_bytes", {}).items():
        lines.append(f"- {name}: {size} bytes")

    lines.extend(["", "## Top binaries"])
    for key in ("time_profile", "time_sample"):
        lines.append(f"### {key}")
        binaries = summary.get(key, {}).get("top_binaries", [])[:15]
        if binaries:
            for item, count in binaries:
                lines.append(f"- {item}: {count}")
        else:
            lines.append("- none")

    lines.extend(["", "## Potential hangs"])
    hangs = summary.get("potential_hangs", {})
    if hangs.get("rows"):
        for row in hangs["rows"]:
            lines.append(f"- {row}")
    else:
        lines.append("- none")

    lines.extend(["", "## GCD perf events"])
    for item, count in summary.get("gcd_perf_events", {}).get("event_counts", [])[:15]:
        lines.append(f"- {item}: {count}")

    lines.extend(["", "## Thread hotspots"])
    for key in ("time_profile", "time_sample"):
        lines.append(f"### {key}")
        hotspots = summary.get("thread_hotspots", {}).get(key, [])[:10]
        if hotspots:
            for hotspot in hotspots:
                lines.append(f"- {hotspot.get('thread')}: {hotspot.get('samples')} samples")
                focus_frames = hotspot.get("top_focus_frames") or []
                actionable_frames = hotspot.get("top_actionable_frames") or []
                if focus_frames:
                    lines.append(
                        "  - focus: "
                        + ", ".join(f"{name} ({count})" for name, count in focus_frames[:5])
                    )
                elif actionable_frames:
                    lines.append(
                        "  - actionable: "
                        + ", ".join(f"{name} ({count})" for name, count in actionable_frames[:5])
                    )
        else:
            lines.append("- none")

    lines.extend(["", "## Top frames"])
    for key in ("time_profile", "time_sample"):
        lines.append(f"### {key} actionable")
        actionable_frames = summary.get(key, {}).get("top_actionable_frames", [])[:20]
        if actionable_frames:
            for item, count in actionable_frames:
                lines.append(f"- {item}: {count}")
        else:
            lines.append("- none")
        lines.append(f"### {key} focus actionable")
        focus_actionable = summary.get(key, {}).get("top_app_or_focus_actionable_frames", [])[:20]
        if focus_actionable:
            for item, count in focus_actionable:
                lines.append(f"- {item}: {count}")
        else:
            lines.append("- none")
        lines.append(f"### {key} overall")
        overall_frames = summary.get(key, {}).get("top_frames", [])[:20]
        if overall_frames:
            for item, count in overall_frames:
                lines.append(f"- {item}: {count}")
        else:
            lines.append("- none")
        lines.append(f"### {key} focus")
        focus_frames = summary.get(key, {}).get("top_app_or_focus_frames", [])[:20]
        if focus_frames:
            for item, count in focus_frames:
                lines.append(f"- {item}: {count}")
        else:
            lines.append("- none")

    lines.extend(["", "## Top stack signatures"])
    for key in ("time_profile", "time_sample"):
        signatures = summary.get("top_stack_signatures", {}).get(key, {})
        lines.append(f"### {key} focus")
        focus_signatures = signatures.get("focus", [])[:10]
        if focus_signatures:
            for item in focus_signatures:
                lines.append(f"- count={item.get('count')} thread={item.get('thread')}")
                for frame in item.get("frames", [])[:10]:
                    lines.append(f"  - {frame}")
        else:
            lines.append("- none")
        lines.append(f"### {key} hang-window focus")
        hang_window_signatures = signatures.get("hang_window_focus", {})
        if not hang_window_signatures:
            lines.append("- none")
        for label, entries in hang_window_signatures.items():
            lines.append(f"#### {label}")
            if entries:
                for item in entries[:10]:
                    lines.append(f"- count={item.get('count')} thread={item.get('thread')}")
                    for frame in item.get("frames", [])[:10]:
                        lines.append(f"  - {frame}")
            else:
                lines.append("- none")

    lines.extend(["", "## Hang-window focus frames"])
    for key in ("time_profile", "time_sample"):
        windows = summary.get(key, {}).get("hang_window_focus_actionable_frames", {})
        lines.append(f"### {key}")
        if not windows:
            lines.append("- none")
        for label, frames in windows.items():
            lines.append(f"#### {label}")
            if frames:
                for item, count in frames[:20]:
                    lines.append(f"- {item}: {count}")
            else:
                lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def default_output_dir(trace_path: Path) -> Path:
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", trace_path.stem).strip("-") or "trace"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("/tmp") / f"xctrace-summary-{safe_stem}-{stamp}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize xctrace exports into compact JSON/Markdown evidence.")
    parser.add_argument("trace", help="Path to .trace package/directory.")
    parser.add_argument("--output-dir", default=None, help="Directory for exported XML and summary artifacts. Defaults to /tmp/xctrace-summary-*.")
    parser.add_argument("--skip-export", action="store_true", help="Reuse existing XML exports in --output-dir instead of running xcrun xctrace export.")
    parser.add_argument("--run-number", default="1", help="Trace run number to export. Default: 1.")
    parser.add_argument("--tables", nargs="*", default=DEFAULT_TABLES, help="xctrace table schemas to export.")
    parser.add_argument("--focus-pattern", action="append", help="Substring used to identify app/focus frames. Can be repeated. Defaults to target process names from the trace TOC.")
    parser.add_argument("--max-frames", type=int, default=0, help="Max frame nodes to parse per table. 0 means unlimited.")
    parser.add_argument("--quiet", action="store_true", help="Suppress export command logging.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    trace_path = Path(args.trace).expanduser().resolve()
    if not trace_path.exists():
        print(f"error: trace path does not exist: {trace_path}", file=sys.stderr)
        return 2
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir(trace_path)
    args.output_dir = str(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    toc_path = output_dir / "toc.xml"
    if args.skip_export:
        if not toc_path.exists():
            print(f"error: --skip-export requires existing {toc_path}", file=sys.stderr)
            return 2
    else:
        toc_path = export_tables(trace_path, output_dir, args.tables, run_number=args.run_number, quiet=args.quiet)

    summary = build_summary(args, toc_path)
    json_path = output_dir / "trace-summary.json"
    md_path = output_dir / "trace-summary.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(summary, md_path)

    print(
        json.dumps(
            {
                "status": summary["status"],
                "summary_json": str(json_path),
                "summary_md": str(md_path),
                "assessment": summary["assessment"],
                "potential_hangs": summary.get("potential_hangs", {}).get("row_count", 0),
                "exported_files_bytes": summary.get("exported_files_bytes", {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
