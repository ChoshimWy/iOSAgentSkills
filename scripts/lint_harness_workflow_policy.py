#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = ROOT / "skills" / "codex-subagent-orchestration"
CODEX_TEMPLATE_AGENTS = ROOT / "config" / "codex" / "templates" / "agents"
CODEX_AGENT_VALIDATE_SCRIPT = ROOT / "scripts" / "validate_codex_agent_templates.py"
REMOVED_SKILLS = {
    "office-docx",
    "office-pptx",
    "macos-menubar-tuist-app",
    "macos-spm-app-packaging",
    "open-design",
    "sdk-architecture",
    "refactoring",
    "swift-expert",
    "swiftui-feature-implementation",
    "uikit-feature-implementation",
    "ios-sdk-architecture",
    "swiftui-liquid-glass",
}
CURRENT_REQUIRED_SKILLS = {
    "app-store-changelog",
    "app-store-opportunity-research",
    "apple-docs",
    "code-review",
    "codex-subagent-orchestration",
    "debugging",
    "gh-pr-flow",
    "git-workflow",
    "html-docs",
    "ios-verification",
    "ios-automation",
    "ios-feature-implementation",
    "ios-performance",
    "ui-ux-design-system",
    "xcode-build",
}

FORBIDDEN_SUBAGENT_RESTRICTION_PHRASES = [
    "默认进入编排入口不等于必须 spawn",
    "默认进入 `codex-subagent-orchestration` 不等于必须 spawn",
    "full multi-agent execution",
    "write ownership",
    "write set is safe",
    "throughput benefit",
    "运行时工具可用",
    "写集安全",
    "拆分有质量/效率收益",
    "收益明确",
    "最少必要",
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


def require_not_exists(path: Path, failures: list[str]) -> None:
    if path.exists():
        failures.append(f"{path.relative_to(ROOT)} should not exist")


def require_yaml_parse(path: Path, failures: list[str]) -> None:
    result = subprocess.run(
        ["ruby", "-e", "require 'yaml'; YAML.load_file(ARGV[0])", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown yaml parse error"
        failures.append(f"{path.relative_to(ROOT)} invalid yaml: {stderr}")


def require_codex_agent_templates_parse(failures: list[str]) -> None:
    result = subprocess.run(
        ["python3", str(CODEX_AGENT_VALIDATE_SCRIPT), str(CODEX_TEMPLATE_AGENTS)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown codex agent schema error"
        failures.append(f"{CODEX_TEMPLATE_AGENTS.relative_to(ROOT)} invalid codex agent schema: {stderr}")


def require_existing_non_system_skill_openai_yaml_parse(failures: list[str]) -> None:
    for openai_yaml in sorted((ROOT / "skills").glob("*/agents/openai.yaml")):
        if ".system" in openai_yaml.relative_to(ROOT / "skills").parts:
            continue
        require_yaml_parse(openai_yaml, failures)


def main() -> int:
    failures: list[str] = []

    subagent_policy_paths = [
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
    for path in subagent_policy_paths:
        require_not_contains(path, FORBIDDEN_SUBAGENT_RESTRICTION_PHRASES, failures)

    require_contains(
        ROOT / "AGENTS.md",
        [
            "checkpoint 合同",
            "`CP0 Intent Lock`",
            "`CP1 Anchor Slice`",
            "`CP2 Validation Baseline Freeze`",
            "`CP3 Final Gate`",
            "`checkpoint_status`",
            "`fail-fix-report`",
            "本地 `:path` Pod",
            "主项目默认必须保持本地 `:path` 私有库依赖",
            "私有库仓内自测不能替代主项目验证",
            "验证通过后默认先保持当前本地 `:path` 私有库依赖状态",
            "除 `code-review` 必须由独立 reviewer subAgent 执行外",
            "修复 / 实现类任务不依赖手动 Plan 模式",
        ],
        failures,
    )

    require_contains(
        ROOT / "README.md",
        [
            "`CP0 Intent Lock`",
            "`CP1 Anchor Slice`",
            "`CP2 Validation Baseline Freeze`",
            "`CP3 Final Gate`",
            "`checkpoint_status`",
            "`fail-fix-report`",
            "python3 scripts/lint_harness_workflow_policy.py",
            "python3 scripts/lint_workflow_contract_policy.py",
            "python3 scripts/validate_codex_agent_templates.py",
            "config/codex/templates/agents/",
            "~/.codex/agents/",
            "所有技能统一放在 `skills/`",
            "`codex-subagent-orchestration`",
            "路径示例默认以 skill 相对路径为准",
            "主项目默认必须保持本地 `:path` 私有库依赖",
            "私有库仓内自测不能替代主项目验证",
            "禁止在未获明确授权时把包含本地 `:path` 私有库引用的 `Podfile` / `Podfile.lock` / `Pods/Manifest.lock` 提交进仓库",
            "非 Plan 模式也必须在首次写入前自动给出 CP0 最小计划",
        ],
        failures,
    )

    require_contains(
        ROOT / "skills" / "TAXONOMY.md",
        [
            "single-entry iOS core",
            "本文覆盖本仓库 `skills/` 下的全部 skills",
            "`CP0` / `CP1` / `CP2` / `CP3`",
            "`fail-fix-report`",
            "默认 iOS 主 Skill 入口",
            "内部路由到 `apple-docs`",
            "其它原生 subAgent 的启动场景、角色拆分或数量做额外限制"
        ],
        failures,
    )

    require_contains(
        SKILL_ROOT / "SKILL.md",
        [
            "## Checkpoints",
            "`CP0 Intent Lock`",
            "`CP1 Anchor Slice`",
            "`CP2 Validation Baseline Freeze`",
            "`CP3 Final Gate`",
            "`checkpoint_status`",
            "## Fail-Fix-Report Discipline",
            "fail-fix-report discipline",
            "references/checkpoint-contract.md",
            "Default maximum loop count for the same issue class: 2",
            "pre-implementation plan before any write",
        ],
        failures,
    )

    checkpoint_ref = SKILL_ROOT / "references" / "checkpoint-contract.md"
    require_exists(checkpoint_ref, failures)
    if checkpoint_ref.exists():
        require_contains(
            checkpoint_ref,
            [
                "CP0：Intent Lock（计划对齐）",
                "CP1：Anchor Slice（首个关键切片验收）",
                "CP2：Validation Baseline Freeze（验证基线冻结）",
                "CP3：Final Gate（定向验证与审查收口）",
                "Fail-Fix-Report 纪律",
                "CP0 不依赖手动 Plan 模式",
            ],
            failures,
        )

    require_contains(SKILL_ROOT / "references" / "role-contracts.md", ["`checkpoint_status`", "`first_failure`", "`next_action`"], failures)
    require_contains(
        SKILL_ROOT / "references" / "handoff-loop.md",
        [
            "`CP0 Intent Lock`",
            "`CP1 Anchor Slice`",
            "`CP2 Validation Baseline Freeze`",
            "`CP3 Final Gate`",
            "## Fail-Fix-Report",
            "定向验证失败或 `code-review` 存在 `阻塞问题` 时，不得宣告默认收口完成",
            "除实现链路 reviewer subAgent 必须独立启动外",
            "该计划不依赖手动 Plan 模式",
        ],
        failures,
    )
    require_contains(
        SKILL_ROOT / "references" / "prompt-templates.md",
        [
            "first_failure（仅当调用方要求机器字段时填写）",
            "first_failure: <none|首个真实失败点>",
            "next_action: <fix-and-rerun|blocked|complete>",
            "`checkpoint_status`：显式汇报 `CP0` / `CP1` / `CP2` / `CP3` 的 pass|fail|blocked",
            "禁止把 `Pods/<LibraryName>` 作为 ownership",
            "验证通过后默认保持当前本地 `:path` 状态",
            "默认写入前输出",
        ],
        failures,
    )

    for skill in CURRENT_REQUIRED_SKILLS:
        require_exists(ROOT / "skills" / skill / "SKILL.md", failures)
    for removed_skill in REMOVED_SKILLS:
        require_not_exists(ROOT / "skills" / removed_skill / "SKILL.md", failures)

    require_exists(CODEX_AGENT_VALIDATE_SCRIPT, failures)
    if CODEX_AGENT_VALIDATE_SCRIPT.exists():
        require_codex_agent_templates_parse(failures)

    for agent_file in (
        CODEX_TEMPLATE_AGENTS / "pm.toml",
        CODEX_TEMPLATE_AGENTS / "explorer.toml",
        CODEX_TEMPLATE_AGENTS / "builder.toml",
        CODEX_TEMPLATE_AGENTS / "tester.toml",
        CODEX_TEMPLATE_AGENTS / "reporter.toml",
    ):
        require_exists(agent_file, failures)

    require_contains(CODEX_TEMPLATE_AGENTS / "pm.toml", ["name = \"pm\"", '"checkpoint_status"', '"first_failure"', '"next_action"'], failures)
    require_contains(CODEX_TEMPLATE_AGENTS / "explorer.toml", ["name = \"explorer\"", '"validation_baseline"', '"checkpoint_status"', '"first_failure"', '"next_action"'], failures)
    require_contains(CODEX_TEMPLATE_AGENTS / "builder.toml", ["name = \"builder\"", '"changed_files"', '"known_risks"', '"change_intent"', '"rollback_hint"', '"checkpoint_status"', '"first_failure"', '"next_action"'], failures)
    require_contains(CODEX_TEMPLATE_AGENTS / "tester.toml", ["name = \"tester\"", '"suggested_validation"', '"failure_attribution"', '"failure_attribution_type"', '"checkpoint_status"', '"first_failure"', '"next_action"'], failures)
    require_contains(CODEX_TEMPLATE_AGENTS / "reporter.toml", ["name = \"reporter\"", '"acceptance_matrix"', '"delivery_summary"', '"residual_risks"', '"checkpoint_status"', '"first_failure"', '"next_action"'], failures)
    require_contains(
        CODEX_TEMPLATE_AGENTS / "README.md",
        [
            "默认最小逻辑角色集合：`explorer + builder + reporter`",
            "本仓只强制实现链路 `code-review` 使用独立 reviewer subAgent",
            "统一字段",
            "非 Plan 模式也必须在首次写入前自动给出 CP0 最小计划",
        ],
        failures,
    )

    require_contains(
        ROOT / "skills" / "ios-feature-implementation" / "SKILL.md",
        ["`changed_files`", "`summary`", "`known_risks`", "`test_impact`"],
        failures,
    )
    require_contains(
        ROOT / "skills" / "code-review" / "SKILL.md",
        ["阻塞问题", "非阻塞建议", "首个失败", "下一步", "阻塞问题：无"],
        failures,
    )
    require_contains(
        ROOT / "skills" / "ios-verification" / "SKILL.md",
        ["`suggested_validation`", "`executed_validation`", "`failure_attribution`", "`first_blocking_error`", "`no_test_reason`"],
        failures,
    )

    require_existing_non_system_skill_openai_yaml_parse(failures)

    if failures:
        print("harness workflow policy lint failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("harness workflow policy lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
