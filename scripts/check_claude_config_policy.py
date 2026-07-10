#!/usr/bin/env python3
"""Validate the repository-managed Claude Code safety and merge contract."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "config" / "claude-code" / "settings.json"
SYNC = ROOT / "scripts" / "sync_claude_settings.py"
AGENTS = ROOT / "config" / "claude-code" / "agents"
LEGACY_APPLE_DOCS = {
    "command": "npx",
    "args": ["-y", "@kimsungwhee/apple-docs-mcp@latest"],
}


def fail_if(condition: bool, message: str, failures: list[str]) -> None:
    if condition:
        failures.append(message)


def run_sync(existing: dict) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "settings.json"
        target.write_text(json.dumps(existing))
        result = subprocess.run(
            ["python3", str(SYNC), "--template", str(SETTINGS), "--target", str(target)],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return json.loads(target.read_text())


def main() -> int:
    failures: list[str] = []
    try:
        settings = json.loads(SETTINGS.read_text())
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL: invalid Claude settings template: {error}")
        return 1

    for settings_path in sorted(SETTINGS.parent.glob("settings*.json")):
        try:
            candidate = json.loads(settings_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            failures.append(f"invalid Claude settings file {settings_path.relative_to(ROOT)}: {error}")
            continue
        allow = candidate.get("permissions", {}).get("allow", [])
        fail_if(
            "Bash(xcodebuild:*)" in allow,
            f"{settings_path.relative_to(ROOT)} must not allow bare Bash(xcodebuild:*)",
            failures,
        )
    servers = settings.get("mcpServers", {})
    fail_if("codegraph" not in servers, "settings missing codegraph MCP", failures)
    expected_apple = {"command": "npx", "args": ["-y", "@kimsungwhee/apple-docs-mcp@1.0.26"]}
    fail_if(servers.get("appleDeveloperDocs") != expected_apple, "appleDeveloperDocs must use the pinned managed baseline", failures)

    docs_researcher = AGENTS / "docs_researcher.md"
    orchestration = AGENTS / "orchestration.md"
    readme = AGENTS / "README.md"
    for path, snippets in {
        docs_researcher: ["appleDeveloperDocs", "OpenAI 官方域名", "checkpoint_status", "不修改代码"],
        orchestration: ["默认直接输出 CP0 最小计划", "不依赖 `EnterPlanMode`", "docs_researcher.md"],
        readme: ["docs_researcher.md", "不复制 Codex 的 Profile、Fast mode 或模型名"],
    }.items():
        text = path.read_text() if path.exists() else ""
        for snippet in snippets:
            fail_if(snippet not in text, f"{path.relative_to(ROOT)} missing: {snippet}", failures)

    try:
        migrated = run_sync(
            {
                "permissions": {"allow": ["Bash(xcodebuild:*)", "Bash(custom:*)"]},
                "mcpServers": {
                    "codegraph": {"command": "custom-codegraph"},
                    "appleDeveloperDocs": LEGACY_APPLE_DOCS,
                    "private": {"command": "private-mcp"},
                },
            }
        )
        migrated_servers = migrated["mcpServers"]
        fail_if("Bash(xcodebuild:*)" in migrated["permissions"]["allow"], "sync must remove retired bare xcodebuild permission", failures)
        fail_if("Bash(custom:*)" not in migrated["permissions"]["allow"], "sync must preserve user permissions", failures)
        fail_if(migrated_servers.get("codegraph") != {"command": "custom-codegraph"}, "sync must preserve custom same-name codegraph MCP", failures)
        fail_if(migrated_servers.get("appleDeveloperDocs") != expected_apple, "sync must migrate exact legacy apple MCP", failures)
        fail_if(migrated_servers.get("private") != {"command": "private-mcp"}, "sync must preserve user MCPs", failures)

        custom_apple = {"command": "npx", "args": ["-y", "@kimsungwhee/apple-docs-mcp@9.9.9"]}
        preserved = run_sync({"mcpServers": {"appleDeveloperDocs": custom_apple}})
        fail_if(preserved["mcpServers"].get("appleDeveloperDocs") != custom_apple, "sync must preserve custom same-name apple MCP", failures)
    except (KeyError, RuntimeError, OSError, json.JSONDecodeError) as error:
        failures.append(f"sync regression check failed: {error}")

    if failures:
        print("FAIL")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print("PASS: Claude settings and agent policy are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
