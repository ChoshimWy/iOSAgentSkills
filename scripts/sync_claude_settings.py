#!/usr/bin/env python3
"""
Merge Claude Code settings template with existing user settings.

- Preserves user-added permissions, MCP servers, and hooks
- Template values win for core managed keys
- Union strategy for allow/deny lists (deduplicate)
"""
import argparse
import json
import sys
from pathlib import Path


def deep_merge(existing, template):
    """Merge two settings dicts. Template values win for managed keys; lists are unioned."""
    if not isinstance(existing, dict) or not isinstance(template, dict):
        return template

    result = {}
    all_keys = set(existing.keys()) | set(template.keys())

    for key in all_keys:
        if key not in template:
            result[key] = existing[key]
        elif key not in existing:
            result[key] = template[key]
        else:
            if key in ("allow", "deny") and isinstance(existing[key], list) and isinstance(template[key], list):
                result[key] = sorted(set(existing[key] + template[key]))
            elif isinstance(existing[key], dict) and isinstance(template[key], dict):
                result[key] = deep_merge(existing[key], template[key])
            else:
                result[key] = template[key]

    return result


def main():
    parser = argparse.ArgumentParser(description="Merge Claude Code settings template")
    parser.add_argument("--template", required=True, help="Path to settings template JSON")
    parser.add_argument("--target", required=True, help="Path to ~/.claude/settings.json")
    args = parser.parse_args()

    template_path = Path(args.template)
    if not template_path.exists():
        print(f"Error: template not found: {args.template}", file=sys.stderr)
        return 1

    template = json.loads(template_path.read_text())
    target_path = Path(args.target)

    if target_path.exists() and target_path.stat().st_size > 0:
        existing = json.loads(target_path.read_text())
    else:
        existing = {}

    merged = deep_merge(existing, template)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
