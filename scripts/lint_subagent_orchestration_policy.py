#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = ROOT / "skills" / "codex-subagent-orchestration"


FORBIDDEN_AUTO_SUBAGENT_PHRASES = [
    "仓库级显式触发",
    "自动使用 subAgent",
    "自动启动",
    "按档位自动",
    "默认启用 subAgent 工作流",
]


def require_contains(path: Path, snippets: list[str], failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"{path.relative_to(ROOT)} missing")
        return
    text = path.read_text()
    missing = [snippet for snippet in snippets if snippet not in text]
    if missing:
        failures.append(f"{path.relative_to(ROOT)} missing: {', '.join(missing)}")


def require_not_contains(path: Path, snippets: list[str], failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"{path.relative_to(ROOT)} missing")
        return
    text = path.read_text()
    present = [snippet for snippet in snippets if snippet in text]
    if present:
        failures.append(f"{path.relative_to(ROOT)} should not contain: {', '.join(present)}")


def require_exists(path: Path, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"{path.relative_to(ROOT)} missing")


def require_yaml_parse(path: Path, failures: list[str]) -> None:
    result = subprocess.run(
        ["ruby", "-e", "require 'yaml'; YAML.load_file(ARGV[0])", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown yaml parse error"
        failures.append(f"{path.relative_to(ROOT)} invalid yaml: {stderr}")


def main() -> int:
    failures: list[str] = []

    policy_paths = [
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / "skills" / "TAXONOMY.md",
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "agents" / "openai.yaml",
        SKILL_ROOT / "references" / "coding-standards.md",
        SKILL_ROOT / "references" / "handoff-loop.md",
        SKILL_ROOT / "references" / "model-selection.md",
        SKILL_ROOT / "references" / "prompt-templates.md",
        SKILL_ROOT / "references" / "role-contracts.md",
        ROOT / "config" / "codex" / "templates" / "agents" / "README.md",
    ]
    for path in policy_paths:
        require_not_contains(path, FORBIDDEN_AUTO_SUBAGENT_PHRASES, failures)

    require_contains(
        ROOT / "AGENTS.md",
        [
            "使用任何 Skill 前，必须先输出 `>>> Skill: <skill-name>`",
            "iOS 开发任务默认先进入 `codex-subagent-orchestration`",
            "`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`",
            "默认进入编排入口不等于默认实际 spawn subAgent",
            "只有用户显式要求 subAgent / parallel agent / delegation",
            "`explorer + builder + reporter`",
            "定向验证 + `code-review`",
            "最窄定向验证",
        ],
        failures,
    )
    require_contains(
        ROOT / "README.md",
        [
            "`codex-subagent-orchestration/` —— 默认优先的自适应编排入口",
            "只有用户显式要求 subAgent / parallel agent / delegation",
            "默认进入编排入口不等于默认实际 spawn subAgent",
            "`实现 skill -> testing/定向验证 -> code-review`",
            "最窄定向单测",
            "80~120 行",
            "image_model = \"gpt-image-2\"",
            "model = \"gpt-5.5\"",
            "model_reasoning_effort = \"medium\"",
            "python3 scripts/lint_subagent_orchestration_policy.py",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "TAXONOMY.md",
        [
            "iOS 开发任务默认先进入 `codex-subagent-orchestration`",
            "`实现 skill -> testing/定向验证 -> code-review`",
            "最窄定向单测",
            "`appleDeveloperDocs`",
            "`lite` / `standard` / `full`",
            "仅在用户显式要求 subAgent / parallel agent / delegation",
            "需要补强证据时再切 `final-evidence-gate` 或 `verify-ios-build`",
            "保持本地 `:path` 私有库依赖",
        ],
        failures,
    )

    skill_md = SKILL_ROOT / "SKILL.md"
    require_contains(
        skill_md,
        [
            "默认优先使用的 iOS 主 Skill 入口",
            "Native subAgents are used only when explicitly requested",
            "Use Codex native subAgent tools only when the user explicitly asks",
            "Default to single Agent execution when native subAgent use is not explicitly authorized",
            "Single Agent execution must still preserve testing / targeted validation and `code-review` closure",
            "`test_impact` or `no_test_reason`",
            "`blocking_findings`",
            "`suggested_validation`",
            "`executed_validation`",
            "`failure_attribution`",
            "`needs_test_code`",
            "真机 / 模拟器验证不属于默认 testing 执行面",
            "`spawn_agent` / `send_input` / `wait_agent` / `close_agent`",
            "80-120 relevant lines",
            "references/coding-standards.md",
            "references/tool-routing.md",
        ],
        failures,
    )

    require_contains(
        ROOT / "config" / "codex" / "codex.shared.toml",
        [
            "model = \"gpt-5.5\"",
            "image_model = \"gpt-image-2\"",
            "model_reasoning_effort = \"medium\"",
            "plan_mode_reasoning_effort = \"medium\"",
            "multi_agent = true",
            "[agents]",
            "max_threads = 6",
            "max_depth = 1",
        ],
        failures,
    )

    yaml_path = SKILL_ROOT / "agents" / "openai.yaml"
    require_exists(yaml_path, failures)
    if yaml_path.exists():
        require_contains(
            yaml_path,
            [
                "iOS 主 Skill 入口",
                "$codex-subagent-orchestration",
                "lite / standard / full",
                "只有用户显式要求 subAgent / parallel agent / delegation",
                "未显式授权时按单 Agent 执行",
            ],
            failures,
        )
        require_yaml_parse(yaml_path, failures)

    require_contains(
        SKILL_ROOT / "references" / "model-selection.md",
        [
            "只有用户显式要求 subAgent / parallel agent / delegation",
            "截至 2026-06-15",
            "默认 reasoning effort 为 `medium`",
            "不调用 `spawn_agent`",
            "继承主 Agent 默认模型",
        ],
        failures,
    )
    require_contains(
        SKILL_ROOT / "references" / "prompt-templates.md",
        [
            "默认进入 `codex-subagent-orchestration` 不等于默认实际 spawn subAgent",
            "只有显式授权原生 subAgent",
            "最窄定向单测",
            "code-review 审查（实现链路必选",
            "回线上版本化引用与复测仅在用户明确要求时执行",
        ],
        failures,
    )
    require_contains(
        SKILL_ROOT / "references" / "role-contracts.md",
        [
            "默认进入编排入口只做决策",
            "只有用户显式要求 subAgent / parallel agent / delegation",
            "未显式授权",
            "按单 Agent 执行",
            "`blocking_findings: []`",
        ],
        failures,
    )
    require_contains(
        SKILL_ROOT / "references" / "handoff-loop.md",
        [
            "默认进入 `codex-subagent-orchestration` 不等于默认实际 spawn subAgent",
            "只有用户显式要求 subAgent / parallel agent / delegation",
            "按单 Agent 执行",
            "同一类问题最多回写 coder 2 次",
        ],
        failures,
    )
    require_contains(
        SKILL_ROOT / "references" / "tool-routing.md",
        [
            "`appleDeveloperDocs`",
            "`Build iOS Apps` / `xcodebuildmcp`",
            "`functions.exec_command`",
            '`sandbox_permissions=\\"require_escalated\\"',
            "最窄定向单测",
            "`multi_tool_use.parallel`",
            "`apply_patch`",
            "80~120 行",
            "`/tmp/*.log`",
        ],
        failures,
    )

    if failures:
        print("subagent orchestration policy lint failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("subagent orchestration policy lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
