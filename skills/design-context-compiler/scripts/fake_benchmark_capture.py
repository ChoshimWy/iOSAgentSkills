#!/usr/bin/env python3
"""Synthetic-only capture adapter for deterministic benchmark runner self-tests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import time
import zlib


DEVIATION = {
    "screenshot-only": 4.0,
    "ui-ir": 1.5,
    "ui-ir-with-binding": 0.5,
}
REUSE_RATE = {
    "screenshot-only": 0.2,
    "ui-ir": 0.5,
    "ui-ir-with-binding": 1.0,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_png(width: int, height: int) -> bytes:
    """Return one deterministic opaque-black RGB PNG without third-party dependencies."""

    def chunk(kind: bytes, payload: bytes) -> bytes:
        checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    rows = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows, 9))
        + chunk(b"IEND", b"")
    )


def main() -> int:
    if os.environ.get("DCC_EVIDENCE_STATUS") != "synthetic-example":
        print("fake capture refuses non-synthetic evidence", file=sys.stderr)
        return 2
    variant = os.environ.get("DCC_VARIANT", "")
    if variant not in DEVIATION:
        return 2
    run_dir = Path(os.environ["DCC_RUN_DIR"])
    worktree = Path(os.environ["DCC_WORKTREE"])
    if os.environ.get("DCC_FAKE_CAPTURE_REQUIRE_OVERLAY") == "1":
        marker = worktree / "capture-only.txt"
        baseline = worktree / "baseline.txt"
        if not marker.is_file() or marker.read_text(encoding="utf-8") != "evaluator capture only\n":
            print("capture overlay marker is unavailable", file=sys.stderr)
            return 2
        if baseline.read_text(encoding="utf-8") != "capture overlay\n":
            print("capture overlay baseline edit is unavailable", file=sys.stderr)
            return 2
    if os.environ.get("DCC_FAKE_CAPTURE_MUTATE_OVERLAY") == "1":
        (worktree / "capture-mutation.txt").write_text("capture mutation outside overlay\n", encoding="utf-8")
    if os.environ.get("DCC_FAKE_CAPTURE_TIMEOUT_AFTER_MUTATION") == "1":
        (worktree / "capture-mutation.txt").write_text("capture mutation before timeout\n", encoding="utf-8")
        time.sleep(60)
    if os.environ.get("DCC_FAKE_CAPTURE_BREAK_OVERLAY") == "1":
        (worktree / "baseline.txt").write_text("capture mutated overlay\n", encoding="utf-8")
    if os.environ.get("DCC_FAKE_CAPTURE_FAIL") == "1":
        print("synthetic capture failure", file=sys.stderr)
        return 3
    input_context = json.loads(Path(os.environ["DCC_INPUT_CONTEXT"]).read_text(encoding="utf-8"))
    validation_item = next(item for item in input_context["inputs"] if item["kind"] == "validation-config")
    validation = json.loads((run_dir / validation_item["path"]).read_text(encoding="utf-8"))
    viewport = input_context["environment"]["viewport"]
    actual = Path(os.environ["DCC_ACTUAL_SCREENSHOT"])
    actual.write_bytes(make_png(viewport["width"], viewport["height"]))

    regions = []
    for index, item in enumerate(validation["reference_regions"]):
        frame = dict(item["frame"])
        if index == 0:
            delta = DEVIATION[variant]
            frame["x"] += delta
            frame["width"] = max(0, frame["width"] - delta)
        regions.append(
            {
                "id": item["id"],
                "frame": frame,
                "runtime_type": item["runtime_type"],
                "accessibility_identifier": item["accessibility_identifier"],
                "visible": True,
                "parent_id": item["parent_id"],
                "child_ids": item["child_ids"],
            }
        )
    binding_specs = validation["required_bindings"]
    reused_count = round(REUSE_RATE[variant] * len(binding_specs))
    probe = {
        "validator_probe_version": "1.0.0",
        "case_id": input_context["case_id"],
        "variant": variant,
        "validator_id": os.environ["DCC_VALIDATOR_ID"],
        "capture_adapter_sha256": os.environ["DCC_CAPTURE_ADAPTER_SHA256"],
        "environment": {
            "viewport": viewport,
            "scale": input_context["environment"]["scale"],
            "appearance": input_context["environment"]["appearance"],
            "locale": input_context["environment"]["locale"],
        },
        "actual_screenshot": {"path": actual.name, "sha256": sha256(actual)},
        "regions": regions,
        "bindings": [
            {
                "id": binding["id"],
                "region_id": binding["region_id"],
                "runtime_type": binding["runtime_type"],
            }
            for binding in binding_specs[:reused_count]
        ],
    }
    Path(os.environ["DCC_VALIDATOR_PROBE"]).write_text(
        json.dumps(probe, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if os.environ.get("DCC_FAKE_CAPTURE_MUTATE_PATCH") == "1":
        (run_dir / "implementation-output.patch").write_text("capture tampered patch\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
