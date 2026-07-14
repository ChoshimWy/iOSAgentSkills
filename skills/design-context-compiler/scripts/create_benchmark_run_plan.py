#!/usr/bin/env python3
"""Freeze one machine-specific measured Codex benchmark Run Plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from codex_benchmark_executor import ExecutorError, _cli_identity
from validate_contract import load_json, validate


ROOT = Path(__file__).resolve().parents[1]
EXECUTOR = ROOT / "scripts" / "codex_benchmark_executor.py"
VALIDATOR = ROOT / "scripts" / "ios_semantic_visual_validator.py"


class PlanError(ValueError):
    """A trustworthy measured Run Plan cannot be frozen."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence(path: Path, output_parent: Path) -> dict[str, str]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise PlanError(f"evidence file is missing: {resolved}")
    try:
        path_value = resolved.relative_to(output_parent.resolve()).as_posix()
    except ValueError:
        path_value = str(resolved)
    return {"path": path_value, "sha256": sha256(resolved)}


def git_root(path: Path) -> Path:
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path if path.is_dir() else path.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PlanError(f"path is not inside a reviewed Git repository: {path}")
    return Path(result.stdout.strip()).resolve()


def create_plan(
    case_path: Path,
    capture_adapter: Path,
    codex_launcher: Path,
    model: str,
    reasoning: str,
    output: Path,
    capture_overlay: Path | None = None,
    capture_runtime: Path | None = None,
) -> dict:
    output = output.resolve()
    if output.exists():
        raise PlanError(f"refusing to overwrite existing Run Plan: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    paths = [case_path.resolve(), capture_adapter.resolve(), EXECUTOR.resolve(), VALIDATOR.resolve(), output.parent]
    if capture_overlay is not None:
        paths.append(capture_overlay.resolve())
    runtime = load_json(capture_runtime) if capture_runtime is not None else {"mode": "none"}
    dependency_setup = runtime.get("evaluator_dependency_setup", {"mode": "none"}) if isinstance(runtime, dict) else {"mode": "none"}
    if runtime.get("mode") == "ios-simulator" and dependency_setup.get("mode") != "none":
        generator = dependency_setup.get("generator", {})
        generator_path = generator.get("path") if isinstance(generator, dict) else None
        if not isinstance(generator_path, str):
            raise PlanError("evaluator dependency setup generator path is missing")
        resolved_generator = Path(generator_path).resolve()
        if not resolved_generator.is_file() or sha256(resolved_generator) != generator.get("sha256"):
            raise PlanError("evaluator dependency setup generator identity mismatch")
        paths.append(resolved_generator)
    roots = {git_root(path) for path in paths}
    if len(roots) != 1:
        raise PlanError("case, capture adapter, executor, validator and output must belong to one reviewed Git repository")
    case = load_json(case_path)
    _, diagnostics, blocking = validate(case, "benchmark-case")
    if diagnostics or blocking:
        raise PlanError(f"benchmark case is not ready: {[item.as_dict() for item in diagnostics]} {blocking}")
    version, launcher_path, native_path, launcher_hash, native_hash, package_hash = _cli_identity(
        codex_launcher.resolve(),
        output.parent,
    )
    plan = {
        "run_plan_version": "1.2.0",
        "plan_id": f"{case['case_id']}.codex-measured",
        "evidence_status": "measured",
        "case": evidence(case_path, output.parent),
        "executor": {
            "model": model,
            "reasoning": reasoning,
            "synthetic": False,
            "provider_cli": {
                "name": "openai-codex-cli",
                "version": version,
                "launcher_path": launcher_path,
                "native_path": native_path,
                "launcher_sha256": launcher_hash,
                "native_sha256": native_hash,
                "package_json_sha256": package_hash,
            },
            "adapter": evidence(EXECUTOR, output.parent),
            "implementation_command": ["{adapter}"],
            "timeout_seconds": 1800,
            "environment": {},
        },
        "validator": {
            "id": "ios-semantic-visual-validator-v1",
            "synthetic": False,
            "capture_adapter": evidence(capture_adapter, output.parent),
            "capture_overlay": (
                {"mode": "git-patch", "artifact": evidence(capture_overlay, output.parent)}
                if capture_overlay is not None
                else {"mode": "none"}
            ),
            "capture_runtime": runtime,
            "capture_command": ["{capture}"],
            "adapter": evidence(VALIDATOR, output.parent),
            "command": ["{validator}"],
            "timeout_seconds": 1800,
            "environment": {},
        },
        "isolation": {
            "strategy": "git-pinned-tree-slice",
            "run_order": ["screenshot-only", "ui-ir", "ui-ir-with-binding"],
            "clean_checkout": True,
        },
    }
    _, plan_diagnostics, plan_blocking = validate(plan, "benchmark-run-plan")
    if plan_diagnostics or plan_blocking:
        raise PlanError(f"generated Run Plan is invalid: {[item.as_dict() for item in plan_diagnostics]} {plan_blocking}")
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--capture-adapter", type=Path, required=True)
    parser.add_argument("--capture-overlay", type=Path, help="optional evaluator-only git patch applied after implementation and removed after capture")
    parser.add_argument("--capture-runtime", type=Path, help="optional inline ios-simulator capture runtime JSON")
    parser.add_argument("--codex-launcher", type=Path, required=True, help="absolute @openai/codex bin/codex.js path")
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning", choices=["low", "medium", "high", "xhigh"], default="high")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        plan = create_plan(
            args.case,
            args.capture_adapter,
            args.codex_launcher,
            args.model,
            args.reasoning,
            args.output,
            args.capture_overlay,
            args.capture_runtime,
        )
    except (ExecutorError, OSError, PlanError, ValueError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"status": "ready", "plan": str(args.output), "plan_id": plan["plan_id"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
