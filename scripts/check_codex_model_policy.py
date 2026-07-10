#!/usr/bin/env python3
"""Validate repository Codex model/profile policy against the current catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        import pip._vendor.tomli as tomllib  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parent.parent
SHARED_CONFIG = ROOT / "config" / "codex" / "codex.shared.toml"
AGENT_DIR = ROOT / "config" / "codex" / "templates" / "agents"
PROFILE_DIR = ROOT / "config" / "codex" / "templates" / "profiles"
REQUIRED_PROFILES = {
    "daily",
    "budget",
    "readonly",
    "deep",
    "extreme",
    "interactive-fast",
}
REQUIRED_AGENTS = {
    "builder",
    "docs_researcher",
    "explorer",
    "pm",
    "reporter",
    "reviewer",
    "tester",
}
TASK_SPECIFIC_ROOT_KEYS = {
    "model",
    "model_reasoning_effort",
    "plan_mode_reasoning_effort",
    "model_verbosity",
    "service_tier",
}
VALID_REASONING = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
VALID_VERBOSITY = {"low", "medium", "high"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Validate repository policy without invoking `codex debug models`.",
    )
    parser.add_argument(
        "--catalog-json",
        help="Read a previously captured `codex debug models` JSON file.",
    )
    parser.add_argument(
        "--local-config",
        help="Also diagnose a local config.toml for stale profiles or unresolved MCP commands.",
    )
    return parser.parse_args()


def load_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text())


def load_catalog(path: str | None) -> dict[str, dict]:
    if path:
        payload = json.loads(Path(path).read_text())
    else:
        result = subprocess.run(
            ["codex", "debug", "models"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or "unknown error"
            raise RuntimeError(f"`codex debug models` failed: {detail}")
        payload = json.loads(result.stdout)

    models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(models, list):
        raise RuntimeError("model catalog must contain a models array")
    return {
        item["slug"]: item
        for item in models
        if isinstance(item, dict) and isinstance(item.get("slug"), str)
    }


def configured_entries() -> list[tuple[str, Path, dict]]:
    entries: list[tuple[str, Path, dict]] = []
    for path in sorted(AGENT_DIR.glob("*.toml")):
        entries.append((f"agent:{path.stem}", path, load_toml(path)))
    for path in sorted(PROFILE_DIR.glob("*.config.toml")):
        name = path.name.removesuffix(".config.toml")
        entries.append((f"profile:{name}", path, load_toml(path)))
    return entries


def validate_static(failures: list[str]) -> list[tuple[str, Path, dict]]:
    shared = load_toml(SHARED_CONFIG)
    forbidden = sorted(TASK_SPECIFIC_ROOT_KEYS.intersection(shared))
    if forbidden:
        failures.append(
            "shared baseline must not override task-specific runtime keys: " + ", ".join(forbidden)
        )

    profile_names = {
        path.name.removesuffix(".config.toml")
        for path in PROFILE_DIR.glob("*.config.toml")
    }
    missing_profiles = sorted(REQUIRED_PROFILES - profile_names)
    if missing_profiles:
        failures.append("missing profile templates: " + ", ".join(missing_profiles))

    agent_names = {path.stem for path in AGENT_DIR.glob("*.toml")}
    missing_agents = sorted(REQUIRED_AGENTS - agent_names)
    if missing_agents:
        failures.append("missing custom agents: " + ", ".join(missing_agents))

    entries = configured_entries()
    by_name = {name: data for name, _, data in entries}
    reviewer = by_name.get("agent:reviewer")
    if not reviewer:
        failures.append("missing reviewer custom agent")
    else:
        if reviewer.get("sandbox_mode") != "read-only":
            failures.append("reviewer must use sandbox_mode=read-only")
        if reviewer.get("model_reasoning_effort") != "high":
            failures.append("reviewer must use model_reasoning_effort=high")
        if reviewer.get("model") != "gpt-5.4":
            failures.append("reviewer must use the current stable quality-gate model gpt-5.4")
        if "spark" in str(reviewer.get("model", "")).lower():
            failures.append("reviewer must not use Spark as the mandatory quality gate")

    for name, path, data in entries:
        model = data.get("model")
        effort = data.get("model_reasoning_effort")
        verbosity = data.get("model_verbosity")
        if not isinstance(model, str) or not model.strip():
            failures.append(f"{name} must declare a model ({path.relative_to(ROOT)})")
        if effort is not None and effort not in VALID_REASONING:
            failures.append(f"{name} has unsupported reasoning value: {effort}")
        if verbosity is not None and verbosity not in VALID_VERBOSITY:
            failures.append(f"{name} has unsupported verbosity value: {verbosity}")
        if data.get("service_tier") == "fast" and name != "profile:interactive-fast":
            failures.append(f"Fast mode is only allowed in profile:interactive-fast, found in {name}")
        if data.get("features", {}).get("fast_mode") is True and name != "profile:interactive-fast":
            failures.append(f"features.fast_mode is only allowed in profile:interactive-fast, found in {name}")

    docs_agent = by_name.get("agent:docs_researcher", {})
    docs_servers = docs_agent.get("mcp_servers", {})
    for server_name in ("openaiDeveloperDocs", "appleDeveloperDocs"):
        if server_name not in docs_servers:
            failures.append(f"docs_researcher missing scoped MCP server: {server_name}")
    apple_args = (
        docs_servers
        .get("appleDeveloperDocs", {})
        .get("args", [])
    )
    if not apple_args or any("@latest" in str(item) for item in apple_args):
        failures.append("docs_researcher must pin apple-docs-mcp to an explicit version")

    for role in ("agent:explorer", "agent:reviewer"):
        servers = by_name.get(role, {}).get("mcp_servers", {})
        if "codegraph" not in servers:
            failures.append(f"{role} must own the scoped codegraph MCP")

    readonly_profile = by_name.get("profile:readonly", {})
    if readonly_profile.get("sandbox_mode") != "read-only":
        failures.append("readonly profile must use sandbox_mode=read-only")
    fast_profile = by_name.get("profile:interactive-fast", {})
    if fast_profile.get("service_tier") != "fast":
        failures.append("interactive-fast profile must set service_tier=fast")
    if fast_profile.get("features", {}).get("fast_mode") is not True:
        failures.append("interactive-fast profile must enable features.fast_mode")

    return entries


def validate_catalog(
    catalog: dict[str, dict],
    entries: list[tuple[str, Path, dict]],
    failures: list[str],
) -> None:
    for name, _, data in entries:
        model = data.get("model")
        if not isinstance(model, str):
            continue
        item = catalog.get(model)
        if item is None:
            failures.append(f"{name} model is unavailable in current catalog: {model}")
            continue
        effort = data.get("model_reasoning_effort")
        levels = item.get("supported_reasoning_levels")
        if effort and isinstance(levels, list):
            supported = {
                level.get("effort")
                for level in levels
                if isinstance(level, dict)
            }
            if effort not in supported:
                failures.append(f"{name} model {model} does not support reasoning={effort}")


def validate_local_config(path: Path, failures: list[str], warnings: list[str]) -> None:
    data = load_toml(path)
    if data.get("profiles"):
        warnings.append(
            "local config contains embedded [profiles]; current documented CLI path is "
            "~/.codex/<name>.config.toml selected with --profile"
        )
    for name, config in data.get("mcp_servers", {}).items():
        if not isinstance(config, dict):
            continue
        command = config.get("command")
        if not isinstance(command, str) or not command:
            continue
        resolved = Path(command).exists() if Path(command).is_absolute() else shutil.which(command) is not None
        if not resolved:
            failures.append(f"local MCP command is not resolvable: {name} -> {command}")


def main() -> int:
    args = parse_args()
    failures: list[str] = []
    warnings: list[str] = []
    entries = validate_static(failures)

    if not args.offline:
        try:
            validate_catalog(load_catalog(args.catalog_json), entries, failures)
        except Exception as exc:
            failures.append(str(exc))

    if args.local_config:
        validate_local_config(Path(args.local_config).expanduser(), failures, warnings)

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if failures:
        print("Codex model policy check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    mode = "offline" if args.offline else "runtime catalog"
    print(f"Codex model policy check passed ({len(entries)} entries, {mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
