#!/usr/bin/env python3
"""Synthetic-only executor used by deterministic benchmark runner self-tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


METRICS = {
    "screenshot-only": {
        "layout_deviation_pt": 4.0,
        "component_reuse_rate": 0.2,
        "magic_numbers": 10,
        "repair_iterations": 4,
        "manual_minutes": 60,
        "input_tokens": 3000,
    },
    "ui-ir": {
        "layout_deviation_pt": 1.5,
        "component_reuse_rate": 0.5,
        "magic_numbers": 5,
        "repair_iterations": 2,
        "manual_minutes": 40,
        "input_tokens": 8000,
    },
    "ui-ir-with-binding": {
        "layout_deviation_pt": 0.5,
        "component_reuse_rate": 1.0,
        "magic_numbers": 2,
        "repair_iterations": 1,
        "manual_minutes": 20,
        "input_tokens": 6000,
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame_edge(frame: dict, edge: str) -> float:
    if edge == "min_x":
        return frame["x"]
    if edge == "mid_x":
        return frame["x"] + frame["width"] / 2
    if edge == "max_x":
        return frame["x"] + frame["width"]
    if edge == "min_y":
        return frame["y"]
    if edge == "mid_y":
        return frame["y"] + frame["height"] / 2
    if edge == "max_y":
        return frame["y"] + frame["height"]
    raise ValueError(f"unsupported edge: {edge}")


def derived_anchor(anchor: dict, region_id: str, reference_frames: dict, actual_frames: dict) -> dict:
    metric = anchor["metric"]
    if metric == "position":
        reference = [reference_frames[region_id]["x"], reference_frames[region_id]["y"]]
        actual = [actual_frames[region_id]["x"], actual_frames[region_id]["y"]]
    elif metric == "size":
        reference = [reference_frames[region_id]["width"], reference_frames[region_id]["height"]]
        actual = [actual_frames[region_id]["width"], actual_frames[region_id]["height"]]
    else:
        reference = [anchor["reference_value"]]
        relative_id = anchor["relative_to_region_id"]
        actual = [
            frame_edge(actual_frames[region_id], anchor["region_edge"])
            - frame_edge(actual_frames[relative_id], anchor["relative_edge"])
        ]
    deviation = max(abs(actual_value - reference_value) for actual_value, reference_value in zip(actual, reference))
    return {
        "id": anchor["id"],
        "metric": metric,
        "reference_value": reference,
        "actual_value": actual,
        "deviation_pt": deviation,
    }


def derived_region(expected: dict, observed: dict) -> dict:
    return {
        "id": expected["id"],
        "frame": observed["frame"],
        "structure": "passed" if observed["visible"] and observed["parent_id"] == expected["parent_id"] and observed["child_ids"] == expected["child_ids"] else "failed",
        "semantic": "passed" if observed["runtime_type"] == expected["runtime_type"] and observed["accessibility_identifier"] == expected["accessibility_identifier"] else "failed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["implementation", "validation"], required=True)
    args = parser.parse_args()
    if os.environ.get("DCC_EVIDENCE_STATUS") != "synthetic-example":
        print("fake executor refuses non-synthetic evidence", file=sys.stderr)
        return 2
    variant = os.environ["DCC_VARIANT"]
    if variant not in METRICS:
        return 2
    worktree = Path(os.environ["DCC_WORKTREE"])
    if args.phase == "implementation":
        if os.environ.get("DCC_FAKE_REQUIRE_MINIMAL_SCOPE") == "1" and (worktree / "secret.txt").exists():
            print("full source checkout leaked into provider worktree", file=sys.stderr)
            return 2
        if os.environ.get("DCC_FAKE_PROVIDER_FORBID_OVERLAY") == "1":
            archived_overlay = Path(os.environ["DCC_INPUT_CONTEXT"]).parent / "capture-overlay.patch"
            if archived_overlay.exists() or (worktree / "capture-only.txt").exists() or (worktree / "baseline.txt").read_text(encoding="utf-8") != "baseline\n":
                print("evaluator capture overlay leaked into implementation phase", file=sys.stderr)
                return 2
        input_dir = Path(os.environ["DCC_INPUT_DIR"])
        if os.environ.get("DCC_FAKE_MUTATE_INPUT") == "1":
            input_context = json.loads(Path(os.environ["DCC_INPUT_CONTEXT"]).read_text(encoding="utf-8"))
            first_input = input_dir.parent / input_context["inputs"][0]["path"]
            first_input.write_text("mutated by adversarial synthetic executor\n", encoding="utf-8")
        if os.environ.get("DCC_FAKE_ADD_INPUT") == "1":
            (input_dir / "agent-packet.json").write_text("{}\n", encoding="utf-8")
        if os.environ.get("DCC_FAKE_WRITE_OUTSIDE_SCOPE") == "1":
            (worktree / "OutsideScope.swift").write_text("let outsideScope = true\n", encoding="utf-8")
        if os.environ.get("DCC_FAKE_HIDE_OUTSIDE_SCOPE") == "1":
            (worktree / "OutsideScope.swift").write_text("let hiddenOutsideScope = true\n", encoding="utf-8")
            exclude = worktree / ".git/info/exclude"
            exclude.write_text(exclude.read_text(encoding="utf-8") + "\nOutsideScope.swift\n", encoding="utf-8")
        metrics = METRICS[variant]
        validation = json.loads((input_dir / "validation-config.json").read_text(encoding="utf-8"))
        binding_specs = validation["required_bindings"]
        binding_count = len(binding_specs)
        reused_count = round(metrics["component_reuse_rate"] * binding_count)
        lines = [f"{binding['code_symbol']} reused={index < reused_count}" for index, binding in enumerate(binding_specs)]
        lines.extend(f"view.frame.origin.x = CGFloat({index})" for index in range(metrics["magic_numbers"]))
        (worktree / "BenchmarkGenerated.swift").write_text("\n".join(lines) + "\n", encoding="utf-8")
        provider_id = f"synthetic-{variant}"
        observation_payload = {
            "run_observation_version": "1.1.0",
            "case_id": os.environ["DCC_CASE_ID"],
            "variant": variant,
            "executor_adapter_sha256": os.environ["DCC_EXECUTOR_ADAPTER_SHA256"],
            "model": os.environ["DCC_MODEL"],
            "reasoning": os.environ["DCC_REASONING"],
            "provider_cli": {
                "name": "synthetic-test-adapter",
                "version": "1.0.0",
                "launcher_path": os.environ["DCC_EXPECTED_PROVIDER_LAUNCHER_PATH"],
                "native_path": os.environ["DCC_EXPECTED_PROVIDER_NATIVE_PATH"],
                "launcher_sha256": sha256(Path(__file__)),
                "native_sha256": sha256(Path(__file__)),
                "package_json_sha256": os.environ["DCC_EXPECTED_PROVIDER_PACKAGE_JSON_SHA256"],
            },
            "provider_event_stream_sha256": hashlib.sha256(b"").hexdigest(),
            "provider_runs": [
                {
                    "id": provider_id,
                    "input_tokens": metrics["input_tokens"],
                    "cached_input_tokens": 0,
                    "output_tokens": 1000,
                    "reasoning_output_tokens": 0,
                }
            ],
            "repair_events": [
                {"id": f"repair-{index}", "provider_run_id": provider_id, "reason": "synthetic repair"}
                for index in range(metrics["repair_iterations"])
            ],
            "manual_interventions": ([{"id": "manual-0", "duration_seconds": metrics["manual_minutes"] * 60, "reason": "synthetic timing"}] if metrics["manual_minutes"] else []),
        }
        Path(os.environ["DCC_RUN_OBSERVATION"]).write_text(json.dumps(observation_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if os.environ.get("DCC_FAKE_EVENT_STREAM_MISMATCH") == "1":
            print('{"type":"synthetic-unreceipted-event"}')
        if os.environ.get("DCC_FAKE_PREWRITE_VALIDATION") == "1":
            (input_dir.parent / "benchmark-run-result.json").write_text("{}\n", encoding="utf-8")
        if os.environ.get("DCC_FAKE_MOVE_HEAD") == "1":
            subprocess.run(["git", "add", "BenchmarkGenerated.swift"], cwd=worktree, check=True)
            subprocess.run(
                ["git", "-c", "user.name=Adversarial Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "move HEAD"],
                cwd=worktree,
                check=True,
            )
        return 0

    if os.environ.get("DCC_FAKE_VALIDATOR_FORBID_OVERLAY") == "1":
        if (worktree / "capture-only.txt").exists() or (worktree / "baseline.txt").read_text(encoding="utf-8") != "baseline\n":
            print("evaluator capture overlay leaked into validation phase", file=sys.stderr)
            return 2
    run_dir = Path(os.environ["DCC_RUN_DIR"])
    input_context = json.loads(Path(os.environ["DCC_INPUT_CONTEXT"]).read_text(encoding="utf-8"))
    validation_item = next(item for item in input_context["inputs"] if item["kind"] == "validation-config")
    validation = json.loads((run_dir / validation_item["path"]).read_text(encoding="utf-8"))
    actual = run_dir / "actual.png"
    probe = run_dir / "validator-probe.json"
    semantic = run_dir / "semantic-snapshot.json"
    visual_diff = run_dir / "visual-diff.json"
    if not actual.is_file() or not probe.is_file():
        print("capture evidence is missing", file=sys.stderr)
        return 2
    metrics = METRICS[variant]
    binding_specs = validation["required_bindings"]
    binding_count = len(binding_specs)
    probe_payload = json.loads(probe.read_text(encoding="utf-8"))
    probe_regions = {item["id"]: item for item in probe_payload["regions"]}
    semantic_regions = [derived_region(item, probe_regions[item["id"]]) for item in validation["reference_regions"]]
    observed_binding_ids = {item["id"] for item in probe_payload["bindings"]}
    probe_hash = sha256(probe)
    semantic_payload = {
        "semantic_evidence_version": "1.1.0",
        "case_id": os.environ["DCC_CASE_ID"],
        "variant": variant,
        "validator_id": os.environ["DCC_VALIDATOR_ID"],
        "validator_adapter_sha256": os.environ["DCC_VALIDATOR_ADAPTER_SHA256"],
        "validator_probe_sha256": probe_hash,
        "capture_adapter_sha256": probe_payload["capture_adapter_sha256"],
        "regions": semantic_regions,
        "required_bindings": [
            {
                "id": binding["id"],
                "registry_entry_id": binding["registry_entry_id"],
                "code_symbol": binding["code_symbol"],
                "source": binding["source"],
                "region_id": binding["region_id"],
                "runtime_type": binding["runtime_type"],
                "runtime_observed": binding["id"] in observed_binding_ids,
                "reused": binding["id"] in observed_binding_ids,
                "locations": ([{"path": binding["source"], "line": index + 1}] if binding["id"] in observed_binding_ids else []),
            }
            for index, binding in enumerate(binding_specs)
        ],
        "unmapped_literals": [
            {
                "kind": "layout",
                "value": str(index),
                "location": {"path": "BenchmarkGenerated.swift", "line": binding_count + index + 1},
            }
            for index in range(metrics["magic_numbers"])
        ],
    }
    semantic.write_text(json.dumps(semantic_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reference_frames = {item["id"]: item["frame"] for item in validation["reference_regions"]}
    actual_frames = {item["id"]: item["frame"] for item in probe_payload["regions"]}
    visual_regions = []
    for anchor_region in validation["required_anchors"]:
        anchors = [
            derived_anchor(anchor, anchor_region["region_id"], reference_frames, actual_frames)
            for anchor in anchor_region["anchors"]
        ]
        visual_regions.append(
            {
                "id": anchor_region["region_id"],
                "visual": "passed",
                "layout_deviation_pt": max((item["deviation_pt"] for item in anchors), default=0),
                "pixel_difference_ratio": 0,
                "anchors": anchors,
            }
        )
    visual_payload = {
        "visual_diff_version": "1.1.0",
        "case_id": os.environ["DCC_CASE_ID"],
        "variant": variant,
        "validator_id": os.environ["DCC_VALIDATOR_ID"],
        "validator_adapter_sha256": os.environ["DCC_VALIDATOR_ADAPTER_SHA256"],
        "validator_probe_sha256": probe_hash,
        "capture_adapter_sha256": probe_payload["capture_adapter_sha256"],
        "reference_sha256": os.environ["DCC_REFERENCE_SHA256"],
        "actual_sha256": sha256(actual),
        "regions": visual_regions,
    }
    visual_diff.write_text(json.dumps(visual_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    observation = Path(os.environ["DCC_RUN_OBSERVATION"])
    observation_payload = json.loads(observation.read_text(encoding="utf-8"))
    provider_id = observation_payload["provider_runs"][0]["id"]
    visual_by_id = {item["id"]: item for item in visual_regions}
    semantic_by_id = {item["id"]: item for item in semantic_regions}
    regions = [
        {
            "id": region,
            "structure": semantic_by_id[region]["structure"],
            "semantic": semantic_by_id[region]["semantic"],
            "visual": visual_by_id[region]["visual"],
            "layout_deviation_pt": visual_by_id[region]["layout_deviation_pt"],
        }
        for region in validation["required_regions"]
    ]
    derived_layout_deviation = max(item["layout_deviation_pt"] for item in visual_regions)
    derived_reuse_rate = len(observed_binding_ids) / binding_count
    thresholds = validation["thresholds"]
    passed = all(
        item[status] == "passed"
        for item in regions
        for status in ("structure", "semantic", "visual")
    ) and all(
        (
            derived_layout_deviation <= thresholds["max_layout_deviation_pt"],
            derived_reuse_rate >= thresholds["min_component_reuse_rate"],
            metrics["magic_numbers"] <= thresholds["max_magic_numbers"],
            metrics["repair_iterations"] <= thresholds["max_repair_iterations"],
            metrics["input_tokens"] <= thresholds["max_input_tokens"],
            metrics["manual_minutes"] <= thresholds["max_manual_minutes"],
        )
    )
    result = {
        "run_result_version": "1.1.0",
        "status": "passed" if passed else "failed",
        "variant": variant,
        "model": os.environ["DCC_MODEL"],
        "reasoning": os.environ["DCC_REASONING"],
        "code_baseline_commit": os.environ["DCC_CODE_BASELINE_COMMIT"],
        "reference_sha256": os.environ["DCC_REFERENCE_SHA256"],
        "provider_run_id": provider_id,
        "model_usage": {"input_tokens": metrics["input_tokens"], "output_tokens": 1000},
        "metrics": {
            "layout_deviation_pt": derived_layout_deviation,
            "component_reuse_rate": derived_reuse_rate,
            **{key: metrics[key] for key in ("magic_numbers", "repair_iterations", "manual_minutes")},
        },
        "regions": regions,
        "evidence": {
            "actual_screenshot": {"path": actual.name, "sha256": sha256(actual)},
            "validator_probe": {"path": probe.name, "sha256": probe_hash},
            "semantic_snapshot": {"path": semantic.name, "sha256": sha256(semantic)},
            "visual_diff": {"path": visual_diff.name, "sha256": sha256(visual_diff)},
            "run_observation": {"path": observation.name, "sha256": sha256(observation)},
        },
    }
    if os.environ.get("DCC_FAKE_ABSOLUTE_EVIDENCE") == "1":
        result["evidence"]["actual_screenshot"]["path"] = str(actual.resolve())
    Path(os.environ["DCC_RUN_RESULT"]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if os.environ.get("DCC_FAKE_VALIDATOR_MUTATE_CAPTURE") == "1":
        actual.write_bytes(actual.read_bytes() + b"validator tamper")
    return 0


if __name__ == "__main__":
    sys.exit(main())
