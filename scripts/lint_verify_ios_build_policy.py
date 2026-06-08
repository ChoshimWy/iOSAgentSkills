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
    "sdk-architecture",
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

    require_contains(
        ROOT / "AGENTS.md",
        [
            "条件化最终证据门禁（final-evidence-gate）",
            "目标项目环境",
            "本地所有 `xcodebuild` 命令",
            "codex_verify.sh",
            "~/.codex/bin/codex_verify",
            "XCODE_DERIVED_DATA",
            "如果同时存在 `.xcworkspace` 和 `.xcodeproj`，验证优先使用 `.xcworkspace`",
            "final-evidence-gate",
            "绑定了单元测试 `*Tests` target / bundle 的 scheme",
            "已连接真机",
            "`实现 skill -> testing -> code-review -> final-evidence-gate`",
            "在 `final-evidence-gate` 接受现有证据或 `verify-ios-build` 成功之前，任务都不算完成",
        ],
        failures,
    )
    require_contains(
        ROOT / "README.md",
        [
            "条件化最终证据门禁",
            "目标项目根目录的项目环境",
            "本地所有 `xcodebuild` 命令",
            "codex_verify.sh",
            "~/.codex/bin/codex_verify",
            "XCODE_DERIVED_DATA",
            "优先 `.xcworkspace`",
            "绑定了单元测试 `*Tests` target / bundle 的 scheme",
            "已连接真机",
            "`实现 skill -> testing -> code-review -> final-evidence-gate`",
            "python3 scripts/lint_verify_ios_build_policy.py",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "TAXONOMY.md",
        [
            "最终都必须进入 `final-evidence-gate` 做完成态裁决",
            "目标项目根目录的项目环境",
            "codex_verify.sh",
            "~/.codex/bin/codex_verify",
            "优先 `.xcworkspace`",
            "绑定了单元测试 `*Tests` target / bundle 的 scheme",
            "已连接真机",
            "`实现 skill -> testing -> code-review -> final-evidence-gate`",
            "不能把任务表述为“已完成”",
        ],
        failures,
    )

    for skill in FINAL_EVIDENCE_SKILLS:
        skill_md = ROOT / "skills" / skill / "SKILL.md"
        require_contains(
            skill_md,
            [
                "final-evidence-gate",
                "`verify-ios-build`",
                "项目环境",
                ".xcworkspace",
                "已连接真机",
                "不得把任务表述",
            ],
            failures,
        )

        openai_yaml = ROOT / "skills" / skill / "agents" / "openai.yaml"
        if not openai_yaml.exists():
            failures.append(f"{openai_yaml.relative_to(ROOT)} missing")
        else:
            require_contains(
                openai_yaml,
                [
                    "$final-evidence-gate",
                    "$verify-ios-build",
                    "项目环境",
                    ".xcworkspace",
                ],
                failures,
            )

    for direct_flow_skill in (
        "ios-feature-implementation",
        "swiftui-feature-implementation",
        "uikit-feature-implementation",
    ):
        require_contains(
            ROOT / "skills" / direct_flow_skill / "SKILL.md",
            [
                "固定四步",
                "testing",
                "code-review",
                "verify-ios-build",
            ],
            failures,
        )
        require_contains(
            ROOT / "skills" / direct_flow_skill / "agents" / "openai.yaml",
            [
                "$testing",
                "$code-review",
                "$verify-ios-build",
                "no_test_reason",
            ],
            failures,
        )

    for targeted_skill in (
        "testing",
        "ios-automation",
    ):
        require_contains(
            ROOT / "skills" / targeted_skill / "SKILL.md",
            [
                "workspace / scheme / destination 基线",
                "require_escalated",
                "Xcode 系统 DerivedData",
            ],
            failures,
        )
    require_contains(
        ROOT / "skills" / "testing" / "SKILL.md",
        [
            "绑定了单元测试 `*Tests` target / bundle 的 scheme",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "ios-automation" / "SKILL.md",
        [
            "绑定了单元测试 `*Tests` target/bundle 的 scheme",
        ],
        failures,
    )

    require_contains(
        ROOT / "skills" / "xcode-build" / "SKILL.md",
        [
            "require_escalated",
            "Xcode 系统 DerivedData",
        ],
        failures,
    )

    require_contains(
        ROOT / "skills" / "verify-ios-build" / "SKILL.md",
        [
            "项目环境构建验证执行器",
            "项目环境",
            "require_escalated",
            "codex_verify.sh",
            "~/.codex/bin/codex_verify",
            "本地 `xcodebuild` 命令（含 `-list` / `-showdestinations` / build/test）统一按非沙盒项目环境执行",
            "本地 `verify-ios-build` 不支持 `XCODE_DERIVED_DATA` 覆盖",
            "默认复用同一套 workspace / scheme / destination 基线",
            "绑定了单元测试 `*Tests` target / bundle 的 scheme",
            ".xcworkspace",
            "已连接真机",
            "任务未完成",
            "macOS Xcode 工程",
            "XCODE_UI_SMOKE_MODE",
            "text-first",
            "final-evidence-gate",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "final-evidence-gate" / "SKILL.md",
        [
            "codex_verify.sh",
            "~/.codex/bin/codex_verify",
            "串行化",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "verify-ios-build" / "references" / "override-config.md",
        [
            "项目环境",
            "本地 `verify-ios-build` 不支持 `XCODE_DERIVED_DATA` 覆盖",
            "codex_verify.sh",
            "~/.codex/bin/codex_verify",
            "本地执行 `xcodebuild`（含 `-list` / `-showdestinations` / build/test）默认在项目环境直接执行",
            "绑定了单元测试 `*Tests` target / bundle 的 scheme",
            "复用同一套 workspace / scheme / destination 基线",
            "已连接真机",
            "generic/platform=iOS Simulator",
            "宿主机 `xcodebuild build`",
            "`.xcworkspace` 优先于 `.xcodeproj`",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "verify-ios-build" / "scripts" / "build-check.sh",
        [
            "CODEX_VERIFY_BYPASS_WRAPPER",
            "TARGET_VERIFY_SCRIPT",
            "GLOBAL_VERIFY_SCRIPT",
            "--build-check",
            "generic/platform=iOS Simulator",
            "connected-only",
            "XCODE_VALIDATION_PLATFORM='macos'",
            "no connected physical iOS destination available; using simulator",
        ],
        failures,
    )
    verify_template = ROOT / "config" / "codex" / "templates" / "codex_verify.example.sh"
    if not verify_template.exists():
        failures.append(f"{verify_template.relative_to(ROOT)} missing")
    else:
        require_contains(
            verify_template,
            [
                "--repo-root",
                "--build-check",
                "xcodebuild",
                "/usr/bin/lockf",
                "/usr/bin/shlock",
                "CODEX_VERIFY_BYPASS_WRAPPER",
                "owner.txt",
            ],
            failures,
        )
    require_contains(
        ROOT / "install-local-agent-config.sh",
        [
            "codex_verify.example.sh",
            "sync_codex_verify_template",
            "sync_codex_verify_wrapper",
            "CODEX_VERIFY_WRAPPER",
            "CODEX_BIN_DIR",
            "CODEX_VERIFY_TEMPLATE",
            "REPO_CODEX_VERIFY_TEMPLATE",
        ],
        failures,
    )
    require_contains(
        ROOT / "config" / "codex" / "templates" / "agents" / "README.md",
        [
            "codex_verify.example.sh",
            "codex_verify.sh",
            "~/.codex/bin/codex_verify",
            "~/.codex/templates/codex_verify.example.sh",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "verify-ios-build" / "scripts" / "build_check.py",
        [
            "is_unit_test_preferred_scheme",
            "scheme_has_unit_test_binding",
            "BuildableName",
            "XCODE_DERIVED_DATA is not supported in local verify-ios-build",
            "Library/Developer/Xcode/DerivedData",
            'validation_platform=os.environ.get("XCODE_VALIDATION_PLATFORM")',
            'if config.validation_platform == "macos":',
            'default host build (no explicit destination)',
        ],
        failures,
    )
    require_not_contains(
        ROOT / "skills" / "verify-ios-build" / "scripts" / "build_check.py",
        [
            "-derivedDataPath",
            ".codex-derived-data",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "ios-automation" / "scripts" / "device" / "device_helpers.sh",
        [
            "BuildableName",
            "TestableReference",
            "select_connected_xcode_destination",
            "connected-only",
            "selected first connected xcodebuild destination",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "ios-automation" / "scripts" / "simulator" / "xcode" / "builder.py",
        [
            "is_unit_test_preferred_scheme",
            "scheme_has_unit_test_binding",
            "BuildableName",
            "TestableReference",
        ],
        failures,
    )

    require_contains(
        ROOT / "skills" / "macos-menubar-tuist-app" / "SKILL.md",
        [
            "final-evidence-gate",
            "`verify-ios-build`",
            "项目环境",
            "任务未完成",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "macos-menubar-tuist-app" / "agents" / "openai.yaml",
        [
            "$verify-ios-build",
            "项目环境",
        ],
        failures,
    )

    require_contains(
        ROOT / "skills" / "ios-automation" / "SKILL.md",
        [
            "text-before-pixels",
            "ui_smoke_runner.py",
        ],
        failures,
    )

    ui_smoke_runner = ROOT / "skills" / "ios-automation" / "scripts" / "simulator" / "ui_smoke_runner.py"
    if not ui_smoke_runner.exists():
        failures.append(f"{ui_smoke_runner.relative_to(ROOT)} missing")

    verify_openai = ROOT / "skills" / "verify-ios-build" / "agents" / "openai.yaml"
    if not verify_openai.exists():
        failures.append(f"{verify_openai.relative_to(ROOT)} missing")
    else:
        require_contains(
            verify_openai,
            [
                "项目环境",
                ".xcworkspace",
                "已连接真机",
                "simulator",
            ],
            failures,
        )

    for targeted_openai in (
        ROOT / "skills" / "testing" / "agents" / "openai.yaml",
        ROOT / "skills" / "ios-automation" / "agents" / "openai.yaml",
    ):
        require_contains(
            targeted_openai,
            [
                "$verify-ios-build",
                "scheme",
                "基线",
            ],
                failures,
        )

    require_contains(
        ROOT / "skills" / "code-review" / "SKILL.md",
        [
            "第三步静态审查阶段",
            "默认审查当前 unstaged + untracked 工作区改动",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "code-review" / "agents" / "openai.yaml",
        [
            "$verify-ios-build",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "testing" / "SKILL.md",
        [
            "第二步测试阶段",
            "`no_test_reason`",
            "codex_verify.sh",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "testing" / "agents" / "openai.yaml",
        [
            "no_test_reason",
            "$code-review",
            "$verify-ios-build",
        ],
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
