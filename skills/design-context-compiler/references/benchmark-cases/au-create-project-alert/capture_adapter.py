#!/usr/bin/env python3
"""Capture AUCreateProjectAlertView from the frozen iOS Simulator fixture."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
from contextlib import contextmanager


class CaptureError(ValueError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, check: bool = True, echo: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if echo and result.stdout:
        print(result.stdout, end="")
    if echo and result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if check and result.returncode != 0:
        raise CaptureError(f"command failed with exit {result.returncode}: {command[0]}")
    return result


def is_not_installed(result: subprocess.CompletedProcess[str]) -> bool:
    detail = f"{result.stdout}\n{result.stderr}".lower()
    return (
        "not installed" in detail
        or "no such app" in detail
        or (
            "domain=nsposixerrordomain" in detail
            and "code=2" in detail
            and "no such file or directory" in detail
        )
    )


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise CaptureError("capture screenshot is not a PNG")
    return struct.unpack(">II", data[16:24])


@contextmanager
def evaluator_dependency(runtime: dict, worktree: Path):
    setup = runtime.get("evaluator_dependency_setup", {"mode": "none"})
    if setup.get("mode") == "none":
        yield
        return
    if setup.get("mode") != "unityframework-arm64-simulator-stub-v1":
        raise CaptureError("unsupported evaluator dependency setup")
    generator = Path(setup["generator"]["path"])
    if not generator.is_file() or sha256(generator) != setup["generator"]["sha256"]:
        raise CaptureError("evaluator dependency generator identity mismatch")
    with tempfile.TemporaryDirectory(prefix="dcc-evaluator-dependency-") as directory:
        root = Path(directory)
        contract = root / "contract.json"
        state = root / "state"
        contract.write_text(json.dumps(setup, sort_keys=True), encoding="utf-8")
        run([
            sys.executable, str(generator), "apply", "--contract", str(contract),
            "--worktree", str(worktree), "--state", str(state),
        ])
        try:
            yield
        finally:
            run([
                sys.executable, str(generator), "restore", "--contract", str(contract),
                "--worktree", str(worktree), "--state", str(state),
            ])


def main() -> int:
    try:
        runtime = json.loads(os.environ["DCC_CAPTURE_RUNTIME_JSON"])
        if runtime.get("mode") != "ios-simulator":
            raise CaptureError("AUCreateProjectAlert capture requires ios-simulator runtime")
        wrapper = Path(runtime["verification_wrapper"]["path"])
        simctl = Path(runtime["simctl"]["path"])
        for label, tool in (("verification wrapper", wrapper), ("simctl", simctl)):
            if not tool.is_file() or sha256(tool) != runtime[label.replace(" ", "_")]["sha256"]:
                raise CaptureError(f"{label} identity mismatch")

        destination = runtime["destination"]
        devices = json.loads(run([str(simctl), "list", "-j", "devices", "available"], echo=False).stdout)["devices"]
        matches = [
            item for item in devices.get(destination["runtime"], [])
            if item.get("udid") == destination["udid"]
            and item.get("name") == destination["device_name"]
            and item.get("deviceTypeIdentifier") == destination["device_type_identifier"]
        ]
        if len(matches) != 1:
            raise CaptureError("frozen Simulator destination is unavailable")
        runtimes = json.loads(run([str(simctl), "list", "-j", "runtimes"], echo=False).stdout)["runtimes"]
        runtime_matches = [
            item for item in runtimes
            if item.get("identifier") == destination["runtime"]
            and item.get("version") == destination["runtime_version"]
            and item.get("buildversion") == destination["runtime_build_version"]
            and item.get("isAvailable") is not False
        ]
        if len(runtime_matches) != 1:
            raise CaptureError("frozen Simulator runtime version/build is unavailable")
        if matches[0].get("state") != "Booted":
            run([str(simctl), "boot", destination["udid"]], check=False)
            run([str(simctl), "bootstatus", destination["udid"], "-b"])

        stale_container = run([
            str(simctl), "get_app_container", destination["udid"], runtime["app_bundle_id"], "data"
        ], check=False, echo=False)
        if stale_container.returncode == 0:
            run([str(simctl), "uninstall", destination["udid"], runtime["app_bundle_id"]])
        elif not is_not_installed(stale_container):
            raise CaptureError("unable to prove stale app container is absent")
        post_uninstall = run([
            str(simctl), "get_app_container", destination["udid"], runtime["app_bundle_id"], "data"
        ], check=False, echo=False)
        if post_uninstall.returncode == 0 or not is_not_installed(post_uninstall):
            raise CaptureError("stale app container still exists before capture test")
        worktree = Path(os.environ["DCC_WORKTREE"])
        command = [
            str(wrapper), "--repo-root", str(worktree), "--",
            "-workspace", runtime["workspace"],
            "-scheme", runtime["scheme"],
            "-destination", f"id={destination['udid']}",
            f"-only-testing:{runtime['test_selector']}",
            "test",
        ]
        with evaluator_dependency(runtime, worktree):
            run(command)
        container = Path(run([
            str(simctl), "get_app_container", destination["udid"], runtime["app_bundle_id"], "data"
        ], echo=False).stdout.strip())
        source_image = container / "Documents" / runtime["artifacts"]["screenshot"]
        source_raw = container / "Documents" / runtime["artifacts"]["raw_probe"]
        if not source_image.is_file() or not source_raw.is_file():
            raise CaptureError("project fixture did not emit both capture artifacts")

        actual = Path(os.environ["DCC_ACTUAL_SCREENSHOT"])
        shutil.copyfile(source_image, actual)
        context = json.loads(Path(os.environ["DCC_INPUT_CONTEXT"]).read_text(encoding="utf-8"))
        raw = json.loads(source_raw.read_text(encoding="utf-8"))
        if raw.get("capture_raw_version") != "1.0.0":
            raise CaptureError("unsupported project raw capture version")
        if raw.get("state") != {"id": "fixture-selected", "selected_entry_index": 0}:
            raise CaptureError("project raw capture state is not fixture-selected")
        expected_environment = context["environment"]
        if raw.get("environment") != {
            "viewport": expected_environment["viewport"],
            "scale": expected_environment["scale"],
            "appearance": expected_environment["appearance"],
            "locale": expected_environment["locale"],
        }:
            raise CaptureError("project raw capture environment mismatch")
        if png_size(actual) != (expected_environment["viewport"]["width"], expected_environment["viewport"]["height"]):
            raise CaptureError("project screenshot viewport mismatch")
        region_ids = [item.get("id") for item in raw.get("regions", [])]
        if len(region_ids) != len(set(region_ids)) or not region_ids:
            raise CaptureError("project raw capture regions are empty or duplicated")

        probe = {
            "validator_probe_version": "1.0.0",
            "case_id": os.environ["DCC_CASE_ID"],
            "variant": os.environ["DCC_VARIANT"],
            "validator_id": os.environ["DCC_VALIDATOR_ID"],
            "capture_adapter_sha256": os.environ["DCC_CAPTURE_ADAPTER_SHA256"],
            "environment": raw["environment"],
            "actual_screenshot": {"path": actual.name, "sha256": sha256(actual)},
            "regions": raw["regions"],
            "bindings": raw["bindings"],
        }
        Path(os.environ["DCC_VALIDATOR_PROBE"]).write_text(
            json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return 0
    except (CaptureError, KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
