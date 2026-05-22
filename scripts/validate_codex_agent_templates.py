#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        import pip._vendor.tomli as tomllib  # type: ignore


REQUIRED_STRING_FIELDS = ("name", "description", "developer_instructions")
OPTIONAL_STRING_FIELDS = ("model", "model_reasoning_effort", "sandbox_mode", "default_permissions")
OPTIONAL_STRING_LIST_FIELDS = ("nickname_candidates",)
OPTIONAL_TABLE_FIELDS = ("mcp_servers", "skills")
FORBIDDEN_FIELDS = ("role", "permissions", "output_contract")


def iter_agent_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(sorted(path.glob("*.toml")))
        elif path.suffix == ".toml":
            files.append(path)
        else:
            raise SystemExit(f"unsupported path: {path}")
    return files


def validate_agent_file(path: Path) -> list[str]:
    failures: list[str] = []

    try:
        payload = tomllib.loads(path.read_text())
    except Exception as exc:  # pragma: no cover - defensive parse guard
        return [f"{path}: invalid toml: {exc}"]

    if not isinstance(payload, dict):
        return [f"{path}: root must be a TOML table"]

    for key in REQUIRED_STRING_FIELDS:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{path}: {key} must be a non-empty string")

    for key in OPTIONAL_STRING_FIELDS:
        if key in payload and not isinstance(payload[key], str):
            failures.append(f"{path}: {key} must be a string when present")

    for key in OPTIONAL_STRING_LIST_FIELDS:
        if key not in payload:
            continue
        value = payload[key]
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            failures.append(f"{path}: {key} must be a non-empty string list when present")
        elif len(set(value)) != len(value):
            failures.append(f"{path}: {key} must not contain duplicate entries")

    for key in OPTIONAL_TABLE_FIELDS:
        if key in payload and not isinstance(payload[key], dict):
            failures.append(f"{path}: {key} must be a table when present")

    for key in FORBIDDEN_FIELDS:
        if key in payload:
            failures.append(f"{path}: unsupported legacy field {key}")

    return failures


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python3 scripts/validate_codex_agent_templates.py <dir-or-file> [...]", file=sys.stderr)
        return 2

    agent_files = iter_agent_files(sys.argv[1:])
    if not agent_files:
        print("no agent toml files found", file=sys.stderr)
        return 1

    failures: list[str] = []
    for agent_file in agent_files:
        failures.extend(validate_agent_file(agent_file))

    if failures:
        print("codex agent template validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"codex agent template validation passed ({len(agent_files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
