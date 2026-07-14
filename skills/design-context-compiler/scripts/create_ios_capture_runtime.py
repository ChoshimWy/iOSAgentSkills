#!/usr/bin/env python3
"""Freeze a machine-specific iOS Simulator capture runtime JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_output(command: list[str]) -> str:
    return subprocess.run(command, text=True, capture_output=True, check=True).stdout.strip()


def create_dependency_setup(args: argparse.Namespace) -> dict:
    if args.evaluator_dependency_generator is None:
        return {"mode": "none"}
    if args.source_checkout is None or args.unity_xcframework is None or args.unity_pod_copy_script is None:
        raise ValueError("Unity evaluator dependency setup requires source checkout and both relative Pod paths")
    source = args.source_checkout.resolve()
    generator = args.evaluator_dependency_generator.resolve()
    clang = Path(command_output(["xcrun", "--find", "clang"])).resolve()
    sdk = Path(command_output(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"])).resolve()
    sdk_version = command_output(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"])
    sdk_build = command_output(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-build-version"])
    xcframework = Path(args.unity_xcframework)
    copy_script = Path(args.unity_pod_copy_script)
    for value, label in ((xcframework, "Unity XCFramework"), (copy_script, "Unity Pod copy script")):
        if value.is_absolute() or ".." in value.parts:
            raise ValueError(f"{label} must be source-checkout relative")
    info = source / xcframework / "Info.plist"
    script = source / copy_script
    settings = sdk / "SDKSettings.plist"
    for value, label in ((generator, "dependency generator"), (clang, "clang"), (settings, "Simulator SDK settings"), (info, "Unity XCFramework Info.plist"), (script, "Unity Pod copy script")):
        if not value.is_file():
            raise ValueError(f"{label} is missing: {value}")
    setup = {
        "mode": "unityframework-arm64-simulator-stub-v1",
        "generator": {"path": str(generator), "sha256": sha256(generator)},
        "clang": {"path": str(clang), "sha256": sha256(clang)},
        "sdk": {
            "path": str(sdk),
            "version": sdk_version,
            "build_version": sdk_build,
            "settings_sha256": sha256(settings),
        },
        "xcframework_path": str(xcframework),
        "pod_copy_script_path": str(copy_script),
        "baseline": {
            "xcframework_info_sha256": sha256(info),
            "pod_copy_script_sha256": sha256(script),
        },
        "product": {},
    }
    with tempfile.TemporaryDirectory(prefix="dcc-unity-stub-contract-") as directory:
        contract = Path(directory) / "contract.json"
        contract.write_text(json.dumps(setup, sort_keys=True), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(generator), "fingerprint", "--contract", str(contract)],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        if payload.get("status") != "ready":
            raise ValueError("dependency generator fingerprint did not return ready")
        setup["product"] = payload["result"]
    return setup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--udid", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--scheme", required=True)
    parser.add_argument("--test-selector", required=True)
    parser.add_argument("--app-bundle-id", required=True)
    parser.add_argument("--verification-wrapper", type=Path, default=Path.home() / ".codex/bin/codex_verify")
    parser.add_argument("--screenshot", default="dcc-au-create-project-alert-actual.png")
    parser.add_argument("--raw-probe", default="dcc-au-create-project-alert-raw.json")
    parser.add_argument("--evaluator-dependency-generator", type=Path)
    parser.add_argument("--source-checkout", type=Path)
    parser.add_argument("--unity-xcframework")
    parser.add_argument("--unity-pod-copy-script")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError(f"refusing to overwrite capture runtime: {args.output}")
        simctl_result = subprocess.run(["xcrun", "--find", "simctl"], text=True, capture_output=True, check=True)
        simctl = Path(simctl_result.stdout.strip()).resolve()
        wrapper = args.verification_wrapper.expanduser().resolve()
        if not wrapper.is_file() or not simctl.is_file():
            raise ValueError("verification wrapper or simctl is missing")
        devices_result = subprocess.run([str(simctl), "list", "-j", "devices", "available"], text=True, capture_output=True, check=True)
        devices = json.loads(devices_result.stdout)["devices"]
        found = [(runtime, item) for runtime, items in devices.items() for item in items if item.get("udid") == args.udid]
        if len(found) != 1:
            raise ValueError("UDID must identify exactly one available Simulator")
        runtime, device = found[0]
        runtimes_result = subprocess.run([str(simctl), "list", "-j", "runtimes"], text=True, capture_output=True, check=True)
        runtime_matches = [item for item in json.loads(runtimes_result.stdout)["runtimes"] if item.get("identifier") == runtime and item.get("isAvailable") is not False]
        if len(runtime_matches) != 1:
            raise ValueError("device runtime identity is unavailable or ambiguous")
        runtime_info = runtime_matches[0]
        payload = {
            "mode": "ios-simulator",
            "verification_wrapper": {"path": str(wrapper), "sha256": sha256(wrapper)},
            "simctl": {"path": str(simctl), "sha256": sha256(simctl)},
            "workspace": args.workspace,
            "scheme": args.scheme,
            "destination": {
                "udid": args.udid,
                "runtime": runtime,
                "runtime_version": runtime_info["version"],
                "runtime_build_version": runtime_info["buildversion"],
                "device_name": device["name"],
                "device_type_identifier": device["deviceTypeIdentifier"],
            },
            "test_selector": args.test_selector,
            "app_bundle_id": args.app_bundle_id,
            "artifacts": {"screenshot": args.screenshot, "raw_probe": args.raw_probe},
            "evaluator_dependency_setup": create_dependency_setup(args),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ready", "output": str(args.output), "runtime": runtime}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
