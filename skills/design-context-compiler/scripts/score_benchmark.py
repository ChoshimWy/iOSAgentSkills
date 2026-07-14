#!/usr/bin/env python3
"""Score a completed Design Context Compiler benchmark manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
from typing import Any
import zlib

from validate_contract import (
    Diagnostic,
    load_json,
    validate_benchmark,
    validate_benchmark_artifact,
    validate_benchmark_case,
    validate_benchmark_input_context,
    validate_benchmark_run_plan,
    validate_benchmark_run_result,
    validate_benchmark_run_observation,
    validate_benchmark_semantic_evidence,
    validate_benchmark_validation_config,
    validate_benchmark_validator_probe,
    validate_benchmark_visual_diff,
    validate_provider_source_manifest,
)
METRIC_KEYS = (
    "layout_deviation_pt",
    "component_reuse_rate",
    "magic_numbers",
    "repair_iterations",
    "input_tokens",
    "manual_minutes",
)
ENVIRONMENT_KEYS = (
    "model",
    "reasoning",
    "appearance",
    "ui_framework",
    "adapter_runtime",
    "adapter_runtime_version",
    "provider_cli_name",
    "provider_cli_version",
    "provider_cli_launcher_path",
    "provider_cli_native_path",
    "provider_cli_launcher_hash",
    "provider_cli_native_hash",
    "provider_cli_package_json_hash",
    "code_baseline_hash",
    "shared_prompt_hash",
    "design_source_hash",
    "validation_config_hash",
    "run_plan_hash",
    "benchmark_case_hash",
    "executor_adapter_hash",
    "validator_id",
    "capture_adapter_hash",
    "capture_overlay_mode",
    "capture_overlay_hash",
    "capture_runtime_hash",
    "validator_adapter_hash",
)
EVIDENCE_KEYS = (
    "input_context",
    "implementation_output",
    "implementation_stdout",
    "implementation_stderr",
    "capture_stdout",
    "capture_stderr",
    "validation_stdout",
    "validation_stderr",
    "validation_report",
)


def _resolve(path_value: str, base_dir: Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else base_dir / path


def _verify_file_hash(path: Path, expected_hash: str, diagnostic_path: str) -> list[Diagnostic]:
    if not path.is_file():
        return [Diagnostic(diagnostic_path, "artifact.missing", f"file not found: {path}")]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest.lower() != expected_hash.lower():
        return [Diagnostic(diagnostic_path, "artifact.hash", f"sha256 mismatch for {path}")]
    return []


def _inside(base: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _frame_edge(frame: dict[str, Any], edge: str) -> float:
    if edge == "min_x":
        return float(frame["x"])
    if edge == "mid_x":
        return float(frame["x"]) + float(frame["width"]) / 2
    if edge == "max_x":
        return float(frame["x"]) + float(frame["width"])
    if edge == "min_y":
        return float(frame["y"])
    if edge == "mid_y":
        return float(frame["y"]) + float(frame["height"]) / 2
    if edge == "max_y":
        return float(frame["y"]) + float(frame["height"])
    raise ValueError(f"unsupported frame edge: {edge}")


def _derive_anchor(
    anchor: dict[str, Any],
    region_id: str,
    reference_frames: dict[str, dict[str, Any]],
    actual_frames: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    metric = anchor["metric"]
    reference_frame = reference_frames[region_id]
    actual_frame = actual_frames[region_id]
    if metric == "position":
        reference = [reference_frame["x"], reference_frame["y"]]
        actual = [actual_frame["x"], actual_frame["y"]]
    elif metric == "size":
        reference = [reference_frame["width"], reference_frame["height"]]
        actual = [actual_frame["width"], actual_frame["height"]]
    else:
        relative_id = anchor["relative_to_region_id"]
        reference = [anchor["reference_value"]]
        actual = [
            _frame_edge(actual_frame, anchor["region_edge"])
            - _frame_edge(actual_frames[relative_id], anchor["relative_edge"])
        ]
    deviation = max(abs(float(left) - float(right)) for left, right in zip(reference, actual))
    return {
        "id": anchor["id"],
        "metric": metric,
        "reference_value": reference,
        "actual_value": actual,
        "deviation_pt": deviation,
    }


def _derive_region_evidence(expected: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": expected["id"],
        "frame": observed["frame"],
        "structure": "passed" if observed.get("visible") is True and observed.get("parent_id") == expected.get("parent_id") and observed.get("child_ids") == expected.get("child_ids") else "failed",
        "semantic": "passed" if observed.get("runtime_type") == expected.get("runtime_type") and observed.get("accessibility_identifier") == expected.get("accessibility_identifier") else "failed",
    }


def _load_json_evidence(path: Path, diagnostic_path: str) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    try:
        data = load_json(path)
    except ValueError as exc:
        return None, [Diagnostic(diagnostic_path, "artifact.json", str(exc))]
    if not isinstance(data, dict):
        return None, [Diagnostic(diagnostic_path, "artifact.type", "expected JSON object")]
    return data, []


def _png_size(path: Path) -> tuple[tuple[int, int] | None, str | None]:
    data = path.read_bytes()
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None, "measured screenshot is not a PNG"
    offset = 8
    size: tuple[int, int] | None = None
    has_idat = False
    has_iend = False
    while offset < len(data):
        if offset + 12 > len(data):
            return None, "measured screenshot contains a truncated PNG chunk"
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            return None, "measured screenshot contains a truncated PNG chunk"
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : chunk_end])[0]
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            return None, "measured screenshot contains an invalid PNG CRC"
        if chunk_type == b"IHDR":
            if offset != 8 or length != 13:
                return None, "measured screenshot contains an invalid PNG IHDR"
            size = struct.unpack(">II", chunk_data[:8])
        elif chunk_type == b"IDAT":
            has_idat = True
        elif chunk_type == b"IEND":
            if length != 0 or chunk_end != len(data):
                return None, "measured screenshot contains an invalid PNG IEND"
            has_iend = True
            break
        offset = chunk_end
    if size is None or not has_idat or not has_iend:
        return None, "measured screenshot is not a complete PNG"
    return size, None


def _score_paeth(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    candidates = ((abs(estimate - left), left), (abs(estimate - above), above), (abs(estimate - upper_left), upper_left))
    return min(candidates, key=lambda item: item[0])[1]


def _score_decode_png(path: Path) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    offset = 8
    header: tuple[int, int, int, int] | None = None
    compressed: list[bytes] = []
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("truncated PNG chunk")
        length = int.from_bytes(data[offset : offset + 4], "big")
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("truncated PNG chunk payload")
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        expected_crc = int.from_bytes(data[offset + 8 + length : end], "big")
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != expected_crc:
            raise ValueError("invalid PNG CRC")
        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if bit_depth != 8 or color_type not in {0, 2, 4, 6} or compression != 0 or filtering != 0 or interlace != 0:
                raise ValueError("unsupported PNG encoding")
            header = (width, height, color_type, {0: 1, 2: 3, 4: 2, 6: 4}[color_type])
        elif kind == b"IDAT":
            compressed.append(payload)
        elif kind == b"IEND":
            break
        offset = end
    if header is None or not compressed:
        raise ValueError("incomplete PNG")
    width, height, color_type, channels = header
    row_size = width * channels
    decoded = zlib.decompress(b"".join(compressed))
    if len(decoded) != height * (row_size + 1):
        raise ValueError("unexpected PNG payload size")
    previous = [0] * row_size
    cursor = 0
    pixels: list[tuple[int, int, int, int]] = []
    for _ in range(height):
        filter_type = decoded[cursor]
        cursor += 1
        encoded = decoded[cursor : cursor + row_size]
        cursor += row_size
        row = [0] * row_size
        for index, byte in enumerate(encoded):
            left = row[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            predictor = {
                0: 0,
                1: left,
                2: above,
                3: (left + above) // 2,
                4: _score_paeth(left, above, upper_left),
            }.get(filter_type)
            if predictor is None:
                raise ValueError(f"unsupported PNG row filter: {filter_type}")
            row[index] = (byte + predictor) & 0xFF
        for index in range(0, row_size, channels):
            if color_type == 0:
                rgba = (row[index], row[index], row[index], 255)
            elif color_type == 4:
                rgba = (row[index], row[index], row[index], row[index + 1])
            elif color_type == 2:
                rgba = (row[index], row[index + 1], row[index + 2], 255)
            else:
                rgba = (row[index], row[index + 1], row[index + 2], row[index + 3])
            pixels.append(rgba)
        previous = row
    return width, height, pixels


def _score_pixel_difference_ratio(
    reference: tuple[int, int, list[tuple[int, int, int, int]]],
    actual: tuple[int, int, list[tuple[int, int, int, int]]],
    frame: dict[str, Any],
    ignore_frames: list[dict[str, Any]],
    max_channel_delta: int,
) -> float:
    width, height, reference_pixels = reference
    actual_width, actual_height, actual_pixels = actual
    if (width, height) != (actual_width, actual_height):
        raise ValueError("reference and actual PNG dimensions differ")
    x_range = range(max(0, math.floor(frame["x"])), min(width, math.ceil(frame["x"] + frame["width"])))
    y_range = range(max(0, math.floor(frame["y"])), min(height, math.ceil(frame["y"] + frame["height"])))
    compared = different = 0
    for y in y_range:
        for x in x_range:
            if any(item["x"] <= x < item["x"] + item["width"] and item["y"] <= y < item["y"] + item["height"] for item in ignore_frames):
                continue
            compared += 1
            index = y * width + x
            if any(abs(reference_pixels[index][channel] - actual_pixels[index][channel]) > max_channel_delta for channel in range(4)):
                different += 1
    return different / compared if compared else 0.0


def _verify_source_location(
    checkout: Path,
    location: dict[str, Any],
    expected_text: str,
    diagnostic_path: str,
) -> list[Diagnostic]:
    source = _resolve(location["path"], checkout)
    if not _inside(checkout, source):
        return [Diagnostic(diagnostic_path, "artifact.path", "source location must stay inside the run checkout")]
    if not source.is_file():
        return [Diagnostic(diagnostic_path, "artifact.missing", f"source location not found: {source}")]
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return [Diagnostic(diagnostic_path, "artifact.text", "source location must be UTF-8 text")]
    line = location["line"]
    if line > len(lines) or expected_text not in lines[line - 1]:
        return [Diagnostic(diagnostic_path, "artifact.location", f"line {line} does not contain expected evidence: {expected_text}")]
    return []


def _score_swift_code_lines(text: str) -> list[str]:
    output: list[str] = []
    comment_depth = 0
    terminator: str | None = None
    for raw in text.splitlines():
        code: list[str] = []
        cursor = 0
        while cursor < len(raw):
            if comment_depth:
                if raw.startswith("/*", cursor):
                    comment_depth += 1
                    cursor += 2
                elif raw.startswith("*/", cursor):
                    comment_depth -= 1
                    cursor += 2
                else:
                    cursor += 1
                continue
            if terminator is not None:
                if raw.startswith(terminator, cursor):
                    cursor += len(terminator)
                    terminator = None
                elif terminator == '"' and raw[cursor] == "\\":
                    cursor += 2
                else:
                    cursor += 1
                continue
            if raw.startswith("//", cursor):
                break
            if raw.startswith("/*", cursor):
                comment_depth = 1
                cursor += 2
                continue
            hashes = 0
            while cursor + hashes < len(raw) and raw[cursor + hashes] == "#":
                hashes += 1
            quote = cursor + hashes
            if quote < len(raw) and raw[quote] == '"':
                triple = raw.startswith('"""', quote)
                terminator = ('"""' if triple else '"') + ("#" * hashes)
                cursor = quote + (3 if triple else 1)
                continue
            code.append(raw[cursor])
            cursor += 1
        output.append("".join(code))
    return output


