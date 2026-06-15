#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
FINAL_EVIDENCE_SKILLS = [
    "ios-feature-implementation",
    "swiftui-feature-implementation",
    "uikit-feature-implementation",
    "swift-expert",
    "swiftui-liquid-glass",
    "refactoring",
    "ios-sdk-architecture",
    "debugging",
    "testing",
    "ios-performance",
    "xcode-build",
    "ios-automation",
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


def main() -> int:
    failures: list[str] = []
    policy_paths = [
        ROOT / "AGENTS.md",
        ROOT / "CLAUDE.md",
        ROOT / "README.md",
        ROOT / "skills" / "TAXONOMY.md",
        ROOT / "skills" / "codex-subagent-orchestration" / "SKILL.md",
        ROOT / "config" / "claude-code" / "agents" / "orchestration.md",
        ROOT / "config" / "claude-code" / "memory-seed.md",
        ROOT / "config" / "codex" / "templates" / "agents" / "README.md",
        ROOT / "config" / "codex" / "templates" / "agents" / "pm.toml",
        ROOT / "config" / "codex" / "templates" / "agents" / "tester.toml",
    ]
    for path in policy_paths:
        require_not_contains(
            path,
            [
                "最终都必须进入 `final-evidence-gate`",
                "`实现 skill -> testing -> reviewer subAgent(code-review) -> final-evidence-gate`",
                "任务都不算完成",
                "四步收口",
                "固定四步",
                "未通过 CP3 不得宣告完成",
                "Apple 相关改动必须进入 final-evidence-gate",
            ],
            failures,
        )

    require_contains(
        ROOT / "AGENTS.md",
        [
            "独立 reviewer subAgent 执行 `code-review`",
            "目标项目根目录的项目环境",
            "完整项目环境证据",
            "Xcode 系统 DerivedData",
            "shared build-queue daemon",
            "--queue-status",
            "最窄定向验证",
            "独立 reviewer subAgent 执行的 `code-review` 无 blocking findings",
        ],
        failures,
    )
    require_contains(
        ROOT / "README.md",
        [
            "默认收口与可选证据验证",
            "完整项目环境证据",
            "Xcode 系统 DerivedData",
            "shared build-queue daemon",
            "--queue-status",
            "最窄定向单测",
            "`实现 skill -> testing/定向验证 -> reviewer subAgent(code-review)`",
            "python3 scripts/lint_verify_ios_build_policy.py",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "TAXONOMY.md",
        [
            "默认完成标准：定向测试或必要验证通过",
            "最窄定向单测",
            "sandbox 结果",
            "`.xcworkspace` 优先",
            "shared build-queue daemon",
            "--queue-status",
            "`实现 skill -> testing/定向验证 -> reviewer subAgent(code-review)`",
            "`final-evidence-gate` 与 `verify-ios-build` 不再是所有 Apple Xcode 项目改动的强制收尾",
        ],
        failures,
    )

    for skill in FINAL_EVIDENCE_SKILLS:
        skill_md = ROOT / "skills" / skill / "SKILL.md"
        require_contains(skill_md, ["final-evidence-gate", "verify-ios-build"], failures)

        openai_yaml = ROOT / "skills" / skill / "agents" / "openai.yaml"
        if openai_yaml.exists():
            require_contains(openai_yaml, ["$final-evidence-gate", "$verify-ios-build", "按需"], failures)

    for direct_flow_skill in ("ios-feature-implementation", "swiftui-feature-implementation", "uikit-feature-implementation"):
        require_contains(
            ROOT / "skills" / direct_flow_skill / "SKILL.md",
            ["testing", "code-review", "verify-ios-build"],
            failures,
        )
        require_contains(
            ROOT / "skills" / direct_flow_skill / "agents" / "openai.yaml",
            ["$testing", "$code-review", "$verify-ios-build", "no_test_reason"],
            failures,
        )

    require_contains(ROOT / "skills" / "testing" / "SKILL.md", ["定向测试", "no_test_reason", "suggested_validation"], failures)
    require_contains(ROOT / "skills" / "ios-automation" / "SKILL.md", ["Simulator", "真机"], failures)
    require_contains(ROOT / "skills" / "xcode-build" / "SKILL.md", ["verify-ios-build", "final-evidence-gate"], failures)

    require_contains(
        ROOT / "skills" / "verify-ios-build" / "SKILL.md",
        [
            "按需项目环境构建验证执行器",
            "项目环境",
            "codex_verify.sh",
            "~/.codex/bin/codex_verify",
            "shared build-queue daemon",
            "Xcode 系统 DerivedData",
            "final-evidence-gate",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "final-evidence-gate" / "SKILL.md",
        ["codex_verify.sh", "~/.codex/bin/codex_verify", "项目环境", "verify-ios-build"],
        failures,
    )
    require_contains(
        ROOT / "skills" / "verify-ios-build" / "references" / "override-config.md",
        [
            "项目环境",
            "shared build-queue daemon",
            "--queue-status",
            "公开配置已移除",
            "项目环境执行",
            "`.xcworkspace` 优先于 `.xcodeproj`",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "verify-ios-build" / "scripts" / "build-check.sh",
        ["CODEX_VERIFY_BYPASS_WRAPPER", "TARGET_VERIFY_SCRIPT", "GLOBAL_VERIFY_SCRIPT", "--build-check"],
        failures,
    )
    verify_template = ROOT / "config" / "codex" / "templates" / "codex_verify.example.sh"
    require_contains(
        verify_template,
        ["--repo-root", "--build-check", "--queue-status", "xcodebuild", "shared build-queue daemon", "CODEX_VERIFY_BYPASS_WRAPPER"],
        failures,
    )
    require_contains(
        ROOT / "install-local-agent-config.sh",
        ["codex_verify.example.sh", "sync_codex_verify_template", "sync_codex_verify_wrapper", "CODEX_VERIFY_WRAPPER"],
        failures,
    )
    require_contains(
        ROOT / "config" / "codex" / "templates" / "agents" / "README.md",
        ["codex_verify.example.sh", "codex_verify.sh", "~/.codex/bin/codex_verify", "~/.codex/templates/codex_verify.example.sh", "shared build-queue daemon", "--queue-status"],
        failures,
    )
    require_contains(
        ROOT / "skills" / "verify-ios-build" / "scripts" / "build_check.py",
        ["is_unit_test_preferred_scheme", "scheme_has_unit_test_binding", "BuildableName", "Library/Developer/Xcode/DerivedData"],
        failures,
    )
    require_contains(
        ROOT / "skills" / "ios-automation" / "scripts" / "device" / "device_helpers.sh",
        ["BuildableName", "TestableReference", "select_connected_xcode_destination"],
        failures,
    )
    require_contains(
        ROOT / "skills" / "ios-automation" / "scripts" / "simulator" / "xcode" / "builder.py",
        ["is_unit_test_preferred_scheme", "scheme_has_unit_test_binding", "BuildableName", "TestableReference"],
        failures,
    )

    if failures:
        print("final-evidence-gate policy lint failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("final-evidence-gate policy lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
