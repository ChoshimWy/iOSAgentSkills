#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = ROOT / "skills" / "codex-subagent-orchestration"


def require_contains(path: Path, snippets: list[str], failures: list[str]) -> None:
    text = path.read_text()
    missing = [snippet for snippet in snippets if snippet not in text]
    if missing:
        failures.append(f"{path.relative_to(ROOT)} missing: {', '.join(missing)}")


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

    require_contains(
        ROOT / "AGENTS.md",
        [
            "默认先使用 `codex-subagent-orchestration`",
            "默认三步收口",
            "`实现 skill -> testing/定向验证 -> code-review`",
            "`lite` / `standard` / `full`",
            "临时回退为单 Agent",
            "80~120 行",
            "实现链路必须包含 `code-review` 审查步骤",
            "checkpoint 合同",
            "`checkpoint_status`",
            "`fail-fix-report`",
            "主项目默认必须切回或保持本地 `:path` 私有库依赖",
        ],
        failures,
    )
    require_contains(
        ROOT / "README.md",
        [
            "`codex-subagent-orchestration/` —— 默认优先的自适应多 Agent 编排入口",
            "python3 scripts/lint_subagent_orchestration_policy.py",
            "`实现 skill -> testing/定向验证 -> code-review`",
            "`lite` / `standard` / `full`",
            "80~120 行",
            "计划模式（`proposed_plan`）输出，只要是实现链路也必须显式包含 `code-review` 审查步骤",
            "主项目默认必须切回或保持本地 `:path` 私有库依赖",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "TAXONOMY.md",
        [
            "默认优先切到 `codex-subagent-orchestration`",
            "默认三步收口",
            "`实现 skill -> testing/定向验证 -> code-review`",
            "`appleDeveloperDocs`",
            "`lite` / `standard` / `full`",
            "需要补强证据时再切 `final-evidence-gate` 或 `verify-ios-build`",
            "主项目切回或保持本地 `:path` 私有库依赖",
        ],
        failures,
    )

    skill_md = SKILL_ROOT / "SKILL.md"
    require_contains(
        skill_md,
        [
            "默认优先使用本 skill",
            "`lite` / `standard` / `full`",
            "临时回退单 Agent",
            "`test_impact` 或 `no_test_reason`",
            "`blocking_findings` 只放真实阻塞项",
            "`suggested_validation`、`executed_validation`、`failure_attribution`、`needs_test_code`",
            "`appleDeveloperDocs`",
            "`functions.exec_command`",
            "`multi_tool_use.parallel`",
            "references/coding-standards.md",
            "references/tool-routing.md",
            "80~120 行",
            "`/tmp/*.log`",
            "实现型任务仍必须保留 `testing/定向验证` 与 `code-review` 审查阶段",
        ],
        failures,
    )

    yaml_path = SKILL_ROOT / "agents" / "openai.yaml"
    require_exists(yaml_path, failures)
    if yaml_path.exists():
        require_contains(
            yaml_path,
            [
                "默认优先的自适应多 Agent 编排",
                "$codex-subagent-orchestration",
                "lite / standard / full",
                "临时回退单 Agent",
            ],
            failures,
        )
        require_yaml_parse(yaml_path, failures)

    coding_standards = SKILL_ROOT / "references" / "coding-standards.md"
    require_exists(coding_standards, failures)
    if coding_standards.exists():
        require_contains(
            coding_standards,
            [
                "`test_impact`",
                "`no_test_reason`",
                "`blocking_findings`",
                "`non_blocking_findings`",
                "80~120 行",
                "`suggested_validation`",
                "`executed_validation`",
                "`failure_attribution`",
                "`needs_test_code`",
            ],
            failures,
        )

    tool_routing = SKILL_ROOT / "references" / "tool-routing.md"
    require_exists(tool_routing, failures)
    if tool_routing.exists():
        require_contains(
            tool_routing,
            [
                "`appleDeveloperDocs`",
                "`Build iOS Apps` / `xcodebuildmcp`",
            "`functions.exec_command`",
            '`sandbox_permissions=\\"require_escalated\\"',
            "凡是执行 `xcodebuild`",
            "`multi_tool_use.parallel`",
            "`apply_patch`",
            "80~120 行",
                "`/tmp/*.log`",
            ],
            failures,
        )

    require_contains(
        SKILL_ROOT / "references" / "role-contracts.md",
        [
            "`test_impact` 或 `no_test_reason`",
            "`blocking_findings: []`",
            "`review_scope`",
            "`impact_scope`",
            "`unreviewed_changes`",
            "`suggested_validation`",
            "`executed_validation`",
            "`failure_attribution`",
            "`needs_test_code`",
            "单 Agent fallback",
        ],
        failures,
    )
    require_contains(
        SKILL_ROOT / "references" / "prompt-templates.md",
        [
            "test_impact 或 no_test_reason",
            "lite / standard / full",
            "80~120 行",
            "`suggested_validation`",
            "`executed_validation`",
            "`failure_attribution`",
            "`needs_test_code`",
            "code-review 审查（实现链路必选",
            "本次任务全量差异",
            "直接影响面",
            "unreviewed_changes",
            "回线上版本化引用与复测仅在用户明确要求时执行",
        ],
        failures,
    )
    require_contains(
        SKILL_ROOT / "references" / "handoff-loop.md",
        [
            "`wait_agent(...)`",
            "单 Agent fallback",
            "同一类问题最多回写 coder 2 次",
            "排查 / 实现 / 验证 / 提交",
            '`sandbox_permissions=\\"require_escalated\\"',
        ],
        failures,
    )
    require_contains(
        SKILL_ROOT / "references" / "apple-gate-rules.md",
        [
            "`final-evidence-gate`",
            "目标项目环境",
            "`functions.exec_command`",
            "`.xcworkspace`",
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
