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
}
CURRENT_REQUIRED_SKILLS = {
    "app-store-changelog",
    "app-store-opportunity-research",
    "apple-docs",
    "code-review",
    "codex-subagent-orchestration",
    "debugging",
    "final-evidence-gate",
    "gh-pr-flow",
    "git-workflow",
    "html-docs",
    "ios-affected-tests",
    "ios-automation",
    "ios-build-log-digest",
    "ios-feature-implementation",
    "ios-performance",
    "ios-sdk-architecture",
    "ios-verification-router",
    "refactoring",
    "swift-expert",
    "swiftui-feature-implementation",
    "swiftui-liquid-glass",
    "testing",
    "ui-ux-design-system",
    "uikit-feature-implementation",
    "verify-ios-build",
    "xcode-build",
}


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
            "`git commit` 前也必须恢复到可提交的远端",
            "默认进入编排入口不等于默认实际 spawn subAgent",
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
            "主项目默认必须切回或保持本地 `:path` 私有库依赖",
            "禁止把包含本地 `:path` 私有库引用的 `Podfile` / `Podfile.lock` / `Pods/Manifest.lock` 提交进仓库",
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
            "仅在用户显式要求 subAgent / parallel agent / delegation",
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
            "定向验证失败或 `code-review` 存在 blocking findings 时，不得宣告默认收口完成",
            "默认进入 `codex-subagent-orchestration` 不等于默认实际 spawn subAgent",
        ],
        failures,
    )
    require_contains(
        SKILL_ROOT / "references" / "prompt-templates.md",
        [
            "first_failure（仅当存在阻塞项时填写）",
            "first_failure: <none|首个真实失败点>",
            "next_action: <fix-and-rerun|blocked|complete>",
            "`checkpoint_status`：显式汇报 `CP0` / `CP1` / `CP2` / `CP3` 的 pass|fail|blocked",
            "禁止把 `Pods/<LibraryName>` 作为 ownership",
            "回线上版本化引用与复测仅在用户明确要求时执行",
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
            "只有用户显式要求 subAgent / parallel agent / delegation",
            "统一字段",
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
        ["blocking_findings", "non_blocking_findings", "first_failure", "next_action", "blocking_findings: []"],
        failures,
    )
    require_contains(
        ROOT / "skills" / "testing" / "SKILL.md",
        ["`suggested_validation`", "`executed_validation`", "`failure_attribution`", "`needs_test_code`", "`first_failure`", "`no_test_reason`"],
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
