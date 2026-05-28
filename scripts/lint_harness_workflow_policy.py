#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = ROOT / "skills" / "codex-subagent-orchestration"
EXEMPT_OPENAI_SKILLS = {"_shared-sentinel"}
CODEX_TEMPLATE_AGENTS = ROOT / "config" / "codex" / "templates" / "agents"
CODEX_AGENT_VALIDATE_SCRIPT = ROOT / "scripts" / "validate_codex_agent_templates.py"


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


def require_codex_agent_templates_parse(failures: list[str]) -> None:
    result = subprocess.run(
        ["python3", str(CODEX_AGENT_VALIDATE_SCRIPT), str(CODEX_TEMPLATE_AGENTS)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown codex agent schema error"
        failures.append(f"{CODEX_TEMPLATE_AGENTS.relative_to(ROOT)} invalid codex agent schema: {stderr}")


def require_non_system_skill_openai_yaml(failures: list[str]) -> None:
    skills_root = ROOT / "skills"
    for skill_dir in skills_root.iterdir():
        if not skill_dir.is_dir():
            continue
        if skill_dir.name in {".system"}:
            continue
        if skill_dir.name in EXEMPT_OPENAI_SKILLS:
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        openai_yaml = skill_dir / "agents" / "openai.yaml"
        if not openai_yaml.exists():
            failures.append(f"{openai_yaml.relative_to(ROOT)} missing")
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
        ],
        failures,
    )

    skill_md = SKILL_ROOT / "SKILL.md"
    require_contains(
        skill_md,
        [
            "## Checkpoint 合同（新增默认规则）",
            "`CP0 Intent Lock`",
            "`CP1 Anchor Slice`",
            "`CP2 Validation Baseline Freeze`",
            "`CP3 Final Gate`",
            "`checkpoint_status`",
            "## Fail-Fix-Report 纪律（新增默认规则）",
            "`fail-fix-report`",
            "references/checkpoint-contract.md",
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
                "CP3：Final Gate（最终门禁）",
                "Fail-Fix-Report 纪律",
            ],
            failures,
        )

    require_contains(
        SKILL_ROOT / "references" / "role-contracts.md",
        [
            "`checkpoint_status`",
            "`first_failure`",
            "`next_action`",
        ],
        failures,
    )

    require_contains(
        SKILL_ROOT / "references" / "handoff-loop.md",
        [
            "`CP0 Intent Lock`",
            "`CP1 Anchor Slice`",
            "`CP2 Validation Baseline Freeze`",
            "`CP3 Final Gate`",
            "## Fail-Fix-Report",
            "未通过 `CP3` 不得宣告任务完成",
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
        ],
        failures,
    )

    for additional_skill in (
        ROOT / "skills" / "html-docs" / "SKILL.md",
        ROOT / "skills" / "office-docx" / "SKILL.md",
        ROOT / "skills" / "office-pptx" / "SKILL.md",
        ROOT / "skills" / "macos-menubar-tuist-app" / "SKILL.md",
        ROOT / "skills" / "macos-spm-app-packaging" / "SKILL.md",
        ROOT / "skills" / "ui-ux-design-system" / "SKILL.md",
        ROOT / "skills" / "app-store-changelog" / "SKILL.md",
        ROOT / "skills" / "app-store-opportunity-research" / "SKILL.md",
        ROOT / "skills" / "open-design" / "SKILL.md",
        ROOT / "skills" / "gh-pr-flow" / "SKILL.md",
        ROOT / "skills" / "git-workflow" / "SKILL.md",
    ):
        require_exists(additional_skill, failures)

    for internal_skill in (
        ROOT / "skills" / "apple-docs" / "SKILL.md",
        ROOT / "skills" / "swiftui-ui-patterns" / "SKILL.md",
        ROOT / "skills" / "swiftui-view-refactor" / "SKILL.md",
        ROOT / "skills" / "swiftui-liquid-glass" / "SKILL.md",
        ROOT / "skills" / "refactoring" / "SKILL.md",
        ROOT / "skills" / "sdk-architecture" / "SKILL.md",
        ROOT / "skills" / "swiftui-performance-audit" / "SKILL.md",
    ):
        require_exists(internal_skill, failures)

    require_contains(
        ROOT / "skills" / "verify-ios-build" / "SKILL.md",
        [
            "目标仓库可选文件",
        ],
        failures,
    )

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

    require_contains(
        CODEX_TEMPLATE_AGENTS / "pm.toml",
        [
            "name = \"pm\"",
            "\"checkpoint_status\"",
            "\"first_failure\"",
            "\"next_action\"",
        ],
        failures,
    )

    require_contains(
        CODEX_TEMPLATE_AGENTS / "explorer.toml",
        [
            "name = \"explorer\"",
            "\"validation_baseline\"",
            "\"checkpoint_status\"",
            "\"first_failure\"",
            "\"next_action\"",
        ],
        failures,
    )

    require_contains(
        CODEX_TEMPLATE_AGENTS / "builder.toml",
        [
            "name = \"builder\"",
            "\"changed_files\"",
            "\"known_risks\"",
            "\"change_intent\"",
            "\"rollback_hint\"",
            "\"checkpoint_status\"",
            "\"first_failure\"",
            "\"next_action\"",
        ],
        failures,
    )

    require_contains(
        CODEX_TEMPLATE_AGENTS / "tester.toml",
        [
            "name = \"tester\"",
            "\"suggested_validation\"",
            "\"failure_attribution\"",
            "\"failure_attribution_type\"",
            "\"checkpoint_status\"",
            "\"first_failure\"",
            "\"next_action\"",
        ],
        failures,
    )

    require_contains(
        CODEX_TEMPLATE_AGENTS / "reporter.toml",
        [
            "name = \"reporter\"",
            "\"acceptance_matrix\"",
            "\"delivery_summary\"",
            "\"residual_risks\"",
            "\"checkpoint_status\"",
            "\"first_failure\"",
            "\"next_action\"",
        ],
        failures,
    )

    require_exists(CODEX_TEMPLATE_AGENTS / "README.md", failures)

    require_contains(
        ROOT / "skills" / "ios-feature-implementation" / "SKILL.md",
        [
            "## 实现阶段输出合同",
            "`changed_files`",
            "`summary`",
            "`known_risks`",
            "`test_impact` 与 `no_test_reason` 二选一必须填写",
        ],
        failures,
    )

    require_contains(
        ROOT / "skills" / "code-review" / "SKILL.md",
        [
            "`blocking_findings`",
            "`non_blocking_findings`",
            "`first_failure`",
            "`next_action`",
            "`blocking_findings: []`",
        ],
        failures,
    )

    require_contains(
        ROOT / "skills" / "testing" / "SKILL.md",
        [
            "`suggested_validation`",
            "`executed_validation`",
            "`failure_attribution`",
            "`needs_test_code`",
            "`first_failure`",
            "`no_test_reason`",
        ],
        failures,
    )

    require_contains(
        ROOT / "skills" / "ios-feature-implementation" / "agents" / "openai.yaml",
        [
            "`changed_files`",
            "`summary`",
            "`known_risks`",
            "`test_impact` 与 `no_test_reason` 二选一必填",
            "$code-review",
            "$testing",
            "$verify-ios-build",
        ],
        failures,
    )

    require_contains(
        ROOT / "skills" / "code-review" / "agents" / "openai.yaml",
        [
            "`blocking_findings`",
            "`non_blocking_findings`",
            "`first_failure`",
            "`next_action`",
            "`blocking_findings: []`",
            "unstaged + untracked",
            "$verify-ios-build",
        ],
        failures,
    )

    require_contains(
        ROOT / "skills" / "testing" / "agents" / "openai.yaml",
        [
            "`suggested_validation`",
            "`executed_validation`",
            "`failure_attribution`",
            "`needs_test_code`",
            "`first_failure`",
            "`no_test_reason`",
            "$verify-ios-build",
        ],
        failures,
    )

    require_non_system_skill_openai_yaml(failures)

    if failures:
        print("harness workflow policy lint failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("harness workflow policy lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
