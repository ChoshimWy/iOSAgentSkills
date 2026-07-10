#!/usr/bin/env python3
"""
Render a local Codex config by overlaying repo-managed shared defaults onto an
existing ~/.codex/config.toml while preserving unmanaged local sections and
machine/task-specific model, reasoning, verbosity, and service-tier choices.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, datetime, time
import json
from pathlib import Path
import re
import sys
from typing import Any

try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # Python 3.10 fallback
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        try:
            import pip._vendor.tomli as tomllib  # type: ignore[no-redef]
        except ModuleNotFoundError as exc:
            raise SystemExit(
                "sync_codex_shared_config.py requires Python 3.11+, `tomli`, or pip's vendored tomli"
            ) from exc

ROOT_SCALAR_PRIORITY = [
    "model",
    "image_model",
    "model_reasoning_effort",
    "plan_mode_reasoning_effort",
    "service_tier",
    "model_instructions_file",
]
ROOT_TABLE_PRIORITY = [
    "features",
    "agents",
    "projects",
    "mcp_servers",
    "notice",
    "tui",
    "plugins",
    "marketplaces",
]
DOTTED_ROOT_TABLES = {"memories"}
REPLACE_NAMED_CHILDREN_TABLES = {"mcp_servers", "plugins"}
LOCAL_RUNTIME_KEYS = {
    "model",
    "model_reasoning_effort",
    "plan_mode_reasoning_effort",
    "model_verbosity",
    "service_tier",
}
RETIRED_SHARED_MCP_SERVERS = {
    "codegraph": {
        "command": "codegraph",
        "args": ["serve", "--mcp"],
    },
    "openaiDeveloperDocs": {
        "url": "https://developers.openai.com/mcp",
        "tools": {"search_openai_docs": {"approval_mode": "approve"}},
    },
    "appleDeveloperDocs": {
        "command": "npx",
        "args": ["-y", "@kimsungwhee/apple-docs-mcp@latest"],
    },
}
BARE_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def disable_plugin_entry(plugin_config: Any) -> dict[str, Any]:
    """Return a plugin config copy with the plugin disabled.

    The repo-managed shared config runs Codex in local-only skills mode. Account
    or marketplace sync may leave extra plugin entries in ~/.codex/config.toml;
    preserving those entries but forcing enabled=false keeps the local config
    reversible without letting plugin-contributed skills/tools load.
    """
    if isinstance(plugin_config, dict):
        disabled = deepcopy(plugin_config)
    else:
        disabled = {}
    disabled["enabled"] = False
    return disabled


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

    # Retire the previous repository baseline that set service_tier="fast"
    # without the matching fast_mode feature. Preserve an explicit local Fast
    # choice only when the user enabled both fields intentionally.
    features = merged.get("features")
    explicit_fast_mode = isinstance(features, dict) and features.get("fast_mode") is True
    if merged.get("service_tier") == "fast" and not explicit_fast_mode:
        merged.pop("service_tier", None)

    # These servers used to be injected globally by codex.shared.toml. They now
    # live on explorer/reviewer/docs_researcher custom agents, so remove only
    # the legacy repo-managed global copies while preserving unrelated local MCPs.
    existing_mcp = merged.get("mcp_servers")
    if isinstance(existing_mcp, dict):
        for server_name, retired_config in RETIRED_SHARED_MCP_SERVERS.items():
            if existing_mcp.get(server_name) == retired_config:
                existing_mcp.pop(server_name, None)
        if not existing_mcp:
            merged.pop("mcp_servers", None)

    for key, value in shared.items():
        if key in LOCAL_RUNTIME_KEYS and key in merged:
            # Runtime/account availability changes faster than this repository.
            # Never downgrade an explicit local choice during reinstall.
            continue

        if key == "plugins" and isinstance(value, dict):
            current: dict[str, Any] = {}
            existing_plugins = merged.get(key)
            if isinstance(existing_plugins, dict):
                for child_key, child_value in existing_plugins.items():
                    current[child_key] = disable_plugin_entry(child_value)
            for child_key, child_value in value.items():
                current[child_key] = deepcopy(child_value)
            merged[key] = current
            continue

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


def is_array_of_tables(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, dict) for item in value)


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


def array_table_header(path: list[str]) -> str:
    return "[[" + ".".join(format_key_segment(segment) for segment in path) + "]]"


def emit_table(path: list[str], mapping: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    scalar_items = [
        (key, value)
        for key, value in mapping.items()
        if not isinstance(value, dict) and not is_array_of_tables(value)
    ]
    child_items = [(key, value) for key, value in mapping.items() if isinstance(value, dict)]
    array_table_items = [(key, value) for key, value in mapping.items() if is_array_of_tables(value)]

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

    for child_key, entries in array_table_items:
        for entry in entries:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(array_table_header(path + [child_key]))
            for key, value in entry.items():
                if isinstance(value, dict) or is_array_of_tables(value):
                    raise TypeError(
                        "Nested tables inside arrays of tables are not supported "
                        f"at {'.'.join(path + [child_key, key])}"
                    )
                lines.append(f"{format_key_segment(key)} = {format_value(value)}")
            lines.append("")

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
