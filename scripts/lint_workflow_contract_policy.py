#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = ROOT / "skills" / "codex-subagent-orchestration"
CODEX_TEMPLATE_AGENTS = ROOT / "config" / "codex.templates" / "agents"
CODEX_AGENT_VALIDATE_SCRIPT = ROOT / "scripts" / "validate_codex_agent_templates.py"


def require_contains(path: Path, snippets: list[str], failures: list[str]) -> None:
    text = path.read_text()
    missing = [snippet for snippet in snippets if snippet not in text]
    if missing:
        failures.append(f"{path.relative_to(ROOT)} missing: {', '.join(missing)}")


def require_exists(path: Path, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"{path.relative_to(ROOT)} missing")


def require_not_exists(path: Path, failures: list[str]) -> None:
    if path.exists():
        failures.append(f"{path.relative_to(ROOT)} should not exist")


def main() -> int:
    failures: list[str] = []

    require_contains(
        ROOT / "AGENTS.md",
        [
            "任务分型器归类",
            "`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`",
            "`explorer + builder + reporter`",
        ],
        failures,
    )

    require_contains(
        ROOT / "README.md",
        [
            "任务分型：`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`",
            "`explorer + builder + reporter`",
            "python3 scripts/lint_workflow_contract_policy.py",
            "python3 scripts/validate_codex_agent_templates.py",
            "config/codex.templates/agents/",
            "~/.codex/agents/",
        ],
        failures,
    )

    require_contains(
        ROOT / "install-local-agent-config.sh",
        [
            "~/.codex/agents/*.toml",
            "config/codex.templates/agents/*.toml",
            "sync_codex_agent_templates",
            "verify_codex_agent_templates",
            "validate_codex_agent_templates.py",
        ],
        failures,
    )

    require_contains(
        SKILL_ROOT / "SKILL.md",
        [
            "## 任务分型器（新增默认规则）",
            "`doc-only`",
            "`rule-only`",
            "`code-small`",
            "`code-medium`",
            "`code-risky`",
            "## 角色激活矩阵（新增默认规则）",
            "默认最小集合为：`explorer + builder + reporter`",
            "同一类问题默认最多回环 2 次",
            "`failure_attribution_type`",
            "`acceptance_matrix`",
        ],
        failures,
    )

    require_contains(
        SKILL_ROOT / "references" / "role-contracts.md",
        [
            "`change_intent`",
            "`rollback_hint`",
            "`failure_attribution_type`",
            "`acceptance_matrix`",
            "`checkpoint_status`",
            "`first_failure`",
            "`next_action`",
        ],
        failures,
    )

    require_contains(
        SKILL_ROOT / "references" / "prompt-templates.md",
        [
            "`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`",
            "`failure_attribution_type`",
            "## reporter",
            "acceptance_matrix",
            "next_action 不能是 complete",
        ],
        failures,
    )

    require_contains(
        SKILL_ROOT / "references" / "handoff-loop.md",
        [
            "任务分型器判定",
            "`CP1` 未通过前禁止无必要并行扩散",
            "next_action` 只能是 `blocked`",
        ],
        failures,
    )

    for agent_file in (
        CODEX_TEMPLATE_AGENTS / "pm.toml",
        CODEX_TEMPLATE_AGENTS / "explorer.toml",
        CODEX_TEMPLATE_AGENTS / "builder.toml",
        CODEX_TEMPLATE_AGENTS / "tester.toml",
        CODEX_TEMPLATE_AGENTS / "reporter.toml",
    ):
        require_exists(agent_file, failures)

    require_contains(
        CODEX_TEMPLATE_AGENTS / "pm.toml",
        [
            '"checkpoint_status"',
            '"first_failure"',
            '"next_action"',
        ],
        failures,
    )

    require_contains(
        CODEX_TEMPLATE_AGENTS / "explorer.toml",
        [
            '"checkpoint_status"',
            '"first_failure"',
            '"next_action"',
        ],
        failures,
    )

    require_contains(
        CODEX_TEMPLATE_AGENTS / "builder.toml",
        [
            '"change_intent"',
            '"rollback_hint"',
            '"checkpoint_status"',
            '"first_failure"',
            '"next_action"',
        ],
        failures,
    )

    require_contains(
        CODEX_TEMPLATE_AGENTS / "tester.toml",
        [
            '"failure_attribution_type"',
            '"checkpoint_status"',
            '"first_failure"',
            '"next_action"',
            "code_bug/test_bug/env_issue/unknown",
        ],
        failures,
    )

    require_contains(
        CODEX_TEMPLATE_AGENTS / "reporter.toml",
        [
            '"acceptance_matrix"',
            '"checkpoint_status"',
            '"first_failure"',
            '"next_action"',
        ],
        failures,
    )

    require_contains(
        CODEX_TEMPLATE_AGENTS / "README.md",
        [
            "任务分型",
            "默认最小角色集合：`explorer + builder + reporter`",
            "统一字段",
        ],
        failures,
    )

    require_exists(CODEX_AGENT_VALIDATE_SCRIPT, failures)

    require_not_exists(ROOT / ".codex", failures)

    if failures:
        print("workflow contract policy lint failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("workflow contract policy lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