def _score_added_swift_literals(checkout: Path, baseline_commit: str) -> list[dict[str, Any]]:
    diff = subprocess.run(
        ["git", "diff", "--no-color", "--unified=0", baseline_commit, "--", "*.swift"],
        cwd=checkout,
        capture_output=True,
        text=True,
        check=False,
    )
    if diff.returncode != 0:
        raise ValueError(f"unable to replay Swift diff: {diff.stderr.strip()}")
    changed: dict[str, set[int]] = {}
    relative: str | None = None
    next_line: int | None = None
    for raw in diff.stdout.splitlines():
        if raw.startswith("+++ b/"):
            relative = raw[6:]
        elif raw.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,(\d+))?", raw)
            next_line = int(match.group(1)) if match else None
        elif raw.startswith("+") and not raw.startswith("+++") and relative is not None and next_line is not None:
            changed.setdefault(relative, set()).add(next_line)
            next_line += 1
        elif raw.startswith(" ") and next_line is not None:
            next_line += 1
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", "*.swift"],
        cwd=checkout,
        capture_output=True,
        text=True,
        check=False,
    )
    if untracked.returncode != 0:
        raise ValueError(f"unable to replay untracked Swift files: {untracked.stderr.strip()}")
    for relative in sorted(item for item in untracked.stdout.splitlines() if item):
        source = checkout / relative
        if not source.is_file():
            raise ValueError(f"untracked Swift source is not a regular file: {relative}")
        changed[relative] = set(range(1, len(source.read_text(encoding="utf-8").splitlines()) + 1))
    visual_context = re.compile(
        r"\b(?:CGRect|CGSize|CGPoint|UIEdgeInsets|frame|bounds|constraint|constant|spacing|padding|offset|cornerRadius|font|RGB|RGBA|UIColor|shadow|opacity|alpha|width|height|inset|margin|radius)\b",
        re.IGNORECASE,
    )
    named_visual = re.compile(
        r"(?:spacing|padding|offset|corner|radius|font|color|shadow|opacity|alpha|width|height|inset|margin|size|dimension|layout)",
        re.IGNORECASE,
    )
    declaration = re.compile(r"\b(?:let|var)\s+([A-Za-z_][A-Za-z0-9_]*)[^=]*=")
    number = re.compile(r"(?<![A-Za-z0-9_])(-?(?:0x[0-9A-Fa-f]+|\d+\.\d+|\.\d+|\d+))(?![A-Za-z0-9_])")
    evidence: list[dict[str, Any]] = []
    for relative in sorted(changed):
        lines = _score_swift_code_lines((checkout / relative).read_text(encoding="utf-8"))
        for line_number in sorted(changed[relative]):
            if line_number > len(lines):
                raise ValueError(f"changed Swift line is outside final source: {relative}:{line_number}")
            code = lines[line_number - 1]
            if not visual_context.search(code):
                continue
            binding = declaration.search(code)
            if binding and named_visual.search(binding.group(1)):
                continue
            evidence.extend(
                {"kind": "layout", "value": match.group(1), "location": {"path": relative, "line": line_number}}
                for match in number.finditer(code)
            )
    return evidence


def _verify_symbol_declaration_location(
    checkout: Path,
    location: dict[str, Any],
    symbol: str,
    diagnostic_path: str,
) -> list[Diagnostic]:
    diagnostics = _verify_source_location(checkout, location, symbol, diagnostic_path)
    if diagnostics:
        return diagnostics
    source = _resolve(location["path"], checkout)
    lines = _score_swift_code_lines(source.read_text(encoding="utf-8"))
    line = lines[location["line"] - 1]
    declaration = re.compile(rf"\b(?:class|struct|enum|actor|protocol|typealias)\s+{re.escape(symbol)}\b")
    if declaration.search(line) is None:
        return [Diagnostic(diagnostic_path, "artifact.location", f"line {location['line']} is not a declaration of {symbol}")]
    return []


def _git_bytes(checkout: Path, args: list[str]) -> tuple[int, bytes, bytes]:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(["git", *args], cwd=checkout, env=environment, capture_output=True, check=False)
    return result.returncode, result.stdout, result.stderr


