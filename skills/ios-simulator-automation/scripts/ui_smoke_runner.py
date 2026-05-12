#!/usr/bin/env python3
"""
UI Smoke Runner

Runs named-intent UI smoke flows from a YAML/JSON spec and enforces
post-condition assertions via accessibility tree polling.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app_launcher import AppLauncher
from app_state_capture import AppStateCapture
from common import resolve_udid
from navigator import Navigator


@dataclass
class StepResult:
    success: bool
    message: str


def load_spec(spec_path: Path) -> dict[str, Any]:
    text = spec_path.read_text(encoding="utf-8")

    # 1) JSON (fast path)
    with_json = None
    try:
        with_json = json.loads(text)
    except json.JSONDecodeError:
        with_json = None

    if isinstance(with_json, dict):
        return with_json

    # 2) YAML via Ruby stdlib Psych (no external Python dependency)
    ruby_code = r"""
require "json"
require "yaml"
input = File.read(ARGV[0], mode: "r:bom|utf-8")
data = Psych.safe_load(
  input,
  permitted_classes: [],
  permitted_symbols: [],
  aliases: false,
  filename: ARGV[0],
  fallback: nil
)
puts JSON.generate(data)
"""
    completed = subprocess.run(
        ["ruby", "-e", ruby_code, str(spec_path)],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Failed to parse UI smoke spec as YAML. "
            f"ruby stderr: {completed.stderr.strip() or '<empty>'}"
        )

    parsed = json.loads(completed.stdout)
    if not isinstance(parsed, dict):
        raise RuntimeError("UI smoke spec root must be an object/map")
    return parsed


def resolve_target(step: dict[str, Any]) -> tuple[str | None, str | None]:
    target = step.get("target")
    target_id = step.get("id")
    target_text = step.get("text")
    if isinstance(target, dict):
        target_id = target.get("id", target_id)
        target_text = target.get("text", target_text)
    return (
        target_id if isinstance(target_id, str) and target_id else None,
        target_text if isinstance(target_text, str) and target_text else None,
    )


def resolve_expectation(step: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    expect_id = None
    expect_text = None
    expect_value = None

    expect = step.get("expect")
    if isinstance(expect, dict):
        raw_id = expect.get("id")
        raw_text = expect.get("text")
        raw_value = expect.get("value")
        raw_value_env = expect.get("value_env") or expect.get("value_from_env")

        if isinstance(raw_id, str) and raw_id:
            expect_id = raw_id
        if isinstance(raw_text, str) and raw_text:
            expect_text = raw_text
        if isinstance(raw_value, str):
            expect_value = raw_value
        elif isinstance(raw_value_env, str) and raw_value_env:
            value = os.environ.get(raw_value_env)
            if value is None:
                raise RuntimeError(
                    f"Expectation references missing env var: {raw_value_env}"
                )
            expect_value = value

    # assert step can use direct id/text/value if expect omitted
    if expect is None and step.get("action") == "assert":
        target_id, target_text = resolve_target(step)
        if target_id:
            expect_id = target_id
        if target_text:
            expect_text = target_text
        raw_value = step.get("value")
        if isinstance(raw_value, str):
            expect_value = raw_value

    return expect_id, expect_text, expect_value


def resolve_step_value(step: dict[str, Any]) -> str:
    raw_value = step.get("value")
    if isinstance(raw_value, str):
        return raw_value

    value_env = step.get("value_env")
    if isinstance(value_env, str) and value_env:
        value = os.environ.get(value_env)
        if value is None:
            raise RuntimeError(f"Step references missing env var: {value_env}")
        return value

    raise RuntimeError("set_value step requires `value` or `value_env`")


def run_step(
    navigator: Navigator,
    step: dict[str, Any],
    timeout: float,
    poll_interval: float,
    fail_on_duplicate_id: bool,
) -> StepResult:
    action = step.get("action")
    if not isinstance(action, str):
        return StepResult(False, "Step missing action")

    action = action.strip().lower()
    target_id, target_text = resolve_target(step)

    if action == "tap":
        success, message = navigator.find_and_tap(
            text=target_text,
            identifier=target_id,
            element_type=step.get("type") if isinstance(step.get("type"), str) else None,
            index=int(step.get("index", 0)),
        )
        if not success:
            return StepResult(False, message)
    elif action == "set_value":
        value = resolve_step_value(step)
        success, message = navigator.find_and_enter_text(
            text_to_enter=value,
            find_text=target_text,
            element_type=step.get("type") if isinstance(step.get("type"), str) else "TextField",
            identifier=target_id,
            index=int(step.get("index", 0)),
        )
        if not success:
            return StepResult(False, message)
    elif action == "assert":
        # no-op; assertion handled below
        message = "Assert step"
    else:
        return StepResult(False, f"Unsupported action: {action}")

    expect_id, expect_text, expect_value = resolve_expectation(step)
    has_expectation = any([expect_id, expect_text, expect_value])
    if has_expectation:
        ok, expectation_message = navigator.wait_for_expectations(
            expect_id=expect_id,
            expect_text=expect_text,
            expect_value=expect_value,
            timeout=float(step.get("timeout", timeout)),
            poll_interval=float(step.get("poll_interval", poll_interval)),
            fail_on_duplicate_id=fail_on_duplicate_id,
        )
        if not ok:
            return StepResult(False, expectation_message)

    return StepResult(True, message)


def capture_failure_state(
    output_dir: Path,
    udid: str,
    app_bundle_id: str | None,
    app_name: str | None = None,
) -> str:
    capturer = AppStateCapture(
        app_bundle_id=app_bundle_id,
        udid=udid,
        inline=False,
        screenshot_size="half",
    )
    summary = capturer.capture_all(
        output_dir=str(output_dir),
        log_lines=120,
        app_name=app_name,
    )
    return str(summary.get("output_dir", output_dir))


def maybe_launch_app(spec: dict[str, Any], udid: str) -> None:
    app_bundle_id = spec.get("app_bundle_id")
    if not isinstance(app_bundle_id, str) or not app_bundle_id:
        return

    launcher = AppLauncher(udid=udid)
    success, pid = launcher.launch(app_bundle_id)
    if not success:
        raise RuntimeError(f"Failed to launch app: {app_bundle_id}")
    print(f"Launched app: {app_bundle_id} (pid={pid if pid else 'unknown'})")
    time.sleep(1.0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run UI smoke flows from YAML/JSON spec")
    parser.add_argument("--spec", required=True, help="Path to UI smoke spec (.yml/.yaml/.json)")
    parser.add_argument("--udid", help="Simulator UDID (defaults to booted simulator)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Default expectation timeout per step (seconds)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.3,
        help="Default expectation poll interval (seconds)",
    )
    parser.add_argument(
        "--output-dir",
        default=".codex/ui-smoke-artifacts",
        help="Directory to write failure artifacts",
    )
    parser.add_argument(
        "--fail-on-duplicate-id",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fail when AXUniqueId is duplicated (default: true)",
    )
    args = parser.parse_args()

    spec_path = Path(args.spec).resolve()
    if not spec_path.exists():
        print(f"Error: spec not found: {spec_path}", file=sys.stderr)
        return 2

    try:
        spec = load_spec(spec_path)
    except Exception as exc:
        print(f"Error: failed to parse spec: {exc}", file=sys.stderr)
        return 2

    flows = spec.get("flows")
    if not isinstance(flows, list) or not flows:
        print("Error: spec must contain non-empty `flows` array", file=sys.stderr)
        return 2

    udid_from_spec = spec.get("udid")
    udid_input = args.udid if args.udid else (udid_from_spec if isinstance(udid_from_spec, str) else None)
    try:
        udid = resolve_udid(udid_input)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        maybe_launch_app(spec, udid)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3

    navigator = Navigator(udid=udid)

    total_steps = 0
    for flow_index, flow in enumerate(flows, start=1):
        if not isinstance(flow, dict):
            print(f"Error: flow #{flow_index} is not an object", file=sys.stderr)
            return 2

        flow_name = flow.get("name")
        if not isinstance(flow_name, str) or not flow_name:
            flow_name = f"flow-{flow_index}"

        steps = flow.get("steps")
        if not isinstance(steps, list) or not steps:
            print(f"Error: {flow_name} has no steps", file=sys.stderr)
            return 2

        print(f"Running {flow_name} ({len(steps)} steps)")
        for step_index, step in enumerate(steps, start=1):
            total_steps += 1
            if not isinstance(step, dict):
                print(f"  [{step_index}] FAIL: step is not an object", file=sys.stderr)
                failure_path = capture_failure_state(
                    output_dir=output_dir,
                    udid=udid,
                    app_bundle_id=spec.get("app_bundle_id") if isinstance(spec.get("app_bundle_id"), str) else None,
                    app_name=flow_name,
                )
                print(f"  State captured: {failure_path}")
                return 10

            try:
                result = run_step(
                    navigator=navigator,
                    step=step,
                    timeout=args.timeout,
                    poll_interval=args.poll_interval,
                    fail_on_duplicate_id=args.fail_on_duplicate_id,
                )
            except Exception as exc:
                result = StepResult(False, str(exc))

            if result.success:
                print(f"  [{step_index}] PASS: {result.message}")
                continue

            print(f"  [{step_index}] FAIL: {result.message}", file=sys.stderr)
            failure_path = capture_failure_state(
                output_dir=output_dir,
                udid=udid,
                app_bundle_id=spec.get("app_bundle_id") if isinstance(spec.get("app_bundle_id"), str) else None,
                app_name=flow_name,
            )
            print(f"  State captured: {failure_path}")
            return 10

    print(f"UI smoke passed: {len(flows)} flow(s), {total_steps} step(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
