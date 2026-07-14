#!/usr/bin/env python3
"""Derive measured semantic and visual evidence from a frozen iOS capture probe."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
from typing import Any
import zlib


class ValidationError(ValueError):
    """Frozen capture evidence cannot be validated deterministically."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON evidence: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON evidence must be an object: {path}")
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def frame_edge(frame: dict[str, Any], edge: str) -> float:
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
    raise ValidationError(f"unsupported frame edge: {edge}")


def derive_anchor(
    anchor: dict[str, Any],
    region_id: str,
    reference_frames: dict[str, dict[str, Any]],
    actual_frames: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    metric = anchor["metric"]
    if metric == "position":
        reference = [float(reference_frames[region_id]["x"]), float(reference_frames[region_id]["y"])]
        actual = [float(actual_frames[region_id]["x"]), float(actual_frames[region_id]["y"])]
    elif metric == "size":
        reference = [float(reference_frames[region_id]["width"]), float(reference_frames[region_id]["height"])]
        actual = [float(actual_frames[region_id]["width"]), float(actual_frames[region_id]["height"])]
    elif metric == "spacing":
        reference = [float(anchor["reference_value"])]
        relative = anchor["relative_to_region_id"]
        actual = [
            frame_edge(actual_frames[region_id], anchor["region_edge"])
            - frame_edge(actual_frames[relative], anchor["relative_edge"])
        ]
    else:
        raise ValidationError(f"unsupported anchor metric: {metric}")
    deviation = max(abs(actual_value - reference_value) for actual_value, reference_value in zip(actual, reference))
    return {
        "id": anchor["id"],
        "metric": metric,
        "reference_value": reference,
        "actual_value": actual,
        "deviation_pt": deviation,
    }


def derive_region_evidence(expected: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    structure_passed = (
        observed.get("visible") is True
        and observed.get("parent_id") == expected.get("parent_id")
        and observed.get("child_ids") == expected.get("child_ids")
    )
    semantic_passed = (
        observed.get("runtime_type") == expected.get("runtime_type")
        and observed.get("accessibility_identifier") == expected.get("accessibility_identifier")
    )
    return {
        "id": expected["id"],
        "frame": observed["frame"],
        "structure": "passed" if structure_passed else "failed",
        "semantic": "passed" if semantic_passed else "failed",
    }


def _paeth(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
    return (left, above, upper_left)[distances.index(min(distances))]


def decode_png(path: Path) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValidationError(f"not a PNG: {path}")
    offset = 8
    width = height = color_type = bit_depth = interlace = None
    compressed = bytearray()
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValidationError(f"truncated PNG chunk: {path}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            raise ValidationError(f"truncated PNG chunk payload: {path}")
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        crc = struct.unpack(">I", data[offset + 8 + length : offset + 12 + length])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise ValidationError(f"invalid PNG CRC: {path}")
        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if bit_depth != 8 or color_type not in {0, 2, 4, 6} or compression != 0 or filtering != 0 or interlace != 0:
                raise ValidationError("validator supports non-interlaced 8-bit grayscale/RGB/RGBA PNG only")
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
        offset += 12 + length
    if width is None or height is None or color_type is None:
        raise ValidationError(f"PNG is missing IHDR: {path}")
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    row_bytes = width * channels
    raw = zlib.decompress(bytes(compressed))
    if len(raw) != height * (row_bytes + 1):
        raise ValidationError(f"unexpected PNG payload size: {path}")
    prior = bytearray(row_bytes)
    pixels: list[tuple[int, int, int, int]] = []
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        encoded = raw[cursor : cursor + row_bytes]
        cursor += row_bytes
        row = bytearray(row_bytes)
        for index, value in enumerate(encoded):
            left = row[index - channels] if index >= channels else 0
            above = prior[index]
            upper_left = prior[index - channels] if index >= channels else 0
            if filter_type == 0:
                reconstructed = value
            elif filter_type == 1:
                reconstructed = value + left
            elif filter_type == 2:
                reconstructed = value + above
            elif filter_type == 3:
                reconstructed = value + ((left + above) // 2)
            elif filter_type == 4:
                reconstructed = value + _paeth(left, above, upper_left)
            else:
                raise ValidationError(f"unsupported PNG row filter: {filter_type}")
            row[index] = reconstructed & 0xFF
        for index in range(0, row_bytes, channels):
            if color_type == 0:
                pixels.append((row[index], row[index], row[index], 255))
            elif color_type == 4:
                pixels.append((row[index], row[index], row[index], row[index + 1]))
            elif color_type == 2:
                pixels.append((row[index], row[index + 1], row[index + 2], 255))
            else:
                pixels.append((row[index], row[index + 1], row[index + 2], row[index + 3]))
        prior = row
    return width, height, pixels


def pixel_difference_ratio(
    reference: tuple[int, int, list[tuple[int, int, int, int]]],
    actual: tuple[int, int, list[tuple[int, int, int, int]]],
    frame: dict[str, Any],
    ignore_frames: list[dict[str, Any]],
    max_channel_delta: int,
) -> float:
    width, height, reference_pixels = reference
    actual_width, actual_height, actual_pixels = actual
    if (width, height) != (actual_width, actual_height):
        raise ValidationError("reference and actual PNG dimensions differ")
    min_x = max(0, math.floor(float(frame["x"])))
    min_y = max(0, math.floor(float(frame["y"])))
    max_x = min(width, math.ceil(float(frame["x"]) + float(frame["width"])))
    max_y = min(height, math.ceil(float(frame["y"]) + float(frame["height"])))
    compared = different = 0
    for y in range(min_y, max_y):
        for x in range(min_x, max_x):
            if any(
                float(ignored["x"]) <= x < float(ignored["x"]) + float(ignored["width"])
                and float(ignored["y"]) <= y < float(ignored["y"]) + float(ignored["height"])
                for ignored in ignore_frames
            ):
                continue
            index = y * width + x
            compared += 1
            if max(abs(reference_pixels[index][channel] - actual_pixels[index][channel]) for channel in range(4)) > max_channel_delta:
                different += 1
    return different / compared if compared else 0.0


def swift_code_lines(text: str) -> list[str]:
    """Remove Swift comments and string literal contents while preserving line numbers."""
    output: list[str] = []
    block_depth = 0
    string_end: str | None = None
    for raw_line in text.splitlines():
        line = []
        index = 0
        while index < len(raw_line):
            if block_depth:
                if raw_line.startswith("/*", index):
                    block_depth += 1
                    index += 2
                elif raw_line.startswith("*/", index):
                    block_depth -= 1
                    index += 2
                else:
                    index += 1
                continue
            if string_end is not None:
                if raw_line.startswith(string_end, index):
                    index += len(string_end)
                    string_end = None
                elif string_end == '"' and raw_line[index] == "\\":
                    index += 2
                else:
                    index += 1
                continue
            if raw_line.startswith("//", index):
                break
            if raw_line.startswith("/*", index):
                block_depth = 1
                index += 2
                continue
            hash_count = 0
            while index + hash_count < len(raw_line) and raw_line[index + hash_count] == "#":
                hash_count += 1
            quote_index = index + hash_count
            if quote_index < len(raw_line) and raw_line[quote_index] == '"':
                triple = raw_line.startswith('"""', quote_index)
                string_end = ('"""' if triple else '"') + ("#" * hash_count)
                index = quote_index + (3 if triple else 1)
                continue
            line.append(raw_line[index])
            index += 1
        output.append("".join(line))
    return output


def declaration_location(worktree: Path, binding: dict[str, Any]) -> dict[str, Any]:
    source = worktree / binding["source"]
    if not source.is_file():
        raise ValidationError(f"binding owner source is missing: {binding['source']}")
    symbol = re.escape(binding["code_symbol"])
    pattern = re.compile(rf"\b(?:class|struct|enum|actor|protocol|typealias)\s+{symbol}\b")
    for line_number, line in enumerate(swift_code_lines(source.read_text(encoding="utf-8")), start=1):
        if pattern.search(line):
            return {"path": binding["source"], "line": line_number}
    raise ValidationError(f"binding owner declaration is missing: {binding['code_symbol']} in {binding['source']}")


def added_swift_literals(worktree: Path, baseline_commit: str) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["git", "diff", "--no-color", "--unified=0", baseline_commit, "--", "*.swift"],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValidationError(f"unable to inspect Swift implementation diff: {result.stderr.strip()}")
    path: str | None = None
    line_number: int | None = None
    changed_lines: dict[str, set[int]] = {}
    for line in result.stdout.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
            continue
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            line_number = int(match.group(1)) if match else None
            continue
        if line.startswith("+") and not line.startswith("+++") and path is not None and line_number is not None:
            changed_lines.setdefault(path, set()).add(line_number)
            line_number += 1
        elif line.startswith(" ") and line_number is not None:
            line_number += 1
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", "*.swift"],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )
    if untracked.returncode != 0:
        raise ValidationError(f"unable to inspect untracked Swift files: {untracked.stderr.strip()}")
    for relative in sorted(line for line in untracked.stdout.splitlines() if line):
        source = worktree / relative
        if not source.is_file():
            raise ValidationError(f"untracked Swift source is not a regular file: {relative}")
        changed_lines[relative] = set(range(1, len(source.read_text(encoding="utf-8").splitlines()) + 1))
    visual_context = re.compile(
        r"\b(?:CGRect|CGSize|CGPoint|UIEdgeInsets|frame|bounds|constraint|constant|spacing|padding|offset|cornerRadius|font|RGB|RGBA|UIColor|shadow|opacity|alpha|width|height|inset|margin|radius)\b",
        re.IGNORECASE,
    )
    semantic_name = re.compile(
        r"\b(?:let|var)\s+([A-Za-z_][A-Za-z0-9_]*)[^=]*=",
    )
    semantic_visual_name = re.compile(
        r"(?:spacing|padding|offset|corner|radius|font|color|shadow|opacity|alpha|width|height|inset|margin|size|dimension|layout)",
        re.IGNORECASE,
    )
    number = re.compile(r"(?<![A-Za-z0-9_])(-?(?:0x[0-9A-Fa-f]+|\d+\.\d+|\.\d+|\d+))(?![A-Za-z0-9_])")
    findings: list[dict[str, Any]] = []
    for relative in sorted(changed_lines):
        source = worktree / relative
        code_lines = swift_code_lines(source.read_text(encoding="utf-8"))
        for source_line_number in sorted(changed_lines[relative]):
            if source_line_number > len(code_lines):
                raise ValidationError(f"changed Swift line is outside final source: {relative}:{source_line_number}")
            code = code_lines[source_line_number - 1]
            if not visual_context.search(code):
                continue
            declaration = semantic_name.search(code)
            if declaration and semantic_visual_name.search(declaration.group(1)):
                continue
            for match in number.finditer(code):
                findings.append({"kind": "layout", "value": match.group(1), "location": {"path": relative, "line": source_line_number}})
    return findings


def main() -> int:
    try:
        run_dir = Path(os.environ["DCC_RUN_DIR"])
        worktree = Path(os.environ["DCC_WORKTREE"])
        input_context = load_json(Path(os.environ["DCC_INPUT_CONTEXT"]))
        probe_path = Path(os.environ["DCC_VALIDATOR_PROBE"])
        actual_path = Path(os.environ["DCC_ACTUAL_SCREENSHOT"])
        observation_path = Path(os.environ["DCC_RUN_OBSERVATION"])
        probe = load_json(probe_path)
        observation = load_json(observation_path)
        validation_ref = next(item for item in input_context["inputs"] if item["kind"] == "validation-config")
        reference_ref = next(item for item in input_context["inputs"] if item["kind"] == "reference")
        validation = load_json(run_dir / validation_ref["path"])
        reference_path = run_dir / reference_ref["path"]
        if sha256(reference_path) != reference_ref["sha256"] or sha256(actual_path) != probe["actual_screenshot"]["sha256"]:
            raise ValidationError("reference or capture screenshot hash mismatch")

        probe_hash = sha256(probe_path)
        observed_regions = {item["id"]: item for item in probe["regions"]}
        semantic_regions = [
            derive_region_evidence(expected, observed_regions[expected["id"]])
            for expected in validation["reference_regions"]
        ]
        observed_binding_ids = {item["id"] for item in probe["bindings"]}
        bindings = []
        for binding in validation["required_bindings"]:
            observed = binding["id"] in observed_binding_ids
            bindings.append(
                {
                    **binding,
                    "runtime_observed": observed,
                    "reused": observed,
                    "locations": [declaration_location(worktree, binding)] if observed else [],
                }
            )
        literals = added_swift_literals(worktree, os.environ["DCC_CODE_BASELINE_COMMIT"])
        semantic = {
            "semantic_evidence_version": "1.1.0",
            "case_id": input_context["case_id"],
            "variant": input_context["variant"],
            "validator_id": os.environ["DCC_VALIDATOR_ID"],
            "validator_adapter_sha256": os.environ["DCC_VALIDATOR_ADAPTER_SHA256"],
            "validator_probe_sha256": probe_hash,
            "capture_adapter_sha256": probe["capture_adapter_sha256"],
            "regions": semantic_regions,
            "required_bindings": bindings,
            "unmapped_literals": literals,
        }
        semantic_path = run_dir / "semantic-snapshot.json"
        write_json(semantic_path, semantic)

        reference_frames = {item["id"]: item["frame"] for item in validation["reference_regions"]}
        actual_frames = {item["id"]: item["frame"] for item in probe["regions"]}
        decoded_reference = decode_png(reference_path)
        decoded_actual = decode_png(actual_path)
        ignore_frames = [item["frame"] for item in validation["ignore_regions"]]
        visual_regions = []
        for anchor_region in validation["required_anchors"]:
            region_id = anchor_region["region_id"]
            anchors = [derive_anchor(item, region_id, reference_frames, actual_frames) for item in anchor_region["anchors"]]
            deviation = max((item["deviation_pt"] for item in anchors), default=0)
            ratio = pixel_difference_ratio(
                decoded_reference,
                decoded_actual,
                reference_frames[region_id],
                ignore_frames,
                validation["pixel_diff"]["max_channel_delta"],
            )
            visual_regions.append(
                {
                    "id": region_id,
                    "visual": "passed" if ratio <= validation["pixel_diff"]["max_different_pixel_ratio"] else "failed",
                    "layout_deviation_pt": deviation,
                    "pixel_difference_ratio": ratio,
                    "anchors": anchors,
                }
            )
        visual = {
            "visual_diff_version": "1.1.0",
            "case_id": input_context["case_id"],
            "variant": input_context["variant"],
            "validator_id": os.environ["DCC_VALIDATOR_ID"],
            "validator_adapter_sha256": os.environ["DCC_VALIDATOR_ADAPTER_SHA256"],
            "validator_probe_sha256": probe_hash,
            "capture_adapter_sha256": probe["capture_adapter_sha256"],
            "reference_sha256": reference_ref["sha256"],
            "actual_sha256": sha256(actual_path),
            "regions": visual_regions,
        }
        visual_path = run_dir / "visual-diff.json"
        write_json(visual_path, visual)

        semantic_regions_by_id = {item["id"]: item for item in semantic_regions}
        visual_by_id = {item["id"]: item for item in visual_regions}
        regions = [
            {
                "id": region_id,
                "structure": semantic_regions_by_id[region_id]["structure"],
                "semantic": semantic_regions_by_id[region_id]["semantic"],
                "visual": visual_by_id[region_id]["visual"],
                "layout_deviation_pt": visual_by_id[region_id]["layout_deviation_pt"],
            }
            for region_id in validation["required_regions"]
        ]
        provider_runs = observation["provider_runs"]
        metrics = {
            "layout_deviation_pt": max(item["layout_deviation_pt"] for item in visual_regions),
            "component_reuse_rate": sum(1 for item in bindings if item["reused"]) / len(bindings),
            "magic_numbers": len(literals),
            "repair_iterations": len(observation["repair_events"]),
            "manual_minutes": sum(item["duration_seconds"] for item in observation["manual_interventions"]) / 60,
        }
        thresholds = validation["thresholds"]
        passed = all(
            item[status] == "passed"
            for item in regions
            for status in ("structure", "semantic", "visual")
        ) and all(
            (
                metrics["layout_deviation_pt"] <= thresholds["max_layout_deviation_pt"],
                metrics["component_reuse_rate"] >= thresholds["min_component_reuse_rate"],
                metrics["magic_numbers"] <= thresholds["max_magic_numbers"],
                metrics["repair_iterations"] <= thresholds["max_repair_iterations"],
                sum(item["input_tokens"] for item in provider_runs) <= thresholds["max_input_tokens"],
                metrics["manual_minutes"] <= thresholds["max_manual_minutes"],
            )
        )
        result = {
            "run_result_version": "1.1.0",
            "status": "passed" if passed else "failed",
            "variant": input_context["variant"],
            "model": os.environ["DCC_MODEL"],
            "reasoning": os.environ["DCC_REASONING"],
            "code_baseline_commit": os.environ["DCC_CODE_BASELINE_COMMIT"],
            "reference_sha256": reference_ref["sha256"],
            "provider_run_id": provider_runs[0]["id"],
            "model_usage": {
                "input_tokens": sum(item["input_tokens"] for item in provider_runs),
                "output_tokens": sum(item["output_tokens"] for item in provider_runs),
            },
            "metrics": metrics,
            "regions": regions,
            "evidence": {
                "actual_screenshot": probe["actual_screenshot"],
                "validator_probe": {"path": probe_path.name, "sha256": probe_hash},
                "semantic_snapshot": {"path": semantic_path.name, "sha256": sha256(semantic_path)},
                "visual_diff": {"path": visual_path.name, "sha256": sha256(visual_path)},
                "run_observation": {"path": observation_path.name, "sha256": sha256(observation_path)},
            },
        }
        write_json(Path(os.environ["DCC_RUN_RESULT"]), result)
    except (KeyError, IndexError, OSError, TypeError, ValueError, struct.error, zlib.error, subprocess.SubprocessError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