def _canonical_string_set_sha256(values: set[str]) -> str:
    canonical = json.dumps(sorted(values), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _scope_allows_path(relative: str, scope_entries: list[dict[str, str]]) -> bool:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or relative != path.as_posix():
        return False
    return any(
        (entry.get("kind") == "file" and relative == str(entry.get("path", "")).rstrip("/"))
        or (
            entry.get("kind") == "directory"
            and relative.startswith(str(entry.get("path", "")).rstrip("/") + "/")
        )
        for entry in scope_entries
    )


def _scope_allows_directory(relative: str, scope_entries: list[dict[str, str]]) -> bool:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or relative != path.as_posix():
        return False
    for entry in scope_entries:
        value = str(entry.get("path", "")).rstrip("/")
        if value.startswith(relative + "/"):
            return True
        if entry.get("kind") == "directory" and (relative == value or relative.startswith(value + "/")):
            return True
    return False


def _provider_git_metadata_sha256(worktree: Path) -> tuple[str | None, str | None]:
    git_dir = worktree / ".git"
    if not git_dir.is_dir() or git_dir.is_symlink():
        return None, "provider worktree .git metadata is missing or invalid"
    entries: list[dict[str, Any]] = []
    for path in sorted(git_dir.rglob("*")):
        if path.is_symlink():
            return None, f"provider Git metadata contains a symlink: {path.relative_to(git_dir)}"
        if not path.is_file():
            continue
        relative = path.relative_to(git_dir).as_posix()
        entries.append(
            {
                "path": relative,
                "mode": stat.S_IMODE(path.stat().st_mode),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    canonical = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest(), None


def _git_tree_manifest(worktree: Path, commit: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    returncode, raw, stderr = _git_bytes(worktree, ["ls-tree", "-r", "-l", "-z", commit])
    if returncode != 0:
        return None, f"unable to enumerate provider baseline tree: {stderr.decode(errors='replace').strip()}"
    files: list[dict[str, Any]] = []
    try:
        for record in raw.split(b"\0"):
            if not record:
                continue
            header, raw_path = record.split(b"\t", 1)
            mode, object_type, object_id, raw_size = header.decode("ascii").split()
            if object_type != "blob" or mode not in {"100644", "100755"} or raw_size == "-":
                return None, "provider baseline tree contains unsupported Git entries"
            files.append(
                {
                    "path": raw_path.decode("utf-8", errors="strict"),
                    "git_mode": mode,
                    "blob_sha1": object_id,
                    "bytes": int(raw_size),
                }
            )
    except (UnicodeDecodeError, ValueError) as exc:
        return None, f"unable to decode provider baseline tree: {exc}"
    return sorted(files, key=lambda item: item["path"]), None


def _validate_provider_manifest(manifest: dict[str, Any], diagnostic_path: str) -> list[Diagnostic]:
    diagnostics, _ = validate_provider_source_manifest(manifest)
    return [Diagnostic(f"{diagnostic_path}:{item.path}", item.code, item.message) for item in diagnostics]


def _verify_provider_worktree(
    worktree: Path,
    worktree_identity: dict[str, Any],
    manifest: dict[str, Any],
    implementation_path: Path,
    evaluator_checkout: Path,
    diagnostic_path: str,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not worktree.is_dir() or worktree.is_symlink():
        return [Diagnostic(diagnostic_path, "artifact.missing", "provider worktree is missing or invalid")]
    baseline = worktree_identity.get("baseline_commit", "")
    head_code, head, _ = _git_bytes(worktree, ["rev-parse", "HEAD"])
    branch_code, branch, _ = _git_bytes(worktree, ["symbolic-ref", "--short", "-q", "HEAD"])
    refs_code, refs, _ = _git_bytes(worktree, ["for-each-ref", "--format=%(refname)"])
    remotes_code, remotes, _ = _git_bytes(worktree, ["remote"])
    if head_code != 0 or head.decode().strip() != baseline or branch_code not in {0, 1} or branch.strip():
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.isolation", "provider worktree is not at its frozen detached baseline"))
    if refs_code != 0 or refs.strip() or remotes_code != 0 or remotes.strip():
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.isolation", "provider worktree contains refs or remotes"))
    if (worktree / ".git/objects/info/alternates").exists():
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.isolation", "provider worktree uses alternate Git objects"))
    actual_code, actual_raw, _ = _git_bytes(worktree, ["cat-file", "--batch-all-objects", "--batch-check=%(objectname)"])
    expected_code, expected_raw, _ = _git_bytes(worktree, ["rev-list", "--objects", "--no-object-names", baseline])
    if actual_code != 0 or expected_code != 0:
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.isolation", "unable to enumerate provider worktree objects"))
    else:
        actual = {line.decode().strip() for line in actual_raw.splitlines() if line.strip()}
        expected = {line.decode().strip() for line in expected_raw.splitlines() if line.strip()}
        if actual != expected:
            diagnostics.append(Diagnostic(diagnostic_path, "artifact.isolation", "provider worktree object set differs from baseline closure"))
        if _canonical_string_set_sha256(actual) != worktree_identity.get("object_set_sha256"):
            diagnostics.append(Diagnostic(diagnostic_path, "artifact.linkage", "provider worktree object-set identity changed"))
    metadata_hash, metadata_error = _provider_git_metadata_sha256(worktree)
    if metadata_error is not None or metadata_hash != worktree_identity.get("git_metadata_sha256"):
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.isolation", metadata_error or "provider Git metadata identity changed"))
    tree, tree_error = _git_tree_manifest(worktree, baseline)
    if tree_error is not None or tree != manifest.get("files"):
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.manifest", tree_error or "provider baseline tree differs from source manifest"))

    root = worktree.resolve()
    invalid_paths: list[str] = []
    provider_snapshot: dict[str, tuple[int, str]] = {}
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        if current_path == root and ".git" in directories:
            directories.remove(".git")
        for name in list(directories):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or not _scope_allows_directory(relative, manifest.get("scope_entries", [])):
                invalid_paths.append(relative + "/")
                directories.remove(name)
        for name in files:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode) or not _scope_allows_path(relative, manifest.get("scope_entries", [])):
                invalid_paths.append(relative)
            else:
                provider_snapshot[relative] = (
                    stat.S_IMODE(mode),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
    if invalid_paths:
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.scope", f"provider worktree contains out-of-scope paths: {sorted(invalid_paths)}"))
    evaluator_snapshot: dict[str, tuple[int, str]] = {}
    evaluator_invalid: list[str] = []
    if evaluator_checkout.is_dir() and not evaluator_checkout.is_symlink():
        evaluator_root = evaluator_checkout.resolve()
        for current, directories, files in os.walk(evaluator_root, topdown=True, followlinks=False):
            current_path = Path(current)
            if current_path == evaluator_root and ".git" in directories:
                directories.remove(".git")
            for name in list(directories):
                path = current_path / name
                relative = path.relative_to(evaluator_root).as_posix()
                if path.is_symlink():
                    if _scope_allows_directory(relative, manifest.get("scope_entries", [])):
                        evaluator_invalid.append(relative + "/")
                    directories.remove(name)
                elif not _scope_allows_directory(relative, manifest.get("scope_entries", [])):
                    directories.remove(name)
            for name in files:
                path = current_path / name
                relative = path.relative_to(evaluator_root).as_posix()
                if not _scope_allows_path(relative, manifest.get("scope_entries", [])):
                    continue
                mode = path.lstat().st_mode
                if not stat.S_ISREG(mode):
                    evaluator_invalid.append(relative)
                else:
                    evaluator_snapshot[relative] = (
                        stat.S_IMODE(mode),
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
    else:
        evaluator_invalid.append("checkout/")
    if evaluator_invalid:
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.scope", f"evaluator scope contains unsupported paths: {sorted(evaluator_invalid)}"))
    elif provider_snapshot != evaluator_snapshot:
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.patch", "provider and evaluator scoped filesystem snapshots differ"))
    provider_patch, patch_error = _capture_checkout_patch(worktree, baseline)
    if patch_error is not None:
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.patch", patch_error))
    elif implementation_path.is_file() and provider_patch != implementation_path.read_bytes():
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.patch", "provider worktree patch does not match archived implementation patch"))
    return diagnostics


def _verify_pinned_tree_slice(checkout: Path, commit: str, diagnostic_path: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if (checkout / ".git" / "objects" / "info" / "alternates").exists():
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.isolation", "measured checkout must not use alternate Git objects"))
    refs_code, refs, _ = _git_bytes(checkout, ["for-each-ref", "--format=%(refname)"])
    remotes_code, remotes, _ = _git_bytes(checkout, ["remote"])
    if refs_code != 0 or refs.strip() or remotes_code != 0 or remotes.strip():
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.isolation", "measured checkout must not contain refs or remotes"))
    actual_code, actual_raw, _ = _git_bytes(
        checkout,
        ["cat-file", "--batch-all-objects", "--batch-check=%(objectname)"],
    )
    expected_code, expected_raw, _ = _git_bytes(
        checkout,
        ["rev-list", "--objects", "--no-object-names", f"{commit}^{{tree}}"],
    )
    if actual_code != 0 or expected_code != 0:
        diagnostics.append(Diagnostic(diagnostic_path, "artifact.isolation", "unable to enumerate pinned checkout object closure"))
        return diagnostics
    actual = {line.decode().strip() for line in actual_raw.splitlines() if line.strip()}
    expected = {commit, *[line.decode().strip() for line in expected_raw.splitlines() if line.strip()]}
    if actual != expected:
        diagnostics.append(
            Diagnostic(
                diagnostic_path,
                "artifact.isolation",
                f"measured checkout object set exceeds or misses the pinned tree slice: {sorted(actual ^ expected)[:20]}",
            )
        )
    return diagnostics


def _capture_checkout_patch(checkout: Path, baseline_commit: str) -> tuple[bytes | None, str | None]:
    returncode, tracked, stderr = _git_bytes(
        checkout,
        [
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-renames",
            "--full-index",
            "--binary",
            baseline_commit,
            "--",
        ],
    )
    if returncode != 0:
        return None, f"unable to diff checkout: {stderr.decode(errors='replace').strip()}"
    returncode, raw_untracked, stderr = _git_bytes(checkout, ["ls-files", "--others", "--exclude-standard", "-z"])
    if returncode != 0:
        return None, f"unable to list untracked files: {stderr.decode(errors='replace').strip()}"
    content = bytearray(tracked)
    for raw_path in sorted(item for item in raw_untracked.split(b"\0") if item):
        relative = raw_path.decode("utf-8")
        source = _resolve(relative, checkout)
        if not _inside(checkout, source) or not source.is_file():
            return None, f"untracked output is not a contained regular file: {relative}"
        returncode, diff, stderr = _git_bytes(
            checkout,
            [
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                "--full-index",
                "--no-index",
                "--binary",
                "--",
                "/dev/null",
                relative,
            ],
        )
        if returncode not in (0, 1):
            return None, f"unable to diff untracked file: {stderr.decode(errors='replace').strip()}"
        content.extend(diff)
    return bytes(content), None


def _replay_provider_stream(content: bytes) -> tuple[str | None, dict[str, int] | None, str | None]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, None, f"provider stdout is not UTF-8: {exc}"
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            return None, None, f"provider stdout line {line_number} is not JSON: {exc.msg}"
        if not isinstance(event, dict):
            return None, None, f"provider stdout line {line_number} is not an object"
        events.append(event)
    canonical = b"".join(
        (json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for event in events
    )
    if canonical != content:
        return None, None, "provider stdout is not the canonical JSONL stream"
    thread_started = [index for index, event in enumerate(events) if event.get("type") == "thread.started"]
    turn_started = [index for index, event in enumerate(events) if event.get("type") == "turn.started"]
    turn_completed = [index for index, event in enumerate(events) if event.get("type") == "turn.completed"]
    if (
        any(event.get("type") in {"turn.failed", "error"} for event in events)
        or len(thread_started) != 1
        or len(turn_started) != 1
        or len(turn_completed) != 1
        or not (thread_started[0] < turn_started[0] < turn_completed[0])
        or turn_completed[0] != len(events) - 1
    ):
        return None, None, "provider stdout must contain one ordered successful thread/turn sequence"
    thread_id = events[thread_started[0]].get("thread_id")
    if not isinstance(thread_id, str) or not thread_id:
        return None, None, "provider stdout thread.started is missing thread_id"
    usage = events[turn_completed[0]].get("usage")
    keys = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
    if not isinstance(usage, dict) or any(
        not isinstance(usage.get(key), int) or isinstance(usage.get(key), bool) or usage[key] < 0
        for key in keys
    ):
        return None, None, "provider stdout turn.completed has invalid usage"
    return thread_id, {key: usage[key] for key in keys}, None


def _verify_nested_evidence(
    artifact: dict[str, Any],
    artifact_path: Path,
    benchmark: dict[str, Any],
    candidate_index: int,
    cross_run: dict[str, list[str]],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    base_key = f"$.candidates[{candidate_index}].run.artifact_path"
    input_ref = artifact["evidence"]["input_context"]
    input_path = _resolve(input_ref["path"], artifact_path.parent)
    input_data, input_errors = _load_json_evidence(input_path, f"{base_key}:$.evidence.input_context")
    diagnostics.extend(input_errors)
    if input_data is None:
        return diagnostics
    if input_data.get("input_context_version") != "1.2.0":
        diagnostics.append(Diagnostic(f"{base_key}:$.evidence.input_context", "artifact.contract", "measured input context must use benchmark-input-context-v1"))
        return diagnostics
    input_diagnostics, _ = validate_benchmark_input_context(input_data)
    diagnostics.extend(Diagnostic(f"{base_key}:input:{item.path}", item.code, item.message) for item in input_diagnostics)
    if input_data.get("variant") != artifact.get("variant"):
        diagnostics.append(Diagnostic(f"{base_key}:input", "artifact.variant", "input context variant does not match run artifact"))
    if input_data.get("case_id") != benchmark.get("case_id"):
        diagnostics.append(Diagnostic(f"{base_key}:input:$.case_id", "artifact.linkage", "input context case_id does not match benchmark"))
    input_environment = input_data.get("environment") if isinstance(input_data.get("environment"), dict) else {}
    benchmark_environment = benchmark["environment"]
    viewport_match = re.fullmatch(r"([0-9]+)x([0-9]+)@([0-9.]+)x", benchmark_environment["viewport"])
    expected_input_environment = {
        "task_mode": benchmark_environment["task_mode"],
        "screen": benchmark_environment["screen"],
        "state": benchmark_environment["state"],
        "locale": benchmark_environment["locale"],
        "appearance": benchmark_environment["appearance"],
        "ui_framework": benchmark_environment["ui_framework"],
    }
    if viewport_match:
        expected_input_environment["viewport"] = {
            "width": int(viewport_match.group(1)),
            "height": int(viewport_match.group(2)),
        }
        expected_input_environment["scale"] = float(viewport_match.group(3))
    for key, value in expected_input_environment.items():
        if input_environment.get(key) != value:
            diagnostics.append(Diagnostic(f"{base_key}:input:$.environment.{key}", "artifact.environment", f"input context does not match benchmark: {key}"))

    plan_ref = input_data.get("run_plan")
    plan: dict[str, Any] | None = None
    if isinstance(plan_ref, dict):
        cross_run.setdefault("plan_sha256", []).append(plan_ref["sha256"])
        plan_path = _resolve(plan_ref["path"], input_path.parent)
        plan_key = f"{base_key}:input:$.run_plan"
        if not _inside(artifact_path.parent, plan_path):
            diagnostics.append(Diagnostic(plan_key, "artifact.path", "run plan must stay inside the run artifact directory"))
        else:
            diagnostics.extend(_verify_file_hash(plan_path, plan_ref["sha256"], plan_key))
            if plan_ref["sha256"] != benchmark_environment["run_plan_hash"]:
                diagnostics.append(Diagnostic(plan_key, "artifact.environment", "run plan hash does not match benchmark"))
            if plan_ref["sha256"] != input_data.get("plan_sha256"):
                diagnostics.append(Diagnostic(plan_key, "artifact.linkage", "run plan hash does not match plan_sha256"))
            plan, errors = _load_json_evidence(plan_path, plan_key)
            diagnostics.extend(errors)
            if plan is not None:
                plan_diagnostics, _ = validate_benchmark_run_plan(plan)
                diagnostics.extend(Diagnostic(f"{plan_key}:{item.path}", item.code, item.message) for item in plan_diagnostics)
                if plan.get("evidence_status") != "measured":
                    diagnostics.append(Diagnostic(plan_key, "artifact.synthetic", "measured evidence requires a measured run plan"))
                executor = plan.get("executor") if isinstance(plan.get("executor"), dict) else {}
                for key in ("model", "reasoning"):
                    if executor.get(key) != benchmark["environment"].get(key):
                        diagnostics.append(Diagnostic(f"{plan_key}:$.executor.{key}", "artifact.environment", f"run plan does not match benchmark: {key}"))
                plan_provider = executor.get("provider_cli") if isinstance(executor.get("provider_cli"), dict) else {}
                expected_plan_provider = {
                    "name": benchmark_environment.get("provider_cli_name"),
                    "version": benchmark_environment.get("provider_cli_version"),
                    "launcher_path": benchmark_environment.get("provider_cli_launcher_path"),
                    "native_path": benchmark_environment.get("provider_cli_native_path"),
                    "launcher_sha256": benchmark_environment.get("provider_cli_launcher_hash"),
                    "native_sha256": benchmark_environment.get("provider_cli_native_hash"),
                    "package_json_sha256": benchmark_environment.get("provider_cli_package_json_hash"),
                }
                if plan_provider != expected_plan_provider:
                    diagnostics.append(Diagnostic(f"{plan_key}:$.executor.provider_cli", "artifact.environment", "run plan provider identity does not match benchmark"))
                if ((plan.get("validator") or {}).get("id") if isinstance(plan.get("validator"), dict) else None) != benchmark_environment["validator_id"]:
                    diagnostics.append(Diagnostic(f"{plan_key}:$.validator.id", "artifact.environment", "validator id does not match benchmark"))
                runtime = ((plan.get("validator") or {}).get("capture_runtime") if isinstance(plan.get("validator"), dict) else None)
                runtime_hash = hashlib.sha256(json.dumps(runtime, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
                if runtime_hash != benchmark_environment.get("capture_runtime_hash"):
                    diagnostics.append(Diagnostic(f"{plan_key}:$.validator.capture_runtime", "artifact.environment", "capture runtime hash does not match benchmark"))

    adapter_ref = input_data.get("executor_adapter")
    if isinstance(adapter_ref, dict):
        cross_run.setdefault("executor_adapter_sha256", []).append(adapter_ref["sha256"])
        adapter_path = _resolve(adapter_ref["path"], input_path.parent)
        adapter_key = f"{base_key}:input:$.executor_adapter"
        if not _inside(artifact_path.parent, adapter_path):
            diagnostics.append(Diagnostic(adapter_key, "artifact.path", "executor adapter must stay inside the run artifact directory"))
        else:
            diagnostics.extend(_verify_file_hash(adapter_path, adapter_ref["sha256"], adapter_key))
            if adapter_ref["sha256"] != benchmark_environment["executor_adapter_hash"]:
                diagnostics.append(Diagnostic(adapter_key, "artifact.environment", "executor adapter hash does not match benchmark"))
            plan_adapter = ((plan or {}).get("executor") or {}).get("adapter") if isinstance((plan or {}).get("executor"), dict) else None
            if isinstance(plan_adapter, dict) and adapter_ref["sha256"] != plan_adapter.get("sha256"):
                diagnostics.append(Diagnostic(adapter_key, "artifact.linkage", "executor adapter hash does not match run plan"))

    capture_ref = input_data.get("capture_adapter")
    if isinstance(capture_ref, dict):
        cross_run.setdefault("capture_adapter_sha256", []).append(capture_ref["sha256"])
        capture_path = _resolve(capture_ref["path"], input_path.parent)
        capture_key = f"{base_key}:input:$.capture_adapter"
        if not _inside(artifact_path.parent, capture_path):
            diagnostics.append(Diagnostic(capture_key, "artifact.path", "capture adapter must stay inside the run artifact directory"))
        else:
            diagnostics.extend(_verify_file_hash(capture_path, capture_ref["sha256"], capture_key))
            if capture_ref["sha256"] != benchmark_environment["capture_adapter_hash"]:
                diagnostics.append(Diagnostic(capture_key, "artifact.environment", "capture adapter hash does not match benchmark"))
            plan_capture = ((plan or {}).get("validator") or {}).get("capture_adapter") if isinstance((plan or {}).get("validator"), dict) else None
            if isinstance(plan_capture, dict) and capture_ref["sha256"] != plan_capture.get("sha256"):
                diagnostics.append(Diagnostic(capture_key, "artifact.linkage", "capture adapter hash does not match run plan"))

    input_overlay = input_data.get("capture_overlay") if isinstance(input_data.get("capture_overlay"), dict) else {}
    artifact_overlay = artifact.get("capture_overlay") if isinstance(artifact.get("capture_overlay"), dict) else {}
    plan_overlay = ((plan or {}).get("validator") or {}).get("capture_overlay") if isinstance((plan or {}).get("validator"), dict) else {}
    overlay_mode = input_overlay.get("mode")
    cross_run.setdefault("capture_overlay_identity", []).append(
        (input_overlay.get("artifact") or {}).get("sha256") if overlay_mode == "git-patch" else "none"
    )
    if artifact_overlay != input_overlay:
        diagnostics.append(Diagnostic(f"{base_key}:input:$.capture_overlay", "artifact.linkage", "input context capture overlay does not match run artifact"))
    if isinstance(plan_overlay, dict) and plan_overlay.get("mode") != overlay_mode:
        diagnostics.append(Diagnostic(f"{base_key}:input:$.capture_overlay.mode", "artifact.linkage", "capture overlay mode does not match run plan"))
    if benchmark_environment.get("capture_overlay_mode") != overlay_mode:
        diagnostics.append(Diagnostic(f"{base_key}:input:$.capture_overlay.mode", "artifact.environment", "capture overlay mode does not match benchmark"))
    if overlay_mode == "git-patch":
        overlay_ref = input_overlay.get("artifact") if isinstance(input_overlay.get("artifact"), dict) else {}
        overlay_path = _resolve(overlay_ref.get("path", ""), input_path.parent)
        overlay_key = f"{base_key}:input:$.capture_overlay.artifact"
        if not _inside(artifact_path.parent, overlay_path):
            diagnostics.append(Diagnostic(overlay_key, "artifact.path", "capture overlay must stay inside the run artifact directory"))
        else:
            diagnostics.extend(_verify_file_hash(overlay_path, overlay_ref.get("sha256", ""), overlay_key))
        plan_overlay_ref = plan_overlay.get("artifact") if isinstance(plan_overlay, dict) and isinstance(plan_overlay.get("artifact"), dict) else {}
        if overlay_ref.get("sha256") != plan_overlay_ref.get("sha256"):
            diagnostics.append(Diagnostic(overlay_key, "artifact.linkage", "capture overlay hash does not match run plan"))
        if overlay_ref.get("sha256") != benchmark_environment.get("capture_overlay_hash"):
            diagnostics.append(Diagnostic(overlay_key, "artifact.environment", "capture overlay hash does not match benchmark"))
    elif benchmark_environment.get("capture_overlay_hash") is not None:
        diagnostics.append(Diagnostic(f"{base_key}:input:$.capture_overlay", "artifact.environment", "none capture overlay requires a null benchmark hash"))

    input_provider_scope = input_data.get("provider_source_scope") if isinstance(input_data.get("provider_source_scope"), dict) else None
    if input_provider_scope is None:
        diagnostics.append(Diagnostic(f"{base_key}:input:$.provider_source_scope", "artifact.contract", "provider source scope must be explicitly archived"))
        input_provider_scope = {"mode": "missing"}
    provider_scope_mode = input_provider_scope.get("mode")
    provider_manifest: dict[str, Any] | None = None
    worktree_identity = input_provider_scope.get("worktree") if isinstance(input_provider_scope.get("worktree"), dict) else {}
    cross_run.setdefault("provider_source_scope_identity", []).append(
        json.dumps(
            {
                "mode": provider_scope_mode,
                "manifest_sha256": (input_provider_scope.get("artifact") or {}).get("sha256"),
                "baseline_commit": worktree_identity.get("baseline_commit"),
                "object_set_sha256": worktree_identity.get("object_set_sha256"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    if provider_scope_mode == "allowlist":
        scope_ref = input_provider_scope.get("artifact") if isinstance(input_provider_scope.get("artifact"), dict) else {}
        scope_path = _resolve(scope_ref.get("path", ""), input_path.parent)
        scope_key = f"{base_key}:input:$.provider_source_scope.artifact"
        if not _inside(artifact_path.parent, scope_path):
            diagnostics.append(Diagnostic(scope_key, "artifact.path", "provider source manifest must stay inside the run artifact directory"))
        else:
            diagnostics.extend(_verify_file_hash(scope_path, scope_ref.get("sha256", ""), scope_key))
            provider_manifest, errors = _load_json_evidence(scope_path, scope_key)
            diagnostics.extend(errors)
            if provider_manifest is not None:
                diagnostics.extend(_validate_provider_manifest(provider_manifest, scope_key))
                for key in ("file_count", "total_bytes", "content_sha256"):
                    if provider_manifest.get(key) != input_provider_scope.get(key):
                        diagnostics.append(Diagnostic(scope_key, "artifact.linkage", f"provider source manifest does not match input context: {key}"))
                worktree_path = _resolve(str(worktree_identity.get("path", "")), input_path.parent)
                worktree_key = f"{base_key}:input:$.provider_source_scope.worktree"
                implementation_ref = artifact.get("evidence", {}).get("implementation_output", {})
                implementation_path = _resolve(str(implementation_ref.get("path", "")), artifact_path.parent)
                if not _inside(artifact_path.parent, worktree_path):
                    diagnostics.append(Diagnostic(worktree_key, "artifact.path", "provider worktree must stay inside the run artifact directory"))
                elif not _inside(artifact_path.parent, implementation_path):
                    diagnostics.append(Diagnostic(worktree_key, "artifact.path", "implementation patch must stay inside the run artifact directory"))
                else:
                    diagnostics.extend(
                        _verify_provider_worktree(
                            worktree_path,
                            worktree_identity,
                            provider_manifest,
                            implementation_path,
                            artifact_path.parent / "checkout",
                            worktree_key,
                        )
                    )
    elif provider_scope_mode != "full-tree":
        diagnostics.append(Diagnostic(f"{base_key}:input:$.provider_source_scope.mode", "artifact.contract", "unsupported or missing provider source scope mode"))

    input_setup = input_data.get("evaluator_dependency_setup") if isinstance(input_data.get("evaluator_dependency_setup"), dict) else {"mode": "none"}
    plan_runtime = ((plan or {}).get("validator") or {}).get("capture_runtime") if isinstance((plan or {}).get("validator"), dict) else {}
    plan_setup = plan_runtime.get("evaluator_dependency_setup", {"mode": "none"}) if isinstance(plan_runtime, dict) else {"mode": "none"}
    setup_mode = input_setup.get("mode", "none")
    cross_run.setdefault("evaluator_dependency_identity", []).append(
        (input_setup.get("artifact") or {}).get("sha256") if setup_mode != "none" else "none"
    )
    if plan_setup.get("mode", "none") != setup_mode:
        diagnostics.append(Diagnostic(f"{base_key}:input:$.evaluator_dependency_setup.mode", "artifact.linkage", "evaluator dependency setup mode does not match run plan"))
    if setup_mode != "none":
        setup_ref = input_setup.get("artifact") if isinstance(input_setup.get("artifact"), dict) else {}
        setup_path = _resolve(setup_ref.get("path", ""), input_path.parent)
        setup_key = f"{base_key}:input:$.evaluator_dependency_setup.artifact"
        if not _inside(artifact_path.parent, setup_path):
            diagnostics.append(Diagnostic(setup_key, "artifact.path", "evaluator dependency generator must stay inside the run artifact directory"))
        else:
            diagnostics.extend(_verify_file_hash(setup_path, setup_ref.get("sha256", ""), setup_key))
        plan_generator = plan_setup.get("generator") if isinstance(plan_setup.get("generator"), dict) else {}
        if setup_ref.get("sha256") != plan_generator.get("sha256"):
            diagnostics.append(Diagnostic(setup_key, "artifact.linkage", "evaluator dependency generator hash does not match run plan"))

    validator_ref = input_data.get("validator_adapter")
    if isinstance(validator_ref, dict):
        cross_run.setdefault("validator_adapter_sha256", []).append(validator_ref["sha256"])
        validator_path = _resolve(validator_ref["path"], input_path.parent)
        validator_key = f"{base_key}:input:$.validator_adapter"
        if not _inside(artifact_path.parent, validator_path):
            diagnostics.append(Diagnostic(validator_key, "artifact.path", "validator adapter must stay inside the run artifact directory"))
        else:
            diagnostics.extend(_verify_file_hash(validator_path, validator_ref["sha256"], validator_key))
            if validator_ref["sha256"] != benchmark_environment["validator_adapter_hash"]:
                diagnostics.append(Diagnostic(validator_key, "artifact.environment", "validator adapter hash does not match benchmark"))
            plan_validator = ((plan or {}).get("validator") or {}).get("adapter") if isinstance((plan or {}).get("validator"), dict) else None
            if isinstance(plan_validator, dict) and validator_ref["sha256"] != plan_validator.get("sha256"):
                diagnostics.append(Diagnostic(validator_key, "artifact.linkage", "validator adapter hash does not match run plan"))

    case_ref = input_data.get("benchmark_case")
    if isinstance(case_ref, dict):
        cross_run.setdefault("benchmark_case_sha256", []).append(case_ref["sha256"])
        case_path = _resolve(case_ref["path"], input_path.parent)
        case_key = f"{base_key}:input:$.benchmark_case"
        if not _inside(artifact_path.parent, case_path):
            diagnostics.append(Diagnostic(case_key, "artifact.path", "benchmark case must stay inside the run artifact directory"))
        else:
            diagnostics.extend(_verify_file_hash(case_path, case_ref["sha256"], case_key))
            if case_ref["sha256"] != benchmark_environment["benchmark_case_hash"]:
                diagnostics.append(Diagnostic(case_key, "artifact.environment", "benchmark case hash does not match benchmark"))
            plan_case = (plan or {}).get("case")
            if isinstance(plan_case, dict) and case_ref["sha256"] != plan_case.get("sha256"):
                diagnostics.append(Diagnostic(case_key, "artifact.linkage", "benchmark case hash does not match run plan"))
            case_data, errors = _load_json_evidence(case_path, case_key)
            diagnostics.extend(errors)
            if case_data is not None:
                case_diagnostics, _ = validate_benchmark_case(case_data)
                diagnostics.extend(Diagnostic(f"{case_key}:{item.path}", item.code, item.message) for item in case_diagnostics)
                if case_data.get("case_id") != benchmark.get("case_id"):
                    diagnostics.append(Diagnostic(f"{case_key}:$.case_id", "artifact.linkage", "benchmark case does not match benchmark case_id"))
                case_scope = ((case_data.get("source") or {}).get("code") or {}).get("provider_source_scope")
                if isinstance(case_scope, dict):
                    expected_scope = {
                        "file_count": case_scope.get("expected_file_count"),
                        "total_bytes": case_scope.get("expected_total_bytes"),
                        "content_sha256": case_scope.get("expected_content_sha256"),
                    }
                    if provider_scope_mode != "allowlist" or provider_manifest is None:
                        diagnostics.append(Diagnostic(f"{case_key}:$.source.code.provider_source_scope", "artifact.linkage", "benchmark case provider source allowlist is missing from input context"))
                    elif (
                        any(provider_manifest.get(key) != value for key, value in expected_scope.items())
                        or provider_manifest.get("scope_entries") != case_scope.get("entries")
                        or provider_manifest.get("code_baseline_commit") != ((case_data.get("source") or {}).get("code") or {}).get("git_commit")
                    ):
                        diagnostics.append(Diagnostic(f"{case_key}:$.source.code.provider_source_scope", "artifact.linkage", "provider source manifest identity does not match benchmark case"))
                elif provider_scope_mode != "full-tree":
                    diagnostics.append(Diagnostic(f"{base_key}:input:$.provider_source_scope", "artifact.linkage", "input context introduced an undeclared provider source allowlist"))
    nested_inputs: dict[str, Path] = {}
    expected_input_files = {item["path"] for item in input_data.get("inputs", [])}
    input_directory = artifact_path.parent / "input"
    actual_input_files = {
        path.relative_to(artifact_path.parent).as_posix()
        for path in input_directory.rglob("*")
        if path.is_file()
    } if input_directory.is_dir() else set()
    if actual_input_files != expected_input_files:
        diagnostics.append(Diagnostic(f"{base_key}:input", "artifact.coverage", f"run input file set differs from input context: {sorted(actual_input_files ^ expected_input_files)}"))
    if input_directory.is_dir() and any(path.is_dir() for path in input_directory.iterdir()):
        diagnostics.append(Diagnostic(f"{base_key}:input", "artifact.path", "run input directory must not contain nested directories"))
    for index, item in enumerate(input_data.get("inputs", [])):
        nested_path = _resolve(item["path"], input_path.parent)
        key = f"{base_key}:input:$.inputs[{index}]"
        if not _inside(artifact_path.parent, nested_path):
            diagnostics.append(Diagnostic(key, "artifact.path", "input evidence must stay inside the run artifact directory"))
            continue
        diagnostics.extend(_verify_file_hash(nested_path, item["sha256"], key))
        nested_inputs[item["kind"]] = nested_path
        expected_hash = {
            "shared-prompt": benchmark_environment["shared_prompt_hash"],
            "validation-config": benchmark_environment["validation_config_hash"],
        }.get(item["kind"])
        if expected_hash is not None and item["sha256"] != expected_hash:
            diagnostics.append(Diagnostic(key, "artifact.environment", f"input hash does not match benchmark: {item['kind']}"))

    validation_path = nested_inputs.get("validation-config")
    validation: dict[str, Any] | None = None
    if validation_path is not None:
        validation, errors = _load_json_evidence(validation_path, f"{base_key}:validation-config")
        diagnostics.extend(errors)
        if validation is not None:
            validation_diagnostics, _ = validate_benchmark_validation_config(validation)
            diagnostics.extend(Diagnostic(f"{base_key}:validation:{item.path}", item.code, item.message) for item in validation_diagnostics)

    result_ref = artifact["evidence"]["validation_report"]
    result_path = _resolve(result_ref["path"], artifact_path.parent)
    result, result_errors = _load_json_evidence(result_path, f"{base_key}:$.evidence.validation_report")
    diagnostics.extend(result_errors)
    if result is None:
        return diagnostics
    if result.get("run_result_version") != "1.1.0":
        diagnostics.append(Diagnostic(f"{base_key}:$.evidence.validation_report", "artifact.contract", "measured validation report must use benchmark-run-result-v1.1"))
        return diagnostics
    result_diagnostics, result_blocking = validate_benchmark_run_result(result)
    diagnostics.extend(Diagnostic(f"{base_key}:result:{item.path}", item.code, item.message) for item in result_diagnostics)
    diagnostics.extend(
        Diagnostic(f"{base_key}:result:{item.get('path', 'status')}", "artifact.blocking", item.get("reason", "run result blocked"))
        for item in result_blocking
    )
    expected_linkage = {
        "variant": artifact["variant"],
        "model": benchmark["environment"]["model"],
        "reasoning": benchmark["environment"]["reasoning"],
        "code_baseline_commit": benchmark["environment"]["code_baseline"],
    }
    reference_item = next((item for item in input_data.get("inputs", []) if item.get("kind") == "reference"), None)
    if reference_item is not None:
        expected_linkage["reference_sha256"] = reference_item["sha256"]
    for key, value in expected_linkage.items():
        if result.get(key) != value:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.{key}", "artifact.linkage", f"run result does not match benchmark: {key}"))
    checkout = artifact_path.parent / "checkout"
    if not checkout.is_dir():
        diagnostics.append(Diagnostic(f"{base_key}:checkout", "artifact.missing", "measured run checkout is missing"))
    else:
        diagnostics.extend(
            _verify_pinned_tree_slice(
                checkout,
                benchmark_environment["code_baseline"],
                f"{base_key}:checkout",
            )
        )
        returncode, head, _ = _git_bytes(checkout, ["rev-parse", "HEAD"])
        if returncode != 0 or head.decode().strip() != benchmark_environment["code_baseline"]:
            diagnostics.append(Diagnostic(f"{base_key}:checkout", "artifact.baseline", "checkout HEAD does not match benchmark code baseline"))
        returncode, commit_object, _ = _git_bytes(checkout, ["cat-file", "commit", benchmark_environment["code_baseline"]])
        if returncode != 0 or hashlib.sha256(commit_object).hexdigest() != benchmark_environment["code_baseline_hash"]:
            diagnostics.append(Diagnostic(f"{base_key}:checkout", "artifact.baseline", "checkout commit object hash does not match benchmark"))
        expected_patch, patch_error = _capture_checkout_patch(checkout, benchmark_environment["code_baseline"])
        implementation_ref = artifact["evidence"]["implementation_output"]
        implementation_path = _resolve(implementation_ref["path"], artifact_path.parent)
        if patch_error is not None:
            diagnostics.append(Diagnostic(f"{base_key}:checkout", "artifact.patch", patch_error))
        elif implementation_path.is_file() and implementation_path.read_bytes() != expected_patch:
            diagnostics.append(Diagnostic(f"{base_key}:$.evidence.implementation_output", "artifact.patch", "implementation patch does not match the final pinned checkout"))
    expected_metrics = {key: artifact["metrics"][key] for key in METRIC_KEYS if key != "input_tokens"}
    if result.get("metrics") != expected_metrics:
        diagnostics.append(Diagnostic(f"{base_key}:result:$.metrics", "artifact.metrics", "run result metrics do not match run artifact"))
    if result.get("status") != artifact.get("validation_status"):
        diagnostics.append(Diagnostic(f"{base_key}:result:$.status", "artifact.validation-status", "run result status does not match run artifact validation_status"))
    if (result.get("model_usage") or {}).get("input_tokens") != artifact["metrics"]["input_tokens"]:
        diagnostics.append(Diagnostic(f"{base_key}:result:$.model_usage.input_tokens", "artifact.metrics", "model usage does not match input_tokens metric"))
    if validation is not None:
        region_ids = [item.get("id") for item in result.get("regions", [])]
        if region_ids != validation.get("required_regions"):
            diagnostics.append(Diagnostic(f"{base_key}:result:$.regions", "artifact.coverage", "run result does not cover validation-config required_regions"))
    payloads: dict[str, dict[str, Any]] = {}
    payload_validators = {
        "validator_probe": validate_benchmark_validator_probe,
        "semantic_snapshot": validate_benchmark_semantic_evidence,
        "visual_diff": validate_benchmark_visual_diff,
        "run_observation": validate_benchmark_run_observation,
    }
    for label, evidence in (result.get("evidence") or {}).items():
        nested_path = _resolve(evidence["path"], result_path.parent)
        key = f"{base_key}:result:$.evidence.{label}"
        if label == "run_observation" and evidence["path"] != "run-observation.json":
            diagnostics.append(Diagnostic(key, "artifact.ownership", "run observation must use the fixed executor-owned path"))
        if label != "run_observation" and (Path(evidence["path"]).is_absolute() or len(Path(evidence["path"]).parts) != 1):
            diagnostics.append(Diagnostic(key, "artifact.ownership", "validator-owned evidence must be a direct child of the run directory"))
        if not _inside(artifact_path.parent, nested_path):
            diagnostics.append(Diagnostic(key, "artifact.path", "validation evidence must stay inside the run artifact directory"))
            continue
        diagnostics.extend(_verify_file_hash(nested_path, evidence["sha256"], key))
        if label in payload_validators and nested_path.is_file():
            payload, errors = _load_json_evidence(nested_path, key)
            diagnostics.extend(errors)
            if payload is not None:
                payload_diagnostics, _ = payload_validators[label](payload)
                diagnostics.extend(Diagnostic(f"{key}:{item.path}", item.code, item.message) for item in payload_diagnostics)
                if not payload_diagnostics:
                    payloads[label] = payload
    screenshot_ref = (result.get("evidence") or {}).get("actual_screenshot")
    if isinstance(screenshot_ref, dict):
        screenshot_path = _resolve(screenshot_ref["path"], result_path.parent)
        if screenshot_path.is_file() and _inside(artifact_path.parent, screenshot_path):
            match = re.fullmatch(r"([0-9]+)x([0-9]+)@.+", benchmark["environment"]["viewport"])
            png_size, png_error = _png_size(screenshot_path)
            if png_error is not None:
                diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.actual_screenshot", "artifact.png", png_error))
            elif match and png_size != (int(match.group(1)), int(match.group(2))):
                diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.actual_screenshot", "artifact.viewport", "measured screenshot viewport does not match benchmark"))

    probe = payloads.get("validator_probe")
    semantic = payloads.get("semantic_snapshot")
    visual = payloads.get("visual_diff")
    observation = payloads.get("run_observation")
    expected_common = {
        "case_id": benchmark["case_id"],
        "variant": artifact["variant"],
    }
    for label, payload in payloads.items():
        for key, value in expected_common.items():
            if payload.get(key) != value:
                diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.{label}:$.{key}", "artifact.linkage", f"{label} does not match benchmark: {key}"))
    for label, payload in (("semantic_snapshot", semantic), ("visual_diff", visual)):
        if payload is not None:
            if payload.get("validator_id") != benchmark_environment["validator_id"]:
                diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.{label}:$.validator_id", "artifact.linkage", "validator id does not match benchmark"))
            if payload.get("validator_adapter_sha256") != benchmark_environment["validator_adapter_hash"]:
                diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.{label}:$.validator_adapter_sha256", "artifact.linkage", "validator adapter hash does not match benchmark"))
            probe_ref = (result.get("evidence") or {}).get("validator_probe") or {}
            if payload.get("validator_probe_sha256") != probe_ref.get("sha256"):
                diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.{label}:$.validator_probe_sha256", "artifact.linkage", "derived validation evidence must link the archived validator probe"))
            if probe is not None and payload.get("capture_adapter_sha256") != probe.get("capture_adapter_sha256"):
                diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.{label}:$.capture_adapter_sha256", "artifact.linkage", "derived validation evidence must preserve validator probe capture identity"))
    if probe is not None:
        if probe.get("validator_id") != benchmark_environment["validator_id"]:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.validator_probe:$.validator_id", "artifact.linkage", "validator probe id does not match benchmark"))
        if probe.get("capture_adapter_sha256") != benchmark_environment["capture_adapter_hash"]:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.validator_probe:$.capture_adapter_sha256", "artifact.linkage", "validator probe capture adapter hash does not match benchmark"))
        screenshot_evidence = (result.get("evidence") or {}).get("actual_screenshot") or {}
        if probe.get("actual_screenshot") != screenshot_evidence:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.validator_probe:$.actual_screenshot", "artifact.linkage", "validator probe screenshot must match run-result screenshot evidence"))
        input_environment = input_data.get("environment", {})
        expected_probe_environment = {
            "viewport": input_environment.get("viewport"),
            "scale": input_environment.get("scale"),
            "appearance": input_environment.get("appearance"),
            "locale": input_environment.get("locale"),
        }
        if probe.get("environment") != expected_probe_environment:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.validator_probe:$.environment", "artifact.environment", "validator probe environment must match the frozen input context"))
        probe_regions = [item.get("id") for item in probe.get("regions", [])]
        expected_regions = validation.get("required_regions", []) if validation is not None else []
        if probe_regions != expected_regions:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.validator_probe:$.regions", "artifact.coverage", "validator probe must exactly cover required_regions in order"))
        required_runtime_bindings = {
            item["id"]: {
                "id": item["id"],
                "region_id": item["region_id"],
                "runtime_type": item["runtime_type"],
            }
            for item in (validation.get("required_bindings", []) if validation is not None else [])
        }
        for index, binding in enumerate(probe.get("bindings", [])):
            if required_runtime_bindings.get(binding.get("id")) != binding:
                diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.validator_probe:$.bindings[{index}]", "artifact.linkage", "validator probe runtime binding must exactly match a frozen required binding"))
    if observation is not None:
        if observation.get("executor_adapter_sha256") != benchmark_environment["executor_adapter_hash"]:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.run_observation:$.executor_adapter_sha256", "artifact.linkage", "executor adapter hash does not match benchmark"))
        for key in ("model", "reasoning"):
            if observation.get(key) != benchmark_environment[key]:
                diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.run_observation:$.{key}", "artifact.linkage", f"run observation does not match benchmark: {key}"))
        provider_cli = observation.get("provider_cli") if isinstance(observation.get("provider_cli"), dict) else {}
        expected_provider_cli = {
            "name": benchmark_environment.get("provider_cli_name"),
            "version": benchmark_environment.get("provider_cli_version"),
            "launcher_path": benchmark_environment.get("provider_cli_launcher_path"),
            "native_path": benchmark_environment.get("provider_cli_native_path"),
            "launcher_sha256": benchmark_environment.get("provider_cli_launcher_hash"),
            "native_sha256": benchmark_environment.get("provider_cli_native_hash"),
            "package_json_sha256": benchmark_environment.get("provider_cli_package_json_hash"),
        }
        if provider_cli != expected_provider_cli:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.run_observation:$.provider_cli", "artifact.linkage", "provider CLI identity does not match benchmark"))
        stdout_ref = artifact["evidence"]["implementation_stdout"]
        if observation.get("provider_event_stream_sha256") != stdout_ref.get("sha256"):
            diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.run_observation:$.provider_event_stream_sha256", "artifact.linkage", "provider event stream hash must match implementation stdout evidence"))
        stdout_path = _resolve(stdout_ref["path"], artifact_path.parent)
        if stdout_path.is_file() and _inside(artifact_path.parent, stdout_path):
            stdout_bytes = stdout_path.read_bytes()
            thread_id, usage, replay_error = _replay_provider_stream(stdout_bytes)
            if replay_error is not None:
                diagnostics.append(Diagnostic(f"{base_key}:$.evidence.implementation_stdout", "artifact.provider", replay_error))
            elif observation.get("provider_runs") != [{"id": thread_id, **(usage or {})}]:
                diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.run_observation:$.provider_runs", "artifact.derived", "provider runs must be replayed from canonical implementation stdout"))

    if probe is not None and semantic is not None and visual is not None and observation is not None and isinstance(screenshot_ref, dict):
        required_regions = validation.get("required_regions", []) if validation is not None else []
        semantic_regions = {item["id"]: item for item in semantic["regions"]}
        visual_regions = {item["id"]: item for item in visual["regions"]}
        if list(semantic_regions) != required_regions or list(visual_regions) != required_regions:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.regions", "artifact.coverage", "structured semantic and visual evidence must exactly cover required_regions in order"))
        probe_regions_by_id = {item["id"]: item for item in probe["regions"]}
        expected_regions_by_id = {
            item["id"]: item
            for item in (validation.get("reference_regions", []) if validation is not None else [])
        }
        for region_id in required_regions:
            if region_id in semantic_regions and region_id in probe_regions_by_id and region_id in expected_regions_by_id:
                derived_region = _derive_region_evidence(expected_regions_by_id[region_id], probe_regions_by_id[region_id])
                if semantic_regions[region_id] != derived_region:
                    diagnostics.append(Diagnostic(f"{base_key}:result:semantic:$.regions[{region_id}]", "artifact.derived", "semantic region evidence must be derived from frozen expectations and raw validator probe observations"))
        expected_anchors = {
            item["region_id"]: [anchor["id"] for anchor in item["anchors"]]
            for item in (validation.get("required_anchors", []) if validation is not None else [])
        }
        for region_id, region in visual_regions.items():
            actual_anchor_ids = [anchor["id"] for anchor in region["anchors"]]
            if actual_anchor_ids != expected_anchors.get(region_id):
                diagnostics.append(Diagnostic(f"{base_key}:result:visual:$.regions[{region_id}].anchors", "artifact.coverage", "visual evidence must exactly cover validation-config anchors in order"))
        reference_frames = {
            item["id"]: item["frame"]
            for item in (validation.get("reference_regions", []) if validation is not None else [])
        }
        actual_frames = {item["id"]: item["frame"] for item in probe["regions"]}
        decoded_reference = decoded_actual = None
        reference_path = nested_inputs.get("reference")
        actual_path = _resolve(screenshot_ref["path"], result_path.parent)
        if reference_path is not None and reference_path.is_file() and actual_path.is_file():
            try:
                decoded_reference = _score_decode_png(reference_path)
                decoded_actual = _score_decode_png(actual_path)
            except (OSError, ValueError, struct.error, zlib.error) as exc:
                diagnostics.append(Diagnostic(f"{base_key}:result:visual:$.regions", "artifact.pixel", f"unable to replay pixel evidence: {exc}"))
        for anchor_region in (validation.get("required_anchors", []) if validation is not None else []):
            region_id = anchor_region["region_id"]
            if region_id not in visual_regions or region_id not in reference_frames or region_id not in actual_frames:
                continue
            try:
                derived_anchors = [
                    _derive_anchor(anchor, region_id, reference_frames, actual_frames)
                    for anchor in anchor_region["anchors"]
                ]
            except (KeyError, TypeError, ValueError) as exc:
                diagnostics.append(Diagnostic(f"{base_key}:result:visual:$.regions[{region_id}].anchors", "artifact.derived", f"unable to derive anchor values from frozen frames: {exc}"))
                continue
            if visual_regions[region_id]["anchors"] != derived_anchors:
                diagnostics.append(Diagnostic(f"{base_key}:result:visual:$.regions[{region_id}].anchors", "artifact.derived", "visual anchors must be derived from validation reference frames and validator probe frames"))
            derived_deviation = max((item["deviation_pt"] for item in derived_anchors), default=0)
            if not math.isclose(float(visual_regions[region_id]["layout_deviation_pt"]), derived_deviation, abs_tol=1e-9):
                diagnostics.append(Diagnostic(f"{base_key}:result:visual:$.regions[{region_id}].layout_deviation_pt", "artifact.derived", "region deviation must equal the maximum derived anchor deviation"))
            if decoded_reference is not None and decoded_actual is not None:
                try:
                    derived_ratio = _score_pixel_difference_ratio(
                        decoded_reference,
                        decoded_actual,
                        reference_frames[region_id],
                        [item["frame"] for item in validation.get("ignore_regions", [])],
                        validation["pixel_diff"]["max_channel_delta"],
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    diagnostics.append(Diagnostic(f"{base_key}:result:visual:$.regions[{region_id}].pixel_difference_ratio", "artifact.pixel", f"unable to derive pixel difference: {exc}"))
                else:
                    if not math.isclose(float(visual_regions[region_id]["pixel_difference_ratio"]), derived_ratio, abs_tol=1e-12):
                        diagnostics.append(Diagnostic(f"{base_key}:result:visual:$.regions[{region_id}].pixel_difference_ratio", "artifact.derived", "pixel difference ratio must be replayed from frozen reference and actual PNG evidence"))
                    expected_visual = "passed" if derived_ratio <= validation["pixel_diff"]["max_different_pixel_ratio"] else "failed"
                    if visual_regions[region_id]["visual"] != expected_visual:
                        diagnostics.append(Diagnostic(f"{base_key}:result:visual:$.regions[{region_id}].visual", "artifact.derived", "visual status must be derived from the frozen pixel threshold"))
        derived_regions = [
            {
                "id": region_id,
                "structure": semantic_regions[region_id]["structure"],
                "semantic": semantic_regions[region_id]["semantic"],
                "visual": visual_regions[region_id]["visual"],
                "layout_deviation_pt": visual_regions[region_id]["layout_deviation_pt"],
            }
            for region_id in required_regions
            if region_id in semantic_regions and region_id in visual_regions
        ]
        if result.get("regions") != derived_regions:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.regions", "artifact.metrics", "run result regions must be derived from semantic and visual evidence"))
        bindings = semantic["required_bindings"]
        expected_bindings = validation.get("required_bindings", []) if validation is not None else []
        actual_binding_contract = [
            {
                "id": item["id"],
                "registry_entry_id": item["registry_entry_id"],
                "code_symbol": item["code_symbol"],
                "source": item["source"],
                "region_id": item["region_id"],
                "runtime_type": item["runtime_type"],
            }
            for item in bindings
        ]
        if actual_binding_contract != expected_bindings:
            diagnostics.append(Diagnostic(f"{base_key}:result:semantic:$.required_bindings", "artifact.coverage", "semantic evidence must exactly cover validation-config required_bindings in order"))
        observed_runtime_ids = {item["id"] for item in probe.get("bindings", [])}
        for binding_index, binding in enumerate(bindings):
            expected_runtime_observed = binding["id"] in observed_runtime_ids
            if binding.get("runtime_observed") is not expected_runtime_observed or binding.get("reused") is not expected_runtime_observed:
                diagnostics.append(Diagnostic(f"{base_key}:result:semantic:$.required_bindings[{binding_index}]", "artifact.derived", "runtime_observed and reused must be derived from the validator probe binding observation"))
        reuse_rate = sum(1 for item in bindings if item["reused"]) / len(bindings)
        layout_deviation = max((item["layout_deviation_pt"] for item in visual["regions"]), default=0)
        provider_runs = observation["provider_runs"]
        input_tokens = sum(item["input_tokens"] for item in provider_runs)
        output_tokens = sum(item["output_tokens"] for item in provider_runs)
        manual_minutes = sum(item["duration_seconds"] for item in observation["manual_interventions"]) / 60
        try:
            replayed_literals = _score_added_swift_literals(checkout, benchmark_environment["code_baseline"])
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            diagnostics.append(Diagnostic(f"{base_key}:result:semantic:$.unmapped_literals", "artifact.derived", f"unable to replay unmapped visual literals: {exc}"))
            replayed_literals = []
        if semantic["unmapped_literals"] != replayed_literals:
            diagnostics.append(Diagnostic(f"{base_key}:result:semantic:$.unmapped_literals", "artifact.derived", "unmapped visual literals must be independently replayed from changed Swift source"))
        derived_metrics = {
            "layout_deviation_pt": layout_deviation,
            "component_reuse_rate": reuse_rate,
            "magic_numbers": len(replayed_literals),
            "repair_iterations": len(observation["repair_events"]),
            "manual_minutes": manual_minutes,
        }
        for key, value in derived_metrics.items():
            actual = (result.get("metrics") or {}).get(key)
            if not isinstance(actual, (int, float)) or isinstance(actual, bool) or not math.isclose(float(actual), float(value), abs_tol=1e-9):
                diagnostics.append(Diagnostic(f"{base_key}:result:$.metrics.{key}", "artifact.derived", f"metric must be derived from structured evidence: expected {value}"))
        expected_usage = {"input_tokens": input_tokens, "output_tokens": output_tokens}
        if result.get("model_usage") != expected_usage:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.model_usage", "artifact.derived", "model usage must equal the sum of provider_runs"))
        thresholds = validation["thresholds"]
        expected_pass = all(
            item.get(status) == "passed"
            for item in result.get("regions", [])
            for status in ("structure", "semantic", "visual")
        ) and all(
            (
                derived_metrics["layout_deviation_pt"] <= thresholds["max_layout_deviation_pt"],
                derived_metrics["component_reuse_rate"] >= thresholds["min_component_reuse_rate"],
                derived_metrics["magic_numbers"] <= thresholds["max_magic_numbers"],
                derived_metrics["repair_iterations"] <= thresholds["max_repair_iterations"],
                input_tokens <= thresholds["max_input_tokens"],
                derived_metrics["manual_minutes"] <= thresholds["max_manual_minutes"],
            )
        )
        if result.get("status") != ("passed" if expected_pass else "failed"):
            diagnostics.append(Diagnostic(f"{base_key}:result:$.status", "artifact.derived", "run status must be derived from region outcomes and frozen absolute thresholds"))
        primary_provider_id = provider_runs[0]["id"]
        cross_run.setdefault("provider_run_id", []).extend(item["id"] for item in provider_runs)
        if result.get("provider_run_id") != primary_provider_id:
            diagnostics.append(Diagnostic(f"{base_key}:result:$.provider_run_id", "artifact.derived", "provider_run_id must equal the first observed provider run"))
        if visual.get("reference_sha256") != result.get("reference_sha256"):
            diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.visual_diff:$.reference_sha256", "artifact.linkage", "visual diff reference hash does not match run result"))
        if visual.get("actual_sha256") != screenshot_ref.get("sha256"):
            diagnostics.append(Diagnostic(f"{base_key}:result:$.evidence.visual_diff:$.actual_sha256", "artifact.linkage", "visual diff actual hash does not match screenshot evidence"))
        for binding_index, binding in enumerate(bindings):
            if binding["reused"]:
                for location_index, location in enumerate(binding["locations"]):
                    diagnostics.extend(_verify_symbol_declaration_location(checkout, location, binding["code_symbol"], f"{base_key}:result:semantic:$.required_bindings[{binding_index}].locations[{location_index}]"))
        for literal_index, literal in enumerate(semantic["unmapped_literals"]):
            diagnostics.extend(_verify_source_location(checkout, literal["location"], str(literal["value"]), f"{base_key}:result:semantic:$.unmapped_literals[{literal_index}].location"))
    return diagnostics


def _verify_measured_artifacts(data: dict[str, Any], base_dir: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    cross_run: dict[str, list[str]] = {}
    for index, candidate in enumerate(data["candidates"]):
        run = candidate["run"]
        artifact_path = _resolve(run["artifact_path"], base_dir)
        artifact_path_key = f"$.candidates[{index}].run.artifact_path"
        if not _inside(base_dir, artifact_path):
            diagnostics.append(Diagnostic(artifact_path_key, "artifact.path", "run artifact must stay inside the benchmark directory"))
            continue
        artifact_file_diagnostics = _verify_file_hash(artifact_path, run["artifact_sha256"], artifact_path_key)
        diagnostics.extend(artifact_file_diagnostics)
        if artifact_file_diagnostics:
            continue
        try:
            artifact = load_json(artifact_path)
        except ValueError as exc:
            diagnostics.append(Diagnostic(artifact_path_key, "artifact.json", str(exc)))
            continue
        artifact_diagnostics, _ = validate_benchmark_artifact(artifact)
        diagnostics.extend(
            Diagnostic(f"{artifact_path_key}:{item.path}", item.code, item.message)
            for item in artifact_diagnostics
        )
        if artifact_diagnostics or not isinstance(artifact, dict):
            continue
        if artifact["run_id"] != run["id"]:
            diagnostics.append(Diagnostic(artifact_path_key, "artifact.run", "run_id does not match benchmark manifest"))
        if artifact["variant"] != candidate["variant"]:
            diagnostics.append(Diagnostic(artifact_path_key, "artifact.variant", "variant does not match benchmark candidate"))
        if artifact.get("validation_status") != candidate.get("validation_status"):
            diagnostics.append(Diagnostic(artifact_path_key, "artifact.validation-status", "validation_status does not match benchmark candidate"))
        for key in ENVIRONMENT_KEYS:
            if artifact["environment"].get(key) != data["environment"].get(key):
                diagnostics.append(Diagnostic(artifact_path_key, "artifact.environment", f"environment field does not match: {key}"))
        for key in METRIC_KEYS:
            if artifact["metrics"].get(key) != candidate.get(key):
                diagnostics.append(Diagnostic(artifact_path_key, "artifact.metrics", f"metric does not match: {key}"))
        for evidence_key in EVIDENCE_KEYS:
            evidence = artifact["evidence"][evidence_key]
            evidence_path = _resolve(evidence["path"], artifact_path.parent)
            if not _inside(artifact_path.parent, evidence_path):
                diagnostics.append(
                    Diagnostic(
                        f"{artifact_path_key}:$.evidence.{evidence_key}",
                        "artifact.path",
                        "run evidence must stay inside the run artifact directory",
                    )
                )
                continue
            diagnostics.extend(
                _verify_file_hash(
                    evidence_path,
                    evidence["sha256"],
                    f"{artifact_path_key}:$.evidence.{evidence_key}",
                )
            )
        diagnostics.extend(_verify_nested_evidence(artifact, artifact_path, data, index, cross_run))
    for key in ("plan_sha256", "benchmark_case_sha256", "executor_adapter_sha256", "capture_adapter_sha256", "capture_overlay_identity", "provider_source_scope_identity", "evaluator_dependency_identity", "validator_adapter_sha256"):
        values = cross_run.get(key, [])
        if len(values) != len(data["candidates"]) or len(set(values)) != 1:
            diagnostics.append(Diagnostic("$.candidates", "artifact.cross-run", f"all candidates must share exactly one {key}"))
    provider_ids = cross_run.get("provider_run_id", [])
    if len(provider_ids) < len(data["candidates"]) or len(set(provider_ids)) != len(provider_ids):
        diagnostics.append(Diagnostic("$.candidates", "artifact.provider", "all structured provider run IDs must be globally unique across candidates"))
    return diagnostics


def score(data: dict[str, Any], allow_synthetic: bool = False, base_dir: Path | None = None) -> dict[str, Any]:
    diagnostics, _ = validate_benchmark(data)
    if diagnostics:
        return {
            "status": "invalid",
            "diagnostics": [item.as_dict() for item in diagnostics],
        }
    if data.get("evidence_status") != "measured" and not allow_synthetic:
        return {
            "status": "blocked",
            "reason": "synthetic-example cannot be used as real benchmark evidence",
        }
    if data.get("evidence_status") == "measured":
        artifact_diagnostics = _verify_measured_artifacts(data, base_dir or Path.cwd())
        if artifact_diagnostics:
            return {
                "status": "blocked",
                "reason": "measured benchmark artifacts are missing or do not match their hashes",
                "diagnostics": [item.as_dict() for item in artifact_diagnostics],
            }

    candidates = {item["variant"]: item for item in data["candidates"]}
    baseline = candidates["screenshot-only"]
    ui_ir = candidates["ui-ir"]
    target = candidates["ui-ir-with-binding"]
    thresholds = data["thresholds"]

    gates = {
        "ui_ir_layout_gain": baseline["layout_deviation_pt"] - ui_ir["layout_deviation_pt"] >= thresholds["min_ui_ir_layout_improvement_pt"],
        "ui_ir_repair_gain": ui_ir["repair_iterations"] < baseline["repair_iterations"],
        "ui_ir_magic_number_gain": ui_ir["magic_numbers"] < baseline["magic_numbers"],
        "binding_reuse_gain": target["component_reuse_rate"] - ui_ir["component_reuse_rate"] >= thresholds["min_binding_reuse_gain"],
        "binding_context_compaction": target["input_tokens"] <= ui_ir["input_tokens"],
        "final_layout": target["layout_deviation_pt"] <= thresholds["max_layout_deviation_pt"],
        "final_component_reuse": target["component_reuse_rate"] >= thresholds["min_component_reuse_rate"],
        "final_repair_iterations": target["repair_iterations"] <= thresholds["max_repair_iterations"],
        "final_input_tokens": target["input_tokens"] <= thresholds["max_input_tokens"],
        "final_magic_numbers": target["magic_numbers"] <= thresholds["max_magic_numbers"],
        "final_manual_minutes": target["manual_minutes"] <= thresholds["max_manual_minutes"],
        "final_semantic_visual_validation": target["validation_status"] == "passed",
    }
    deltas = {
        "layout_deviation_pt": target["layout_deviation_pt"] - baseline["layout_deviation_pt"],
        "component_reuse_rate": target["component_reuse_rate"] - baseline["component_reuse_rate"],
        "magic_numbers": target["magic_numbers"] - baseline["magic_numbers"],
        "repair_iterations": target["repair_iterations"] - baseline["repair_iterations"],
        "input_tokens": target["input_tokens"] - baseline["input_tokens"],
        "manual_minutes": target["manual_minutes"] - baseline["manual_minutes"],
    }
    return {
        "status": "scored",
        "evidence_status": data["evidence_status"],
        "case_id": data["case_id"],
        "gates": gates,
        "deltas_vs_screenshot_only": deltas,
        "recommendation": "go" if all(gates.values()) else "revise",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--allow-synthetic", action="store_true", help="self-test only; synthetic data is not real evidence")
    args = parser.parse_args()
    try:
        data = load_json(args.path)
    except ValueError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    result = score(data, allow_synthetic=args.allow_synthetic, base_dir=args.path.parent)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result.get("status") != "scored":
        return 1
    return 0 if result.get("recommendation") == "go" else 3


if __name__ == "__main__":
    sys.exit(main())
