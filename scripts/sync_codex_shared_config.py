#!/usr/bin/env python3
"""
Render a local Codex config by overlaying repo-managed shared defaults onto an
existing ~/.codex/config.toml while preserving unmanaged local sections.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, time
import json
from pathlib import Path
import re
import sys
import tomllib
from typing import Any

ROOT_SCALAR_PRIORITY = [
    "model",
    "model_reasoning_effort",
    "plan_mode_reasoning_effort",
    "service_tier",
    "model_instructions_file",
]
ROOT_TABLE_PRIORITY = [
    "features",
    "projects",
    "mcp_servers",
    "notice",
    "tui",
    "plugins",
    "marketplaces",
]
DOTTED_ROOT_TABLES = {"memories"}
REPLACE_NAMED_CHILDREN_TABLES = {"mcp_servers", "plugins"}
BARE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shared-config", required=True)
    parser.add_argument("--existing-config")
    parser.add_argument("--agents-path", required=True)
    return parser.parse_args()


def load_toml(path_text: str | None) -> dict[str, Any]:
    if not path_text:
        return {}

    path = Path(path_text)
    if not path.exists():
        return {}

    content = path.read_text()
    if not content.strip():
        return {}

    data = tomllib.loads(content)
    if not isinstance(data, dict):
        raise TypeError(f"Unexpected TOML root type for {path}: {type(data).__name__}")
    return data


def deep_overlay(existing: Any, shared: Any) -> Any:
    if isinstance(existing, dict) and isinstance(shared, dict):
        merged = deepcopy(existing)
        for key, value in shared.items():
            merged[key] = deep_overlay(merged.get(key), value)
        return merged
    return deepcopy(shared)


def merge_shared_config(
    existing: dict[str, Any],
    shared: dict[str, Any],
    agents_path: str,
) -> dict[str, Any]:
    merged = deepcopy(existing)

    for key, value in shared.items():
        if key in REPLACE_NAMED_CHILDREN_TABLES and isinstance(value, dict):
            current = deepcopy(merged.get(key)) if isinstance(merged.get(key), dict) else {}
            for child_key, child_value in value.items():
                current[child_key] = deepcopy(child_value)
            merged[key] = current
            continue

        merged[key] = deep_overlay(merged.get(key), value)

    merged["model_instructions_file"] = agents_path
    return merged


def format_key_segment(key: str) -> str:
    return key if BARE_KEY_PATTERN.match(key) else json.dumps(key)


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(format_value(item) for item in value) + "]"
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    raise TypeError(f"Unsupported TOML value type: {type(value).__name__}")


def ordered_root_scalar_items(data: dict[str, Any]) -> list[tuple[str, Any]]:
    scalar_items = [(key, value) for key, value in data.items() if not isinstance(value, dict)]
    order = {key: index for index, key in enumerate(ROOT_SCALAR_PRIORITY)}
    return sorted(
        scalar_items,
        key=lambda item: (0, order[item[0]]) if item[0] in order else (1, list(data).index(item[0])),
    )


def ordered_root_table_items(data: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    table_items = [
        (key, value)
        for key, value in data.items()
        if isinstance(value, dict) and key not in DOTTED_ROOT_TABLES
    ]
    order = {key: index for index, key in enumerate(ROOT_TABLE_PRIORITY)}
    return sorted(
        table_items,
        key=lambda item: (0, order[item[0]]) if item[0] in order else (1, list(data).index(item[0])),
    )


def emit_dotted_assignments(path: list[str], mapping: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key, value in mapping.items():
        next_path = path + [key]
        if isinstance(value, dict):
            lines.extend(emit_dotted_assignments(next_path, value))
            continue
        dotted_key = ".".join(format_key_segment(segment) for segment in next_path)
        lines.append(f"{dotted_key} = {format_value(value)}")
    return lines


def table_header(path: list[str]) -> str:
    return "[" + ".".join(format_key_segment(segment) for segment in path) + "]"


def emit_table(path: list[str], mapping: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    scalar_items = [(key, value) for key, value in mapping.items() if not isinstance(value, dict)]
    child_items = [(key, value) for key, value in mapping.items() if isinstance(value, dict)]

    if path and scalar_items:
        lines.append(table_header(path))
        for key, value in scalar_items:
            lines.append(f"{format_key_segment(key)} = {format_value(value)}")
        lines.append("")

    for child_key, child_value in child_items:
        child_lines = emit_table(path + [child_key], child_value)
        if child_lines:
            if lines and lines[-1] != "":
                lines.append("")
            lines.extend(child_lines)

    return lines


def dumps_toml(data: dict[str, Any]) -> str:
    lines: list[str] = []

    for key, value in ordered_root_scalar_items(data):
        lines.append(f"{format_key_segment(key)} = {format_value(value)}")

    memories = data.get("memories")
    if isinstance(memories, dict):
        dotted_lines = emit_dotted_assignments(["memories"], memories)
        if dotted_lines:
            if lines:
                lines.append("")
            lines.extend(dotted_lines)

    root_tables = ordered_root_table_items(data)
    if root_tables:
        if lines:
            lines.append("")
        for index, (key, value) in enumerate(root_tables):
            if index > 0 and lines and lines[-1] != "":
                lines.append("")
            lines.extend(emit_table([key], value))

    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    shared = load_toml(args.shared_config)
    existing = load_toml(args.existing_config)
    merged = merge_shared_config(existing=existing, shared=shared, agents_path=args.agents_path)
    sys.stdout.write(dumps_toml(merged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
