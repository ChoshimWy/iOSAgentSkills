#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

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
                "lint_workflow_contract_policy.py requires Python 3.11+, `tomli`, or pip's vendored tomli"
            ) from exc


ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = ROOT / "skills" / "codex-subagent-orchestration"
CODEX_TEMPLATE_AGENTS = ROOT / "config" / "codex" / "templates" / "agents"
CODEX_AGENT_VALIDATE_SCRIPT = ROOT / "scripts" / "validate_codex_agent_templates.py"
EXPECTED_DISABLED_PLUGINS = {
    "build-ios-apps@openai-curated",
    "build-macos-apps@openai-curated",
    "figma@openai-curated",
    "github@openai-curated",
    "figma@openai-curated-remote",
    "product-design@openai-curated-remote",
    "superpowers@openai-curated-remote",
    "documents@openai-primary-runtime",
    "spreadsheets@openai-primary-runtime",
    "presentations@openai-primary-runtime",
    "pdf@openai-primary-runtime",
    "browser@openai-bundled",
    "chrome@openai-bundled",
    "computer-use@openai-bundled",
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


def require_codex_plugins_disabled(path: Path, failures: list[str]) -> None:
    if not path.exists():
        failures.append(f"{path.relative_to(ROOT)} missing")
        return

    data = tomllib.loads(path.read_text())
    plugins = data.get("plugins")
    if not isinstance(plugins, dict):
        failures.append(f"{path.relative_to(ROOT)} missing plugins table")
        return

    missing = sorted(EXPECTED_DISABLED_PLUGINS - set(plugins))
    if missing:
        failures.append(f"{path.relative_to(ROOT)} missing disabled plugin entries: {', '.join(missing)}")

    enabled_or_invalid = sorted(
        plugin_id
        for plugin_id, config in plugins.items()
        if not isinstance(config, dict) or config.get("enabled") is not False
    )
    if enabled_or_invalid:
        failures.append(
            f"{path.relative_to(ROOT)} plugins must all set enabled = false: {', '.join(enabled_or_invalid)}"
        )


def main() -> int:
    failures: list[str] = []

    for path in (
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / "skills" / "TAXONOMY.md",
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "references" / "prompt-templates.md",
        SKILL_ROOT / "references" / "role-contracts.md",
        SKILL_ROOT / "references" / "apple-gate-rules.md",
        SKILL_ROOT / "references" / "checkpoint-contract.md",
        ROOT / "skills" / "ios-feature-implementation" / "SKILL.md",
        ROOT / "skills" / "ios-performance" / "SKILL.md",
        ROOT / "skills" / "ios-automation" / "SKILL.md",
        ROOT / "config" / "codex" / "templates" / "agents" / "README.md",
        ROOT / "config" / "claude-code" / "memory-seed.md",
    ):
        require_not_contains(
            path,
            ["仓库级显式触发", "自动使用 subAgent", "按档位自动", "默认启用 subAgent 工作流"],
            failures,
        )
        require_not_contains(
            path,
            [
                "-> code-review",
                "then `code-review`",
                "plus `code-review`",
                "且 `code-review` 无 blocking findings",
                "定向验证与 code-review 收口",
                "只有显式授权原生 subAgent 时才拆成独立 subAgent",
                "只有我显式要求 subAgent / parallel agent / delegation 时才调用",
            ],
            failures,
        )

    require_contains(
        ROOT / "AGENTS.md",
        [
            "任务分型器归类",
            "`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`",
            "`explorer + builder + reporter`",
            "默认进入编排入口不等于默认实际 spawn subAgent",
        ],
        failures,
    )

    require_contains(
        ROOT / "README.md",
        [
            "默认按主 Agent 串行承担 explorer -> builder -> reporter 逻辑角色",
            "任务分型：`doc-only` / `rule-only` / `code-small` / `code-medium` / `code-risky`",
            "默认先按任务分型器分类",
            "`explorer + builder + reporter`",
            "model = \"gpt-5.5\"",
            "image_model = \"gpt-image-2\"",
            "model_reasoning_effort = \"medium\"",
            "pod_private_cache_guard.py",
            "python3 scripts/lint_workflow_contract_policy.py",
            "python3 scripts/validate_codex_agent_templates.py",
            "config/codex/templates/agents/",
            "~/.codex/agents/",
            "local-only skills mode",
            "plugin-contributed skills/tools",
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
            "[features]",
            "multi_agent = true",
            "[agents]",
            "max_threads = 6",
            "max_depth = 1",
            "[plugins.\"build-ios-apps@openai-curated\"]",
            "[plugins.\"superpowers@openai-curated-remote\"]",
            "[plugins.\"browser@openai-bundled\"]",
            "[plugins.\"documents@openai-primary-runtime\"]",
            "enabled = false",
        ],
        failures,
    )
    require_codex_plugins_disabled(ROOT / "config" / "codex" / "codex.shared.toml", failures)
    require_contains(
        ROOT / "scripts" / "sync_codex_shared_config.py",
        [
            '"image_model"',
            '"agents"',
            '"model_reasoning_effort"',
            '"plan_mode_reasoning_effort"',
            "disable_plugin_entry",
            "local-only skills mode",
        ],
        failures,
    )

    require_contains(
        ROOT / "install-local-agent-config.sh",
        [
            "~/.codex/agents/*.toml",
            "config/codex/templates/agents/*.toml",
            "sync_codex_agent_templates",
            "verify_codex_agent_templates",
            "validate_codex_agent_templates.py",
        ],
        failures,
    )
    require_contains(
        ROOT / ".githooks" / "pre-commit",
        ["pod_private_cache_guard.py"],
        failures,
    )
    require_contains(
        ROOT / "scripts" / "pod_private_cache_guard.py",
        [
            "Pods/Manifest.lock",
            "本地 `:path` 私有库引用",
            "严格禁止提交",
            "Podfile / Podfile.lock / Pods/Manifest.lock",
        ],
        failures,
    )

    require_contains(
        SKILL_ROOT / "SKILL.md",
        [
            "## Task Classification",
            "`doc-only`",
            "`rule-only`",
            "`code-small`",
            "`code-medium`",
            "`code-risky`",
            "## Role Activation Matrix",
            "Default minimum logical role set: `explorer + builder + reporter`",
            "implementation-chain `reviewer explorer` is a required independent subAgent",
            "Default maximum loop count for the same issue class: 2",
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
            "reviewer subAgent 必须独立启动",
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
            "默认进入 `codex-subagent-orchestration` 不等于默认实际 spawn coder / tester subAgent",
            "next_action 不能是 complete",
        ],
        failures,
    )

    require_contains(
        SKILL_ROOT / "references" / "handoff-loop.md",
        [
            "任务分型器判定",
            "`CP1` 未通过前禁止无必要并行扩散",
            "默认进入 `codex-subagent-orchestration` 不等于默认实际 spawn coder / tester subAgent",
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

    require_contains(CODEX_TEMPLATE_AGENTS / "pm.toml", ['"checkpoint_status"', '"first_failure"', '"next_action"'], failures)
    require_contains(CODEX_TEMPLATE_AGENTS / "explorer.toml", ['"checkpoint_status"', '"first_failure"', '"next_action"'], failures)
    require_contains(
        CODEX_TEMPLATE_AGENTS / "builder.toml",
        ['"change_intent"', '"rollback_hint"', '"checkpoint_status"', '"first_failure"', '"next_action"'],
        failures,
    )
    require_contains(
        CODEX_TEMPLATE_AGENTS / "tester.toml",
        ['"failure_attribution_type"', '"checkpoint_status"', '"first_failure"', '"next_action"', "code_bug/test_bug/env_issue/unknown"],
        failures,
    )
    require_contains(
        CODEX_TEMPLATE_AGENTS / "reporter.toml",
        ['"acceptance_matrix"', '"checkpoint_status"', '"first_failure"', '"next_action"'],
        failures,
    )

    require_contains(
        CODEX_TEMPLATE_AGENTS / "README.md",
        [
            "任务分型",
            "默认最小逻辑角色集合：`explorer + builder + reporter`",
            "reviewer subAgent 是强制收口角色",
            "实现链路收口必须启动独立 reviewer subAgent 执行 code-review",
            "统一字段",
        ],
        failures,
    )

    require_exists(CODEX_AGENT_VALIDATE_SCRIPT, failures)
    if (ROOT / ".codex").exists():
        failures.append(".codex should not exist in repository root")

    if failures:
        print("workflow contract policy lint failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("workflow contract policy lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
